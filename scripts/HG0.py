import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os
import glob

def analyze_zero_distribution(data_folder):
    """
    עובר על כל קבצי המחקרים, ומחשב עבור כל תהליך (PW) 
    בכמה שורות/דגימות הוא קיבל ערך הגדול מ-0.
    """
    print("🔍 מתחיל לסרוק קבצים ולנתח את התפלגות הערכים...")
    feature_files = glob.glob(os.path.join(data_folder, "*_features.csv"))
    
    all_study_distributions = {}
    
    for file_path in feature_files:
        study_name = os.path.basename(file_path).replace("_pathway_abundance_features.csv", "").replace("_features.csv", "")
        
        try:
            # קריאת הקובץ המלא
            df = pd.read_csv(file_path, index_col=0)
            
            # סינון עמודות ששייכות ל-Pathways (מכילות '|')
            pw_cols = [c for c in df.columns if '|' in c]
            if not pw_cols:
                continue
                
            # יצירת מילוי בינארי: האם הערך גדול מ-0?
            is_nonzero = df[pw_cols] > 0
            
            # מיפוי עמודות משוננות (Stratified) לשם התהליך הבסיסי שלהן
            col_mapping = {c: c.split('|', 1)[0] for c in pw_cols}
            
            # תיקון תאימות לפנדס החדש: משחלפים (.T), מקבצים לפי שם התהליך, ומחזירים חזרה (.T)
            pathway_presence = is_nonzero.rename(columns=col_mapping).T.groupby(level=0).any().T
            
            # סכימה לאורך הציר האנכי: בכמה שורות (דגימות) התהליך קיים?
            nonzero_row_counts = pathway_presence.sum(axis=0)
            
            all_study_distributions[study_name] = nonzero_row_counts
            print(f"📊 {study_name}: נותחו {len(nonzero_row_counts)} תהליכים על פני {len(df)} שורות.")
            
        except Exception as e:
            print(f"⚠️ שגיאה בעיבוד המחקר {study_name}: {e}")
            
    return all_study_distributions

def plot_combined_histogram(all_study_distributions, output_dir):
    """
    מייצר גרף המשלב את ההיסטוגרמות של כל המחקרים יחד באמצעות קווים עדינים.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    print("\n📊 מייצר את הגרף המשולב בתיקיית היעד...")
    plt.figure(figsize=(16, 9))
    
    for study_name, counts in all_study_distributions.items():
        val_counts = counts.value_counts().sort_index()
        
        # שימוש בקווי תדירות (Frequency Polygon) עם שקיפות כדי למנוע עומס ויזואלי
        plt.plot(
            val_counts.index, 
            val_counts.values, 
            alpha=0.25, 
            linewidth=1.5, 
            color='royalblue'
        )
        
    plt.title("Distribution of Non-Zero Row Counts per Pathway Across All Datasets", fontsize=16, fontweight='bold')
    plt.xlabel("Number of Non-Zero Rows (Samples where PW > 0)", fontsize=12)
    plt.ylabel("Number of Pathways (Count)", fontsize=12)
    
    plt.grid(True, linestyle='--', alpha=0.5)
    
    plt.text(
        0.02, 0.95, 
        f"Total Datasets Plotted: {len(all_study_distributions)}\nEach line represents one standalone study", 
        transform=plt.gca().transAxes, 
        fontsize=11, 
        verticalalignment='top',
        bbox=dict(boxstyle='round', facecolor='white', alpha=0.8)
    )
    
    output_path = os.path.join(output_dir, "global_pathway_sparsity_histogram.png")
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"✅ הגרף המשולב נשמר בהצלחה בנתיב: {output_path}")

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    INPUT_DATA_DIR = os.path.normpath(os.path.join(script_dir, '..', 'data'))
    OUTPUT_RESULTS_DIR = os.path.normpath(os.path.join(script_dir, '..', 'HG0RESULTS'))
    
    distributions = analyze_zero_distribution(INPUT_DATA_DIR)
    
    if distributions:
        plot_combined_histogram(distributions, OUTPUT_RESULTS_DIR)
        
        summary_data = []
        for study, counts in distributions.items():
            summary_data.append({
                "Study": study,
                "Total_Pathways": len(counts),
                "Avg_NonZero_Rows_Per_PW": round(counts.mean(), 2),
                "Max_NonZero_Rows": counts.max()
            })
        df_summary = pd.DataFrame(summary_data)
        df_summary.to_csv(os.path.join(OUTPUT_RESULTS_DIR, "studies_sparsity_summary.csv"), index=False)
        print(f"📊 קובץ סיכום נתונים נשמר ב: studies_sparsity_summary.csv")
        
    else:
        print("❌ לא נמצאו נתונים מתאימים לעיבוד.")