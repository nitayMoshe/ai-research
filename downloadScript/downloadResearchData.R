# ==============================================================================
# סקריפט הורדה אוטומטי - פרויקט המיקרוביום
# ה-Avengers Initiative של הורדת הנתונים
# ==============================================================================

# וודא שהספריות מותקנות לפני ההרצה הראשונה:
# BiocManager::install("curatedMetagenomicData")
library(curatedMetagenomicData)
library(SummarizedExperiment)

# ------------------------------------------------------------------------------
# 1. הגדרות תצורה (Configuration)
# ------------------------------------------------------------------------------

# כאן תכניס את כל 93 השמות של הניסויים שאושרית ביקשה. 
# בינתיים שמתי פה 3 קלאסיים לדוגמה:
all_studies <- c("AsnicarF_2017", "AsnicarF_2021", "BackhedF_2015", "BedarfJR_2017", "Bengtsson-PalmeJ_2015", "BritoIL_2016"
                 , "BrooksB_2017", "Castro-NallarE_2015", "ChengpingW_2017", "ChngKR_2016", "ChuDM_2017", "CosteaPI_2017", "DavidLA_2015", 
                 "DeFilippisF_2019", "DhakanDB_2019", "FengQ_2015", "FerrettiP_2018", "FrankelAE_2017", "GhensiP_2019", "GopalakrishnanV_2018", 
                 "GuptaA_2019", "HMP_2012", "HMP_2019_ibdmdb", "HMP_2019_t2d", "HallAB_2017", "HanniganGD_2017", "HansenLBS_2018", "Heitz-BuschartA_2016",
                 "IaniroG_2022", "IjazUZ_2017", "JieZ_2017", "KarlssonFH_2013", "KaurK_2020", "KeohaneDM_2020", "KieserS_2018", "KosticAD_2015", 
                 "LassalleF_2017", "LeChatelierE_2013", "LeeKA_2022", "LiJ_2014", "LiJ_2017", "LiSS_2016", "LifeLinesDeep_2016", "LiuW_2016", "LokmerA_2019",
                 "LomanNJ_2013", "LoombaR_2017", "LouisS_2016", "MatsonV_2018", "MehtaRS_2018", "MetaCardis_2020_a", "NagySzakalD_2017",
                 "NielsenHB_2014", "Obregon-TitoAJ_2015", "OhJ_2014", "OlmMR_2017", "PasolliE_2019", "PehrssonE_2016", "PetersBA_2019", 
                 "QinJ_2012", "QinN_2014", "RampelliS_2015", "RaymondF_2016", "RosaBA_2018", "RubelMA_2020", "SankaranarayananK_2015", "SchirmerM_2016",
                 "ShaoY_2019", "ShiB_2015", "SmitsSA_2017", "TettAJ_2016", "TettAJ_2019_a", "TettAJ_2019_b", "TettAJ_2019_c", "ThomasAM_2018a", "ThomasAM_2018b",
                 "ThomasAM_2019_c", "VatanenT_2016", "VilaAV_2018", "VincentC_2016", "VogtmannE_2016", "WampachL_2018", "WindTT_2020", "WirbelJ_2018", "XieH_2016",
                 "YachidaS_2019", "YassourM_2016", "YassourM_2018", "YeZ_2018", "YuJ_2015", "ZeeviD_2015", "ZellerG_2014", "ZhuF_2020") 

# איזה סוג מידע אנחנו רוצים להוריד? (למשל: pathway_abundance או relative_abundance)
target_feature_type <- "pathway_abundance"

# התיקייה שבה יישמרו כל קבצי ה-CSV
output_dir <- file.path("..", "data")

# קובץ הלוגים שיגיד לנו מי הצליח ומי נכשל (נשמר בתיקיית העבודה הנוכחית)
log_file <- "download_log.txt"

# ------------------------------------------------------------------------------
# 2. הכנות לפני הקרב
# ------------------------------------------------------------------------------

# יצירת התיקייה אם היא עדיין לא קיימת
if (!dir.exists(output_dir)) { 
  dir.create(output_dir, showWarnings = FALSE, recursive = TRUE) 
}

# איפוס קובץ הלוג
write(paste("--- Starting Batch Download Process:", Sys.time(), "---"), log_file)
write(paste("Target Feature Type:", target_feature_type), log_file, append = TRUE)

# ------------------------------------------------------------------------------
# 3. הפונקציה המרכזית (מטפלת בניסוי בודד אחד בכל פעם)
# ------------------------------------------------------------------------------

download_single_study <- function(study_name, feature_type, out_dir, log_path) {
  
  # tryCatch: ה"קסדה" של המערכת - מונעת קריסה טוטאלית במקרה של שגיאה בניסוי אחד
  tryCatch({
    print(paste("Processing:", study_name, "..."))
    
    # א. חיפוש אוטומטי של כל המשאבים הקשורים לניסוי
    all_ids <- curatedMetagenomicData(paste0(study_name, ".*"), dryrun = TRUE)
    
    # ב. סינון דינמי רק לסוג הנתונים שביקשנו
    target_id <- grep(feature_type, all_ids, value = TRUE)
    
    if(length(target_id) == 0) {
      stop(paste("Could not find", feature_type, "for this study."))
    }
    
    selected_id <- target_id[1]
    print(paste("   Found matching ID:", selected_id))
    
    # ג. ההורדה והחילוץ האמיתיים
    mae <- curatedMetagenomicData(selected_id, dryrun = FALSE)
    tse <- mae[[1]]
    
    metadata <- as.data.frame(colData(tse))
    features <- as.data.frame(assay(tse))
    
    # ד. הגדרת שמות הקבצים והשמירה ל-CSV
    metadata_path <- file.path(out_dir, paste0(study_name, "_metadata.csv"))
    features_path <- file.path(out_dir, paste0(study_name, "_", feature_type, "_features.csv"))
    
    write.csv(metadata, metadata_path, row.names = TRUE)
    write.csv(t(features), features_path, row.names = TRUE)
    
    # ה. דיווח הצלחה ללוג
    write(paste("[SUCCESS]", study_name), log_path, append = TRUE)
    return(TRUE)
    
  }, error = function(e) {
    # ו. טיפול בשגיאה: רושם את הבעיה ללוג וממשיך לניסוי הבא
    print(paste("   [ERROR]", study_name, ":", e$message))
    write(paste("[FAILED] ", study_name, "-", e$message), log_path, append = TRUE)
    return(FALSE)
  })
}

# ------------------------------------------------------------------------------
# 4. יציאה לדרך! (הרצת הלולאה על כל הניסויים)
# ------------------------------------------------------------------------------

print(paste("Starting batch process for", length(all_studies), "studies..."))

# הפקודה הזו מריצה את הפונקציה שלנו על כל רשימת השמות
results <- sapply(all_studies, function(name) {
  download_single_study(
    study_name = name, 
    feature_type = target_feature_type, 
    out_dir = output_dir, 
    log_path = log_file
  )
})

# סיום
print("=====================================================")
print("Batch process complete!")
print("Please check 'download_log.txt' to see if any studies failed.")
print(paste("All successful CSV files are waiting in:", output_dir))