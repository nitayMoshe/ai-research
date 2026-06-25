import pandas as pd
import os
import glob

def extract_core_and_pan_pathways(data_folder, output_folder):
    """
    סורק את כל קבצי הפיצ'רים, מחלץ את התהליך (Pathway) ללא שם החיידק,
    מחשב את ה-Core (החיתוך של כולם) ואת שאר התהליכים המשתנים עם מדד השכיחות שלהם.
    """
    print("🔍 סורק את קבצי הפיצ'רים ומחלץ תהליכים...")
    
    # מילון שישמור עבור כל מחקר את קבוצת התהליכים שלו
    study_pathways = {}
    feature_files = glob.glob(os.path.join(data_folder, "*_features.csv"))
    
    if not feature_files:
        print("❌ שגיאה: לא נמצאו קבצי features בתיקיית המקור.")
        return
        
    for file_path in feature_files:
        study_name = os.path.basename(file_path).replace("_pathway_abundance_features.csv", "").replace("_features.csv", "")
        
        try:
            # קריאת השורה הראשונה בלבד (כותרות העמודות) כדי לחסוך בזיכרון וזמן ריצה
            df = pd.read_csv(file_path, index_col=0, nrows=1)
            pathways = set()
            
            for col in df.columns:
                if '|' in col:
                    # חיתוך לפי '|' כדי לקבל רק את שם התהליך (בלי החיידק)
                    pathway = col.split('|', 1)[0]
                    pathways.add(pathway)
            
            if pathways:
                study_pathways[study_name] = pathways
                
        except Exception as e:
            print(f"⚠️ שגיאה בקריאת המחקר {study_name}: {e}")

    num_studies = len(study_pathways)
    print(f"📋 נטענו בהצלחה {num_studies} מחקרים.")

    # 1. חישוב ה-Core (חיתוך מתמטי של כל הקבוצות - "הליבה האוניברסלית")
    all_studies_sets = list(study_pathways.values())
    core_pathways = set.intersection(*all_studies_sets)
    print(f"🌟 נמצאו {len(core_pathways)} תהליכי ליבה המשותפים לכל {num_studies} הניסויים!")

    # 2. חישוב איחוד כל התהליכים (כל מה שקיים לפחות במחקר אחד)
    union_pathways = set.union(*all_studies_sets)
    
    # 3. תהליכים שאינם בליבה
    non_core_pathways = union_pathways - core_pathways

    # 4. חישוב שכיחות (בכמה מחקרים מופיע כל תהליך שאינו בליבה)
    pathway_frequencies = []
    for pway in non_core_pathways:
        count = sum(1 for study_set in all_studies_sets if pway in study_set)
        percentage = (count / num_studies) * 100
        pathway_frequencies.append({
            "Pathway_Name": pway,
            "Appears_In_Datasets": count,
            "Total_Datasets": num_studies,
            "Ubiquity_Percentage": round(percentage, 2)
        })

    # יצירת תיקיית התוצאות אם אינה קיימת
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # שמירת קובץ 1: תהליכי הליבה
    df_core = pd.DataFrame(sorted(list(core_pathways)), columns=["Universal_Core_Pathway"])
    core_file_path = os.path.join(output_folder, "universal_core_pathways.csv")
    df_core.to_csv(core_file_path, index=False)
    print(f"💾 רשימת תהליכי הליבה נשמרה בנתיב: {core_file_path}")

    # שמירת קובץ 2: התהליכים המשתנים (ממוינים מהשכיח ביותר להכי פחות שכיח)
    df_non_core = pd.DataFrame(pathway_frequencies)
    df_non_core = df_non_core.sort_values(by="Appears_In_Datasets", ascending=False)
    non_core_file_path = os.path.join(output_folder, "variable_non_core_pathways.csv")
    df_non_core.to_csv(non_core_file_path, index=False)
    print(f"💾 רשימת התהליכים המשתנים ושכיחותם נשמרה בנתיב: {non_core_file_path}")
    
    # כתיבת סיכום קצר לקובץ טקסט
    with open(os.path.join(output_folder, "pathway_extraction_summary.txt"), "w", encoding="utf-8") as f:
        f.write("=== סיכום ניתוח קבוצות תהליכים ===\n")
        f.write(f"סה\"כ מחקרים שנותחו: {num_studies}\n")
        f.write(f"תהליכים אוניברסליים (Core): {len(core_pathways)}\n")
        f.write(f"תהליכים משתנים (Variable/Pan): {len(non_core_pathways)}\n")
        f.write(f"סה\"כ תהליכים ייחודיים שזוהו בפרויקט: {len(union_pathways)}\n")

if __name__ == "__main__":
    # הגדרת נתיבים דינמית לפי מיקום הסקריפט בתיקיית scripts
    script_dir = os.path.dirname(os.path.abspath(__file__))
    INPUT_DATA_DIR = os.path.normpath(os.path.join(script_dir, '..', 'data'))
    OUTPUT_RESULTS_DIR = os.path.normpath(os.path.join(script_dir, '..', 'results'))
    
    extract_core_and_pan_pathways(INPUT_DATA_DIR, OUTPUT_RESULTS_DIR)