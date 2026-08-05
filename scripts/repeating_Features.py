import pandas as pd
import glob
import os
from collections import Counter

def extract_metadata_features_frequency():
    # הגדרת נתיב לתיקיית הנתונים (רמה אחת מעל הסקריפט)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.normpath(os.path.join(script_dir, '..', 'data'))
    
    # איסוף כל קבצי המטאדאטה
    metadata_files = glob.glob(os.path.join(data_dir, "*_metadata.csv"))
    
    if not metadata_files:
        print("❌ No metadata files found!")
        return

    all_features = []
    print(f"🔍 Analyzing {len(metadata_files)} metadata tables...")
    
    # מעבר על כל קובץ ושליפת שמות העמודות (הפיצ'רים)
    for file_path in metadata_files:
        try:
            # קוראים רק את השורה הראשונה (nrows=0) כדי לשלוף עמודות ביעילות
            df = pd.read_csv(file_path, index_col=0, nrows=0)
            all_features.extend(df.columns.tolist())
        except Exception as e:
            print(f"⚠️ Error reading {os.path.basename(file_path)}: {e}")

    # ספירת התדירות של כל פיצ'ר
    feature_counts = Counter(all_features)
    
    # המרה לדאטה-פריים ומיון מהנפוץ לנדיר
    df_results = pd.DataFrame(feature_counts.items(), columns=['Feature_Name', 'Appearance_Count'])
    df_results = df_results.sort_values(by='Appearance_Count', ascending=False).reset_index(drop=True)
    
    # הוספת עמודת אחוזים (נוח כדי לראות את התמונה הגדולה)
    total_files = len(metadata_files)
    df_results['Appearance_Percentage'] = (df_results['Appearance_Count'] / total_files * 100).round(1).astype(str) + '%'
    
    # שמירת התוצאה לקובץ מרוכז
    output_path = os.path.join(data_dir, "Metadata_Features_Frequency.csv")
    df_results.to_csv(output_path, index=False)
    
    print(f"✅ Success! Found {len(df_results)} unique features across {total_files} tables.")
    print(f"💾 File saved to: {output_path}")
    print("\nTop 5 Most Common Features:")
    print(df_results.head())

if __name__ == "__main__":
    extract_metadata_features_frequency()