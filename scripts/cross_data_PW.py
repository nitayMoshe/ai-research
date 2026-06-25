import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os
import glob
import random
from math import comb

def load_all_study_pathways(data_folder):
    """
    סורק את תיקיית הדאטה, קורא את קבצי הפיצ'רים, ומחלץ
    עבור כל מחקר את סט התהליכים (Pathways) הייחודיים שלו.
    """
    print("🔍 סורק קבצים ומחלץ תהליכים מכל המחקרים...")
    study_pathways = {}
    
    feature_files = glob.glob(os.path.join(data_folder, "*_features.csv"))
    
    for file_path in feature_files:
        # חילוץ שם המחקר
        study_name = os.path.basename(file_path).replace("_pathway_abundance_features.csv", "").replace("_features.csv", "")
        
        try:
            df = pd.read_csv(file_path, index_col=0, nrows=1) # קורא רק את השורה הראשונה (הכותרות) כדי לחסוך זיכרון
            pathways = set()
            
            for col in df.columns:
                if '|' in col:
                    pathway = col.split('|', 1)[0]
                    pathways.add(pathway)
            
            if pathways:
                study_pathways[study_name] = pathways
                
        except Exception as e:
            print(f"⚠️ שגיאה בקריאת הקובץ {study_name}: {e}")
            
    print(f"✅ נטענו בהצלחה {len(study_pathways)} מחקרים.")
    return study_pathways

def calculate_overlap_data(study_pathways, max_samples_per_k=50):
    """
    מחשב את חיתוך התהליכים עבור קומבינציות שונות של מחקרים (מ-1 עד N).
    מחשב הן את כמות התהליכים האבסולוטית והן את האחוז (מתוך איחוד התהליכים בקומבינציה).
    משתמש בדגימה סטטיסטית אקראית כדי למנוע קריסה חישובית.
    """
    studies = list(study_pathways.keys())
    N = len(studies)
    
    results = []
    
    # נעבור על כל ערך של K (מ-1 עד מספר המחקרים המקסימלי)
    for k in range(1, N + 1):
        print(f"⚙️ מחשב חפיפות עבור {k} מחקרים משולבים...")
        
        # חישוב מספר הקומבינציות האפשריות לבחירת K מחקרים מתוך N
        total_possible_combos = comb(N, k)
        
        # אם יש פחות מ-max_samples_per_k קומבינציות, נחשב את כולן.
        # אחרת, נדגום באופן אקראי max_samples_per_k קומבינציות ייחודיות.
        if total_possible_combos <= max_samples_per_k:
            import itertools
            combos = list(itertools.combinations(studies, k))
        else:
            combos_set = set()
            while len(combos_set) < max_samples_per_k:
                sampled = tuple(sorted(random.sample(studies, k)))
                combos_set.add(sampled)
            combos = list(combos_set)
            
        # חישוב החיתוך (Overlap) והאיחוד (Union) עבור כל קומבינציה שנדגמה
        for combo in combos:
            # מתחילים עם קבוצת התהליכים של המחקר הראשון בשילוב
            intersection = study_pathways[combo[0]]
            union_set = study_pathways[combo[0]]
            
            for study in combo[1:]:
                intersection = intersection.intersection(study_pathways[study])
                union_set = union_set.union(study_pathways[study])
            
            # חישוב מדד החפיפה באחוזים (Jaccard Index)
            overlap_count = len(intersection)
            total_unique_in_combo = len(union_set)
            
            # אם יש שני מחקרים חופפים לחלוטין, החיתוך שווה לאיחוד והתוצאה תהיה 100%
            overlap_pct = (overlap_count / total_unique_in_combo) * 100 if total_unique_in_combo > 0 else 0
            
            results.append({
                "Num_Datasets": k,
                "Overlap_Count": overlap_count,
                "Overlap_Percentage": overlap_pct
            })
            
    return pd.DataFrame(results)

def plot_swarm_and_save(df_results, output_dir):
    """
    מייצר ושומר שני גרפי Swarm Plot נפרדים:
    1. גרף אבסולוטי (כמות תהליכים חופפים)
    2. גרף יחסי באחוזים (מתוך סך התהליכים הייחודיים בקומבינציה)
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    N_unique = df_results["Num_Datasets"].nunique()
    
    # --- גרף 1: אבסולוטי (Absolute Overlap) ---
    print("📊 מייצר דיאגרמת Swarm Plot אבסולוטית...")
    plt.figure(figsize=(18, 10))
    sns.stripplot(
        data=df_results, 
        x="Num_Datasets", 
        y="Overlap_Count", 
        jitter=0.25, 
        size=4, 
        alpha=0.7, 
        palette="viridis", 
        hue="Num_Datasets",
        legend=False
    )
    plt.title("Pathway Overlap (Absolute Count) Across Combined Datasets", fontsize=16, fontweight='bold')
    plt.xlabel("Number of Combined Datasets (k)", fontsize=12)
    plt.ylabel("Number of Common Overlapping Pathways", fontsize=12)
    
    if N_unique > 20:
        step = max(1, N_unique // 20)
        ticks = range(0, N_unique, step)
        labels = [str(t + 1) for t in ticks]
        plt.xticks(ticks, labels)
        
    plt.grid(axis='y', linestyle='--', alpha=0.5)
    
    abs_image_path = os.path.join(output_dir, "pathway_overlap_swarm_absolute.png")
    plt.savefig(abs_image_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"✅ הגרף האבסולוטי נשמר בהצלחה בנתיב: {abs_image_path}")

    # --- גרף 2: אחוזי (Percentage Overlap - Jaccard Index) ---
    print("📊 מייצר דיאגרמת Swarm Plot אחוזית...")
    plt.figure(figsize=(18, 10))
    sns.stripplot(
        data=df_results, 
        x="Num_Datasets", 
        y="Overlap_Percentage", 
        jitter=0.25, 
        size=4, 
        alpha=0.7, 
        palette="plasma", 
        hue="Num_Datasets",
        legend=False
    )
    plt.title("Pathway Overlap (Jaccard Percentage) Across Combined Datasets", fontsize=16, fontweight='bold')
    plt.xlabel("Number of Combined Datasets (k)", fontsize=12)
    plt.ylabel("Overlap Percentage of Total Pathways in Combination (%)", fontsize=12)
    plt.ylim(-5, 105) # הגבלת הציר בין 0 ל-100 אחוזים
    
    if N_unique > 20:
        step = max(1, N_unique // 20)
        ticks = range(0, N_unique, step)
        labels = [str(t + 1) for t in ticks]
        plt.xticks(ticks, labels)
        
    plt.grid(axis='y', linestyle='--', alpha=0.5)
    
    pct_image_path = os.path.join(output_dir, "pathway_overlap_swarm_percentage.png")
    plt.savefig(pct_image_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"✅ הגרף האחוזי נשמר בהצלחה בנתיב: {pct_image_path}")

if __name__ == "__main__":
    # נתיבי הקלטים והפלטים דינמיים לפי מיקום הסקריפט הנוכחי (ROOT/scripts/pathway_overlap_swarm.py)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # עולים רמה אחת ל-ROOT ואז נכנסים לתיקיות האחיות data ו-results
    INPUT_DATA_DIR = os.path.normpath(os.path.join(script_dir, '..', 'data')) 
    OUTPUT_RESULTS_DIR = os.path.normpath(os.path.join(script_dir, '..', 'results'))
    
    # 1. טעינת הנתונים
    study_pathways = load_all_study_pathways(INPUT_DATA_DIR)
    
    if study_pathways:
        # 2. חישוב נתוני החפיפה (דוגם עד 50 קומבינציות לכל K כדי לרוץ מהר)
        df_results = calculate_overlap_data(study_pathways, max_samples_per_k=50)
        
        # שמירת הנתונים הגולמיים של הניסוי ל-CSV
        df_results.to_csv(os.path.join(OUTPUT_RESULTS_DIR, "pathway_overlap_data.csv"), index=False)
        print(f"📊 הנתונים הגולמיים נשמרו ב-pathway_overlap_data.csv")
        
        # 3. יצירת שני הציורים ושמירתם
        plot_swarm_and_save(df_results, OUTPUT_RESULTS_DIR)
    else:
        print("❌ לא נמצאו קבצי features מתאימים בתיקיית הנתונים.")