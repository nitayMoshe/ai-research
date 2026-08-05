import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os

def parse_nature_s7_matrix(filepath):
    """
    קורא את הקובץ של Nature כמקשה אחת, מזהה את חסימות הנתונים (המחלות השונות)
    ומחלץ רק את האלכסון (Intra-Study AUC) שבו המחקר אומן ונבדק על עצמו.
    """
    df = pd.read_csv(filepath, header=None, skiprows=6)
    intra_aucs = {}
    current_headers = []
    
    for _, row in df.iterrows():
        col0 = str(row[0]).strip()
        
        # זיהוי שורת כותרת
        if pd.isna(row[0]) and not pd.isna(row[1]):
            current_headers = [str(x).strip() for x in row.values]
            continue
            
        # חילוץ נתוני האלכסון
        if pd.notna(row[0]) and current_headers:
            if col0 in current_headers:
                idx = current_headers.index(col0)
                val = row[idx]
                if pd.notna(val) and str(val).strip().lower() != 'nan':
                    try:
                        intra_aucs[col0.upper()] = float(val)
                    except ValueError:
                        pass
                        
    return pd.DataFrame(list(intra_aucs.items()), columns=['Study_ID', 'AUC'])

def generate_dynamic_s7_comparison():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # הגדרת התיקיות
    supp_dir = os.path.normpath(os.path.join(script_dir, '..', 'Supplementary_Material'))
    results_dir = os.path.normpath(os.path.join(script_dir, '..', 'preProcessingResults'))

    # 1. טעינת הקבצים שלנו
    our_results_path = os.path.join(results_dir, 'Intra_Study_Results.csv')
    
    if not os.path.exists(our_results_path):
        print(f"❌ Error: Could not find your results file at '{our_results_path}'.")
        return

    df_ours = pd.read_csv(our_results_path)
    df_ours['Study_ID'] = df_ours['Study_ID'].astype(str).str.strip().str.upper()

    # === איתור אוטומטי של המודל המנצח לכל מחקר ===
    test_columns = [col for col in df_ours.columns if col.endswith('_Test')]
    
    if not test_columns:
        print("❌ Error: Could not find any columns ending with '_Test' in your results.")
        return
        
    df_ours['Our_Best_AUC'] = df_ours[test_columns].max(axis=1)
    df_ours['Our_Best_Model_Name'] = df_ours[test_columns].idxmax(axis=1)

    # 2. טעינה חכמה של קובצי S7 
    s7_taxon_path = os.path.join(supp_dir, 'Table-S7-AUC_taxon.csv')
    s7_pathway_path = os.path.join(supp_dir, 'Table-S7-AUC_pathway.csv')
    s7_both_path = os.path.join(supp_dir, 'Table-S7-AUC_both.csv')

    print("🧹 Parsing Nature S7 matrices and extracting Intra-Study AUCs...")
    
    df_taxon = parse_nature_s7_matrix(s7_taxon_path).rename(columns={'AUC': 'Nature_Taxon'})
    df_pathway = parse_nature_s7_matrix(s7_pathway_path).rename(columns={'AUC': 'Nature_Pathway'})
    df_both = parse_nature_s7_matrix(s7_both_path).rename(columns={'AUC': 'Nature_Both'})

    # 3. המיזוג הישיר (Direct Merge)
    df_merged = pd.merge(df_ours, df_taxon, on='Study_ID', how='inner')
    df_merged = pd.merge(df_merged, df_pathway, on='Study_ID', how='inner')
    df_merged = pd.merge(df_merged, df_both, on='Study_ID', how='inner')

    print(f"📊 Final matching studies for comparison: {len(df_merged)}")

    if df_merged.empty:
        print("\n❌ Merge resulted in an empty table.")
        return

    # === יצירת תווית חכמה לציר ה-X עם שם המודל המנצח ===
    # מסירים את הסיומת "_Test" כדי ששם המודל ייראה נקי יותר בגרף
    df_merged['Clean_Model_Name'] = df_merged['Our_Best_Model_Name'].str.replace('_Test', '', regex=False)
    
    # חיבור שם המחקר עם השם של המודל לשורה אחת כפולה
    df_merged['Study_Display'] = df_merged.apply(
        lambda r: f"{r['Study_ID']}\n🏆 {r['Clean_Model_Name']}", axis=1
    )

    # 4. הכנת הנתונים לגרף 
    methods_to_plot = ['Our_Best_AUC', 'Nature_Taxon', 'Nature_Pathway', 'Nature_Both']
    
    # שימו לב שכעת אנחנו ממזגים על בסיס העמודה החדשה 'Study_Display'
    df_melted = df_merged.melt(id_vars='Study_Display', value_vars=methods_to_plot, 
                               var_name='Method', value_name='AUC')

    # שינוי השמות לתצוגה יפה בגרף
    rename_dict = {
        'Our_Best_AUC': 'Our Best Pipeline (Model Named on X-Axis)',
        'Nature_Taxon': 'Nature Paper (Taxon Only)',
        'Nature_Pathway': 'Nature Paper (Pathway Only)',
        'Nature_Both': 'Nature Paper (Taxon + Pathway)'
    }
    df_melted['Method'] = df_melted['Method'].map(rename_dict)

    # 5. יצירת הגרף ההשוואתי
    plt.figure(figsize=(16, 9)) # הגדלתי מעט את הגובה כדי שיהיה מקום לטקסט למטה
    sns.set_theme(style="whitegrid")
    
    palette = ['#2980b9', '#e74c3c', '#e67e22', '#8e44ad']
    
    ax = sns.barplot(data=df_melted, x='Study_Display', y='AUC', hue='Method', palette=palette)
    
    plt.axhline(y=0.5, color='black', linestyle='--', alpha=0.5, label='Random Guess (0.5)')
    
    plt.title('Head-to-Head: Our Auto-Selected Best Pipeline vs. Nature Paper', fontsize=18, fontweight='bold', pad=20)
    plt.xlabel('Dataset (Study ID) & Winning Model', fontsize=14, labelpad=15)
    plt.ylabel('Test Set AUC', fontsize=14)
    plt.ylim(0.4, 1.05) # נתתי קצת יותר אוויר למעלה כדי שהתוויות לא ייחתכו
    
    # עיצוב הטקסט על ציר ה-X כדי ששם המודל יהיה בולט וקריא
    plt.xticks(fontsize=10, fontweight='medium')
    
    plt.legend(title='Model Type', bbox_to_anchor=(1.05, 1), loc='upper left')
    
    # הוספת התוויות המדויקות מעל העמודות
    for p in ax.patches:
        height = p.get_height()
        if pd.notnull(height) and height > 0:
            ax.annotate(f'{height:.2f}', 
                        (p.get_x() + p.get_width() / 2., height), 
                        ha='center', va='bottom', 
                        fontsize=10, color='black', xytext=(0, 5), 
                        textcoords='offset points')
    
    plt.tight_layout()
    output_graph = os.path.join(results_dir, 'Nature_S7_Dynamic_Comparison.png')
    plt.savefig(output_graph, dpi=300)
    plt.close()
    
    print(f"✅ Victory Graph successfully created at: {output_graph}")

if __name__ == "__main__":
    generate_dynamic_s7_comparison()