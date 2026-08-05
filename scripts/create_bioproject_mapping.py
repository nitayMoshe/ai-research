import os
import glob
import pandas as pd
import requests
import time
import re

def build_bioproject_dictionary():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.normpath(os.path.join(script_dir, '..', 'data'))
    results_dir = os.path.normpath(os.path.join(script_dir, '..', 'preProcessingResults'))

    if not os.path.exists(results_dir):
        os.makedirs(results_dir)

    metadata_files = glob.glob(os.path.join(data_dir, "*_metadata.csv"))
    print(f"🔍 Found {len(metadata_files)} metadata files to process...\n")

    mapping_data = []

    for file_path in metadata_files:
        study_name = os.path.basename(file_path).replace("_metadata.csv", "")

        try:
            df = pd.read_csv(file_path)

            if 'NCBI_accession' not in df.columns:
                print(f"⚠️ Warning: 'NCBI_accession' not found in {study_name}. Skipping API check.")
                continue

            # --- התיקון הקריטי: הוספת [0] בשני המקומות ---
            first_accession = str(df['NCBI_accession'].dropna().iloc[0])
            clean_accession = first_accession.split(';')[0].strip()

            print(f"⏳ Querying NCBI for {study_name} (Run: {clean_accession})...")

            search_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=sra&term={clean_accession}&retmode=json"
            search_res = requests.get(search_url).json()
            id_list = search_res.get('esearchresult', {}).get('idlist', [])

            if not id_list:
                print(f"   ❌ No SRA record found for {clean_accession}")
                mapping_data.append({'Study_ID': study_name, 'SRA_Run': clean_accession, 'BioProject_ID': 'Not_Found'})
                continue

            # --- תיקון נוסף: לקיחת ה-ID הראשון מתוך רשימת התוצאות שחזרה מהשרת ---
            sra_internal_id = id_list[0]

            summary_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=sra&id={sra_internal_id}&retmode=json"
            summary_res = requests.get(summary_url).json()

            exp_xml = summary_res.get('result', {}).get(sra_internal_id, {}).get('expxml', '')
            match = re.search(r'<Bioproject>([^<]+)</Bioproject>', exp_xml, re.IGNORECASE)

            if match:
                bioproject = match.group(1)
                print(f"   ✅ Found: {bioproject}")
                mapping_data.append({'Study_ID': study_name, 'SRA_Run': clean_accession, 'BioProject_ID': bioproject})
            else:
                print(f"   ❌ BioProject not found in XML for {clean_accession}")
                mapping_data.append({'Study_ID': study_name, 'SRA_Run': clean_accession, 'BioProject_ID': 'Not_Found'})

            time.sleep(0.5)

        except Exception as e:
            print(f"   ⚠️ Error processing {study_name}: {e}")

    # הזרקה ידנית של מחקרים שחסרים במטא-דאטה אך ידועים לנו מראש
    print("\n💉 Injecting known BioProjects without NCBI_accession columns...")
    mapping_data.append({'Study_ID': 'HMP_2019_ibdmdb', 'SRA_Run': 'Manual_Override', 'BioProject_ID': 'PRJNA385949'})
    
    df_mapping = pd.DataFrame(mapping_data)
    output_file = os.path.join(results_dir, 'Study_to_BioProject_Dictionary.csv')
    df_mapping.to_csv(output_file, index=False)

    print("\n" + "="*60)
    print(f"🎉 Mapping Complete! Bridge table saved to:\n{output_file}")
    print("="*60)

if __name__ == "__main__":
    build_bioproject_dictionary()