# וודא שהספריות הנדרשות מותקנות אצלך:
# BiocManager::install("curatedMetagenomicData")
library(curatedMetagenomicData)
library(SummarizedExperiment)

download_study_by_name <- function(study_name, feature_type = "pathway_abundance") {
  
  # 1. חיפוש אוטומטי של המשאבים
  all_ids <- curatedMetagenomicData(paste0(study_name, ".*"), dryrun = TRUE)
  
  # 2. בחירה דינמית לפי מה שביקשת (ה-feature_type)
  target_id <- grep(feature_type, all_ids, value = TRUE)
  
  if(length(target_id) == 0) {
    stop(paste("Error: Could not find", feature_type, "for study", study_name))
  }
  
  selected_id <- target_id[1]
  
  # 3. הכנת תיקיית פלט (הפניה לתיקיית data שנמצאת ב-Root)
  # ה-.. אומר ל-R לעלות מתיקיית ה-r_script לתיקיית האב של הפרויקט
  output_dir <- file.path("..", "data")
  
  if (!dir.exists(output_dir)) { 
    dir.create(output_dir) 
  }
  
  print(paste("Downloading:", selected_id))
  
  # 4. הורדה וחילוץ
  mae <- curatedMetagenomicData(selected_id, dryrun = FALSE)
  tse <- mae[[1]]
  
  metadata <- as.data.frame(colData(tse))
  features <- as.data.frame(assay(tse))
  
  # 5. שמירה
  metadata_path <- file.path(output_dir, paste0(study_name, "_metadata.csv"))
  features_path <- file.path(output_dir, paste0(study_name, "_", feature_type, "_features.csv"))
  
  write.csv(metadata, metadata_path, row.names = TRUE)
  write.csv(t(features), features_path, row.names = TRUE)
  
  print(paste("Success! Files saved in", output_dir))
}

# --- דוגמאות להרצה ---
# זכור: כל מה שתוריד כאן יגיע ישירות לתיקיית ה-data שבשורש הפרויקט
 download_study_by_name("FengQ_2015") 
# download_study_by_name("FengQ_2015", feature_type = "pathway_abundance")