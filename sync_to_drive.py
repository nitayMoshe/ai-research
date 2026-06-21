from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
import os

# --- הגדרות ---
LOCAL_FOLDER = r'C:\Users\User\Desktop\Research\downloadScript\data_output'
DRIVE_FOLDER_ID = '1Ym3YEKAq7DPp8J0A-sfXD_-xmbw_ORZ_'

def sync_to_drive():
    # אתחול האוטנטיקציה
    gauth = GoogleAuth()
    
    # ניסיון טעינת שמירה קודמת (כדי לא לבקש אישור כל פעם)
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

    print("--- מתחיל סנכרון ---")

    # קבלת רשימת הקבצים בדרייב
    file_list = drive.ListFile({'q': f"'{DRIVE_FOLDER_ID}' in parents and trashed=false"}).GetList()
    existing_files = {f['title'] for f in file_list}

    for filename in os.listdir(LOCAL_FOLDER):
        if filename.startswith('.'): continue
            
        if filename not in existing_files:
            print(f"מעלה: {filename}...")
            file = drive.CreateFile({'title': filename, 'parents': [{'id': DRIVE_FOLDER_ID}]})
            file.SetContentFile(os.path.join(LOCAL_FOLDER, filename))
            file.Upload()
            print(f"הועלה בהצלחה!")
        else:
            print(f"{filename} כבר קיים.")


if __name__ == '__main__':
    sync_to_drive()