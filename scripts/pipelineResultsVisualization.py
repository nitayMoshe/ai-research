import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os

def generate_auc_comparison_plot():
    print("="*60)
    print("📊 MICROBIOME ML: TEST AUC VISUALIZATION")
    print("="*60)

    # 1. הגדרת נתיבים (מחפש את הקובץ בתיקיית preProcessingResults או בתיקייה הנוכחית)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    results_dir = os.path.normpath(os.path.join(script_dir, '..', 'preProcessingResults'))
    csv_path = os.path.join(results_dir, "Intra_Study_Results.csv")
    
    # חיפוש חלופי אם הקובץ נמצא באותה תיקייה עם הסקריפט
    if not os.path.exists(csv_path):
        csv_path = "Intra_Study_Results.csv"
        if not os.path.exists(csv_path):
            print(f"❌ שגיאה: לא מצאתי את הקובץ {csv_path}.")
            print("אנא ודא שקובץ התוצאות מהסקריפט הקודם נמצא בתיקייה הנכונה.")
            return

    # 2. טעינת הנתונים
    print(f"📂 טוען נתונים מהקובץ: {csv_path}...")
    df = pd.read_csv(csv_path)

    # 3. סינון נתוני ה-Test בלבד (כדי לא להעמיס על הגרף)
    test_cols = [c for c in df.columns if c.endswith("_Test")]
    df_test = df[['Study_ID'] + test_cols]

    # הפיכת הטבלה לצורה ארוכה (Long format) שמתאימה לגרפים של Seaborn
    df_melt = df_test.melt(id_vars=["Study_ID"], value_vars=test_cols, var_name="Method", value_name="AUC")
    
    # ניקוי שמות השיטות (הורדת המילה "_Test" כדי שהתוויות יהיו נקיות)
    df_melt["Method"] = df_melt["Method"].str.replace("_Test", "")

    # 4. מיון השיטות מהגרועה לטובה ביותר (לפי חציון ה-AUC)
    # זה יוצר סיפור ויזואלי ברור של שיפור
    median_scores = df_melt.groupby("Method")["AUC"].median().sort_values()
    sorted_methods = median_scores.index.tolist()

    # 5. יצירת הגרף (Boxplot + Swarmplot)
    print("🎨 מצייר את הגרף המשולב...")
    plt.figure(figsize=(16, 8)) # גודל רחב וקריא
    
    # סגנון רקע יפה
    sns.set_theme(style="whitegrid", rc={"grid.linestyle": "--", "axes.edgecolor": "black"})

    # א. שכבת הבסיס: תרשים קופסה (צבעים עדינים)
    sns.boxplot(
        data=df_melt, 
        x="Method", 
        y="AUC", 
        order=sorted_methods, 
        color="whitesmoke", 
        fliersize=0, # מעלימים את החריגים של הקופסה כי נצייר אותם בנחיל
        linewidth=1.5
    )

    # ב. השכבה העליונה: דיאגרמת נחיל (כל מחקר הוא נקודה)
    sns.swarmplot(
        data=df_melt, 
        x="Method", 
        y="AUC", 
        order=sorted_methods, 
        palette="rocket", # פלטת צבעים מרשימה מהכהה לבהיר
        size=6, 
        alpha=0.8,
        edgecolor="black",
        linewidth=0.5
    )

    # 6. עיצוב וטקסטים
    plt.title("Comparative Performance of ML Preprocessing Methods (Test AUC)", fontsize=18, fontweight='bold', pad=20)
    plt.xlabel("Preprocessing & Training Method", fontsize=14, fontweight='bold')
    plt.ylabel("Test AUC (Hold-out)", fontsize=14, fontweight='bold')
    
    # קו אדום מקווקו המייצג ניחוש אקראי (AUC = 0.5)
    plt.axhline(0.5, color='red', linestyle='--', linewidth=2, label='Random Guess (AUC 0.5)')
    plt.legend(loc="lower right", fontsize=12)

    # סיבוב של שמות השיטות למטה כדי שיהיה קל לקרוא אותן
    plt.xticks(rotation=35, ha='right', fontsize=11)
    plt.yticks(fontsize=11)
    
    # הגבלת ציר ה-Y להצגה פרופורציונלית (קצת מתחת ל-0.5 ועד 1.05)
    plt.ylim(0.35, 1.05)
    plt.tight_layout()

    # 7. שמירת הגרף בתיקיית התוצאות
    output_path = os.path.join(results_dir, "Test_AUC_Methods_Comparison.png")
    # אם תיקיית התוצאות לא קיימת, נשמור בתיקייה הנוכחית
    if not os.path.exists(results_dir):
         output_path = "Test_AUC_Methods_Comparison.png"
         
    plt.savefig(output_path, dpi=300)
    plt.close()

    print(f"✅ הגרף המרהיב נשמר בהצלחה בנתיב:\n{output_path}")
    print("="*60)

if __name__ == "__main__":
    generate_auc_comparison_plot()