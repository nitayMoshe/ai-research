from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
import os

# --- הגדרות ---
# 1. מוצא את התיקייה שבה נמצא הסקריפט הנוכחי (למשל: python_script/)
script_dir = os.path.dirname(os.path.abspath(__file__))

# 2. מגדיר את הנתיב לתיקיית ה-data (עולה רמה אחת למעלה ל-Root, ואז נכנס ל-data)
LOCAL_FOLDER = os.path.normpath(os.path.join(script_dir, '..', 'data'))

# ה-ID של התיקייה בדרייב
DRIVE_FOLDER_ID = '1Ym3YEKAq7DPp8J0A-sfXD_-xmbw_ORZ_'

def sync_to_drive():
    # בדיקה שהתיקייה קיימת
    if not os.path.exists(LOCAL_FOLDER):
        print(f"שגיאה: לא נמצאה תיקייה בנתיב: {LOCAL_FOLDER}")
        return

    # אתחול האוטנטיקציה
    gauth = GoogleAuth()
    
    # טעינת אישורים קיימים
    gauth.LoadCredentialsFile("mycreds.txt")
    
    if gauth.credentials is None:
        # אם אין אישור, פתח דפדפן לבקש אישור
        gauth.LocalWebserverAuth()
    elif gauth.access_token_expired:
        gauth.Refresh()
    else:
        gauth.Authorize()
    
    # שמירה לפעם הבאה
    gauth.SaveCredentialsFile("mycreds.txt")
    
    drive = GoogleDrive(gauth)

    print(f"--- מתחיל סנכרון מול תיקיית: {LOCAL_FOLDER} ---")

    # קבלת רשימת הקבצים הקיימים בדרייב (סינון לפי התיקייה שקבענו)
    file_list = drive.ListFile({'q': f"'{DRIVE_FOLDER_ID}' in parents and trashed=false"}).GetList()
    existing_files = {f['title'] for f in file_list}

    # מעבר על הקבצים בתיקיית ה-data המקומית
    for filename in os.listdir(LOCAL_FOLDER):
        # מתעלמים מתיקיות נסתרות או קבצי מערכת
        if filename.startswith('.'):
            continue
            
        if filename not in existing_files:
            print(f"מעלה: {filename}...")
            # יצירת אובייקט קובץ בגוגל דרייב
            file = drive.CreateFile({
                'title': filename, 
                'parents': [{'id': DRIVE_FOLDER_ID}]
            })
            file.SetContentFile(os.path.join(LOCAL_FOLDER, filename))
            file.Upload()
            print(f"הועלה בהצלחה!")
        else:
            print(f"{filename} כבר קיים בדרייב, מדלג.")

    print("--- הסנכרון הסתיים ---")

if __name__ == '__main__':
    sync_to_drive()