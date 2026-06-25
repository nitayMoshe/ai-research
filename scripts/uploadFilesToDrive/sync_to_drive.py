from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
import os

# --- הגדרות נתיבים ---
script_dir = os.path.dirname(os.path.abspath(__file__))

# התיקיות הלוקאליות שלנו במחשב (יוצאים מתיקיית scripts החוצה ונכנסים לתיקיות היעד)
LOCAL_DATA_FOLDER = os.path.normpath(os.path.join(script_dir, '..', '..',  'data'))
LOCAL_RESULTS_FOLDER = os.path.normpath(os.path.join(script_dir, '..', '..', 'results'))

# ה-IDs של התיקיות בדרייב (תצטרך להעתיק אותם מהדפדפן!)
# איך מוצאים? פותחים את התיקייה בדרייב (למשל DATA) ומעתיקים את הג'יבריש שבסוף שורת הכתובת
DRIVE_DATA_FOLDER_ID = '1Urv6CbnUpcxVYz0Hj6IWMASPU7NnrpSe'
DRIVE_RESULTS_FOLDER_ID = '1zPTIWCRNnh01ebXBKfJNWmlpb-ugyplq'

def authenticate_drive():
    """מטפל בכל האישורים מול גוגל"""
    gauth = GoogleAuth()
    gauth.settings['get_refresh_token'] = True 
    gauth.LoadCredentialsFile("mycreds.txt")
    
    if gauth.credentials is None:
        gauth.LocalWebserverAuth()
    elif gauth.access_token_expired:
        gauth.Refresh()
    else:
        gauth.Authorize()
    
    gauth.SaveCredentialsFile("mycreds.txt")
    return GoogleDrive(gauth)

def get_or_create_drive_folder(drive, folder_name, parent_id):
    """בודק אם תיקייה קיימת בדרייב. אם לא - יוצר אותה ומחזיר את ה-ID שלה."""
    query = f"title='{folder_name}' and '{parent_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
    file_list = drive.ListFile({'q': query}).GetList()
    
    if file_list:
        return file_list[0]['id'] # התיקייה קיימת
    else:
        # יצירת תיקייה חדשה
        folder_metadata = {
            'title': folder_name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [{'id': parent_id}]
        }
        folder = drive.CreateFile(folder_metadata)
        folder.Upload()
        return folder['id']

def sync_directory_recursive(drive, local_dir, drive_parent_id):
    """
    פונקציה חכמה שעוברת על התיקייה הלוקאלית. 
    אם היא נתקלת בקובץ -> מעלה אותו.
    אם היא נתקלת בתיקייה -> יוצרת אותה בדרייב ונכנסת פנימה (רקורסיה).
    """
    # קבלת כל הפריטים (קבצים ותיקיות) שכבר קיימים כרגע בנתיב הספציפי בדרייב
    query = f"'{drive_parent_id}' in parents and trashed=false"
    existing_items = drive.ListFile({'q': query}).GetList()
    
    # מיפוי פריטים קיימים כדי לחסוך קריאות ל-API ולמנוע כפילויות
    existing_files = {item['title']: item['id'] for item in existing_items if item['mimeType'] != 'application/vnd.google-apps.folder'}
    existing_folders = {item['title']: item['id'] for item in existing_items if item['mimeType'] == 'application/vnd.google-apps.folder'}

    for item_name in os.listdir(local_dir):
        if item_name.startswith('.'):
            continue # מתעלמים מקבצי מערכת נסתרים
            
        local_path = os.path.join(local_dir, item_name)

        if os.path.isfile(local_path):
            # טיפול בקובץ רגיל
            if item_name not in existing_files:
                print(f"📄 מעלה קובץ: {item_name}...")
                file_drive = drive.CreateFile({
                    'title': item_name,
                    'parents': [{'id': drive_parent_id}]
                })
                file_drive.SetContentFile(local_path)
                file_drive.Upload()
            else:
                print(f"⏩ קובץ {item_name} כבר קיים, מדלג.")
                
        elif os.path.isdir(local_path):
            # טיפול בתיקייה (למשל תיקיית הניסוי שנוצרה ב-results)
            print(f"📁 מטפל בתיקייה: {item_name}...")
            
            if item_name in existing_folders:
                folder_id = existing_folders[item_name]
            else:
                folder_id = get_or_create_drive_folder(drive, item_name, drive_parent_id)
            
            # קפיצה פנימה לתוך התיקייה (רקורסיה)
            sync_directory_recursive(drive, local_path, folder_id)

def main():
    print("--- 🚀 מערכת הגיבוי מתחילה ---")
    drive = authenticate_drive()
    
    # 1. סנכרון תיקיית ה-DATA
    if os.path.exists(LOCAL_DATA_FOLDER):
        print(f"\n[שלב 1/2] מתחיל סנכרון חומרי גלם (DATA) לדרייב...")
        sync_directory_recursive(drive, LOCAL_DATA_FOLDER, DRIVE_DATA_FOLDER_ID)
    else:
        print("\n[שלב 1/2] מדלג על סנכרון DATA (התיקייה לא קיימת או שה-ID לא עודכן בקוד).")

    # 2. סנכרון תיקיית ה-RESULTS
    if os.path.exists(LOCAL_RESULTS_FOLDER):
        print(f"\n[שלב 2/2] מתחיל סנכרון תוצאות הניתוח (RESULTS) לדרייב...")
        sync_directory_recursive(drive, LOCAL_RESULTS_FOLDER, DRIVE_RESULTS_FOLDER_ID)
    else:
        print("\n[שלב 2/2] מדלג על סנכרון RESULTS (התיקייה לא קיימת או שה-ID לא עודכן בקוד).")
        
    print("\n--- ✅ הגיבוי הושלם! המידע המיקרוביאלי נחת בשלום בדרייב המשותף. ---")

if __name__ == '__main__':
    main()