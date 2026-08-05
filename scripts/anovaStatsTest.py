import pandas as pd
import numpy as np
import os
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from statsmodels.stats.multicomp import pairwise_tukeyhsd

def run_statistical_analysis():
    print("="*70)
    print("🔬 MICROBIOME ML: STATISTICAL SIGNIFICANCE ANALYSIS (ANOVA & TUKEY)")
    print("="*70)

    # 1. הגדרת נתיבים (קורא מתוך תיקיית התוצאות שיצרנו)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    results_dir = os.path.normpath(os.path.join(script_dir, '..', 'preProcessingResults'))
    csv_path = os.path.join(results_dir, "Intra_Study_Results.csv")

    if not os.path.exists(csv_path):
        print(f"❌ שגיאה: קובץ התוצאות לא נמצא בנתיב:\n{csv_path}")
        print("אנא ודא שסקריפט ה-Intra Study סיים לרוץ בהצלחה.")
        return

    # 2. טעינת הנתונים
    df = pd.read_csv(csv_path)
    print(f"✅ נתונים נטענו בהצלחה! מנתח {len(df)} מחקרים בלתי תלויים.")

    # 3. סינון רק של עמודות ה-Test (מדד האמת החיצוני)
    test_cols = [c for c in df.columns if c.endswith("_Test")]
    df_test = df[['Study_ID'] + test_cols]

    # הפיכת הטבלה מ"רחבה" (Wide) ל"ארוכה" (Long) כדי שהמבחן הסטטיסטי יוכל לאכול אותה
    df_melt = df_test.melt(id_vars=["Study_ID"], value_vars=test_cols, var_name="Method", value_name="AUC")
    df_melt["Method"] = df_melt["Method"].str.replace("_Test", "")

    # 4. מבחן ANOVA (האם יש הבדל כללי?)
    print("\n📊 1. מבצע מבחן One-Way ANOVA...")
    groups = [group["AUC"].values for name, group in df_melt.groupby("Method")]
    f_stat, p_val_anova = stats.f_oneway(*groups)
    
    print(f"   ↳ F-Statistic: {f_stat:.4f}")
    print(f"   ↳ P-Value: {p_val_anova:.4e}")

    if p_val_anova > 0.05:
        print("⚠️ מסקנה: לא נמצא הבדל מובהק סטטיסטית בין השיטות (P > 0.05). אין טעם להמשיך למבחני זוגות.")
        return
    else:
        print("🌟 מסקנה: קיים הבדל מובהק בין לפחות שתי שיטות! (P < 0.05). עובר למבחן Tukey...")

    # 5. מבחן Post-Hoc: Tukey HSD (ראש בראש)
    print("\n⚔️ 2. מבצע מבחן Tukey HSD (ראש בראש)...")
    tukey_results = pairwise_tukeyhsd(endog=df_melt["AUC"], groups=df_melt["Method"], alpha=0.05)
    
    # המרת התוצאות ל-DataFrame קריא
    tukey_df = pd.DataFrame(data=tukey_results._results_table.data[1:], columns=tukey_results._results_table.data[0])
    
    # הדפסת התוצאות החשובות למסך
    print("\n🏆 תוצאות מובהקות בלבד (שיטות שניצחו/הפסידו באופן מובהק):")
    significant_pairs = tukey_df[tukey_df['reject'] == True]
    if significant_pairs.empty:
        print("   ↳ (אזהרה: המבחן הכללי יצא מובהק, אך אף זוג ספציפי לא עבר את רף ההחמרה של Tukey)")
    else:
        print(significant_pairs[['group1', 'group2', 'meandiff', 'p-adj']].to_string(index=False))

    # 6. יצירת מפת חום (Heatmap) של P-Values
    print("\n🎨 מייצר מפת חום (Heatmap) של P-Values למאמר...")
    methods = df_melt["Method"].unique()
    p_matrix = pd.DataFrame(np.ones((len(methods), len(methods))), index=methods, columns=methods)

    # מילוי המטריצה בערכי ה-P
    for _, row in tukey_df.iterrows():
        p_matrix.loc[row['group1'], row['group2']] = row['p-adj']
        p_matrix.loc[row['group2'], row['group1']] = row['p-adj'] # המטריצה סימטרית

    plt.figure(figsize=(12, 10))
    # מסכה כדי להראות רק חצי מטריצה (כי היא סימטרית)
    mask = np.triu(np.ones_like(p_matrix, dtype=bool))
    
    # ציור מפת החום (ירוק = מובהק, אדום = לא מובהק)
    cmap = sns.diverging_palette(10, 130, as_cmap=True)
    sns.heatmap(p_matrix, mask=mask, annot=True, fmt=".3f", cmap=cmap, vmin=0, vmax=0.1, 
                cbar_kws={'label': 'Tukey P-Value (Green = Significant)'}, 
                linewidths=1, linecolor='white')
    
    plt.title("Statistical Significance (Tukey HSD p-values) Between Methods", fontsize=16, fontweight='bold', pad=20)
    plt.xticks(rotation=45, ha='right')
    plt.yticks(rotation=0)
    
    # שמירת הגרף בתיקיית התוצאות
    heatmap_path = os.path.join(results_dir, "Statistical_P_Values_Heatmap.png")
    plt.savefig(heatmap_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    # שמירת טבלת התוצאות המלאה
    stats_csv_path = os.path.join(results_dir, "Tukey_HSD_Detailed_Results.csv")
    tukey_df.to_csv(stats_csv_path, index=False)
    
    print(f"💾 טבלת הסטטיסטיקה המלאה נשמרה ב: {stats_csv_path}")
    print(f"🖼️ מפת החום הסטטיסטית נשמרה ב: {heatmap_path}")
    print("\n✅ האנליזה הסטטיסטית הושלמה בהצלחה!")

if __name__ == "__main__":
    run_statistical_analysis()