import os
import glob
import pandas as pd

# 1. הגדר את הנתיב לתיקייה שבה נמצאים הקבצים שלך
data_folder = "../data"  # שנה את זה לנתיב האמיתי שלך במידת הצורך

# חיפוש כל קבצי ה-metadata
metadata_files = glob.glob(os.path.join(data_folder, "*_metadata.csv"))
print(f"🔍 Found {len(metadata_files)} metadata files to scan.\n")

target_col = "study_condition"
matching_studies = []

# 2. סריקת הקבצים
for file_path in metadata_files:
    study_name = os.path.basename(file_path).replace("_metadata.csv", "")
    
    try:
        # טעינת עמודת היעד בלבד כדי לחסוך בזיכרון וזמן ריצה
        df = pd.read_csv(file_path, usecols=lambda x: x.strip() == target_col)
        
        if target_col not in df.columns:
            continue  # דילוג אם העמודה לא קיימת בקובץ הספציפי הזה
            
        # שליפת ערכים ייחודיים (וניקוי ערכים ריקים או רווחים מיותרים)
        unique_vals = df[target_col].dropna().astype(str).str.strip().unique().tolist()
        
        # בדיקה האם יש יותר מ-2 ערכים שונים
        if len(unique_vals) > 2:
            matching_studies.append({
                "study": study_name,
                "count": len(unique_vals),
                "values": unique_vals
            })
            
    except Exception as e:
        print(f"⚠️ Could not process {study_name}: {str(e)}")

# 3. הצגת התוצאות
print("=" * 80)
print(f"📊 SUMMARY: Found {len(matching_studies)} studies with > 2 unique conditions")
print("=" * 80)

if matching_studies:
    for idx, res in enumerate(matching_studies, 1):
        print(f"{idx}. 📖 Study: {res['study']}")
        print(f"   🔹 Number of unique values: {res['count']}")
        print(f"   🔹 Different values found: {res['values']}")
        print("-" * 60)
else:
    print("✨ All scanned studies have 2 or fewer unique values in 'study_condition'.")