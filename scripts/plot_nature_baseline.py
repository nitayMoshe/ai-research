import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os

def plot_nature_baseline_only():
    # 1. הגדרת הנתיבים המעודכנים (פונה לתיקיית preProcessingResults)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    results_dir = os.path.normpath(os.path.join(script_dir, '..', 'preProcessingResults'))
    results_file = os.path.join(results_dir, 'Intra_Study_Results.csv') 
    
    if not os.path.exists(results_file):
        print(f"❌ Error: Cannot find {results_file}.")
        return

    # קריאת הנתונים וניקוי רווחים
    df = pd.read_csv(results_file)
    df.columns = df.columns.str.strip()

    # 2. המילון הבטוח ב-100% (הצלבה ודאית מתוך טבלאות S2 ו-S5 של Nature)
    nature_aucs = {
        'ZellerG_2014': 0.86,
        'FengQ_2015': 0.82,
        'YuJ_2015': 0.59,
        'YachidaS_2019': 0.71,
        'ThomasAM_2019_c': 0.83,
        'WirbelJ_2018': 0.915,   
        'HMP_2019_ibdmdb': 0.98, 
        'KarlssonFH_2013': 0.573, 
        'LeChatelierE_2013': 0.846 
    }

    # 3. סינון הטבלה רק למחקרים המשותפים
    df_plot = df[df['Study_ID'].isin(nature_aucs.keys())].copy()
    
    if df_plot.empty:
        print("❌ No matching studies found in your results table.")
        return

    # >>> כאן בוצע התיקון! התאמה מושלמת לשמות העמודות בקובץ ה-CSV שלך <<<
    possible_methods = ['Raw_Test', 'All_Combined_Test', 'Raw_Optuna_Test', 'Combined_Optuna_Test']
    methods_to_plot = [m for m in possible_methods if m in df_plot.columns]
    
    # הגנה: אם לא נמצאו עמודות בכלל
    if not methods_to_plot:
        print("❌ Error: Could not find the expected AUC columns in your CSV!")
        print("Columns available in your CSV are:", list(df.columns))
        return
        
    print(f"✅ Found the following methods to plot: {methods_to_plot}")
    
    df_melted = df_plot.melt(id_vars='Study_ID', value_vars=methods_to_plot, 
                             var_name='Method', value_name='AUC')

    # 4. יצירת הגרף
    plt.figure(figsize=(14, 8))
    sns.set_theme(style="whitegrid")
    
    # ציור עמודות הביצועים שלכם
    ax = sns.barplot(data=df_melted, x='Study_ID', y='AUC', hue='Method', palette='Blues')
    
    # הוספת הקו המסמל את התוצאה של Nature עבור כל מחקר
    for i, study in enumerate(df_plot['Study_ID'].unique()):
        nature_val = nature_aucs[study]
        plt.scatter(x=i, y=nature_val, color='red', marker='_', s=1000, linewidth=4, zorder=5)
        plt.text(i, nature_val + 0.01, f"Nature: {nature_val}", color='red', ha='center', fontweight='bold')

    plt.axhline(y=0.5, color='black', linestyle='--', alpha=0.5, label='Random Guess (0.5)')
    
    plt.title('Head-to-Head: Our Pipeline vs. Nature Paper Baseline', fontsize=16, fontweight='bold', pad=20)
    plt.xlabel('Dataset (Study ID)', fontsize=14)
    plt.ylabel('Test Set AUC', fontsize=14)
    plt.ylim(0.4, 1.0)
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    
    plt.tight_layout()
    # שמירת הגרף
    output_graph = os.path.join(results_dir, 'Nature_Baseline_Comparison.png')
    plt.savefig(output_graph, dpi=300)
    plt.close()
    
    print(f"✅ Graph successfully created at: {output_graph}")

if __name__ == "__main__":
    plot_nature_baseline_only()