# סקריפט גרסה 12 - Super Turbo
# מריץ Optuna לכל שיטת Preprocessing בנפרד, שומר 2 תוצאות לכל שיטה (Base ו-Optuna),
# וכולל מנגנון אל-כשל (Safe Save) למקרה שקובץ ה-CSV פתוח באקסל.

import pandas as pd
import numpy as np
import lightgbm as lgb
from sklearn.model_selection import train_test_split, StratifiedKFold
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.metrics import roc_auc_score
import optuna
import os
import glob
import json
import warnings
import matplotlib.pyplot as plt
import seaborn as sns
import time

# התעלמות מאזהרות מיותרות של ספריות והשתקת לוגים פנימיים של Optuna
warnings.filterwarnings('ignore')
optuna.logging.set_verbosity(optuna.logging.ERROR)

# ==============================================================================
# 0. BLACKLIST - מחקרים בעייתיים מרובי-מחלות להסרה מוחלטת
# ==============================================================================
BLACKLIST_STUDIES = [
        'FengQ_2015', 'GhensiP_2019', 'HanniganGD_2017', 'HMP_2019_t2d', 
    'IaniroG_2022', 'KarlssonFH_2013', 'LiJ_2014', 'LiJ_2017', 
    'LiSS_2016', 'LoombaR_2017', 'MetaCardis_2020_a', 'ThomasAM_2018a', 
    'VatanenT_2016', 'XieH_2016', 'YachidaS_2019', 'ZellerG_2014', 'BedarfJR_2017', 
    'Castro-NallarE_2015', 'DavidLA_2015', 'GuptaA_2019', 'Heitz-BuschartA_2016', 'SankaranarayananK_2015',
    'ThomasAM_2018b'
]

# ==============================================================================
# 1. REAL DATA LOADER (V5 CACHE)
# ==============================================================================
def load_real_microbiome_data(data_folder):
    print("\n📂 [Data Loader] Initiating real data loading from:", data_folder)
    
    cache_dir = os.path.join(data_folder, ".cache")
    cache_x_path = os.path.join(cache_dir, "X_global_v5.pkl")
    cache_y_path = os.path.join(cache_dir, "y_global_v5.pkl")
    cache_meta_path = os.path.join(cache_dir, "cache_metadata_v5.json")
    
    feature_files = glob.glob(os.path.join(data_folder, "*_features.csv"))
    metadata_files = glob.glob(os.path.join(data_folder, "*_metadata.csv"))
    
    if not feature_files:
        raise FileNotFoundError(f"No feature files found in {data_folder}!")
        
    current_state = {
        "cache_version": 5, 
        "blacklist": sorted(BLACKLIST_STUDIES) 
    }
    
    for f in feature_files + metadata_files:
        stat = os.stat(f)
        current_state[os.path.basename(f)] = {"mtime": stat.st_mtime, "size": stat.st_size}
        
    if os.path.exists(cache_x_path) and os.path.exists(cache_y_path) and os.path.exists(cache_meta_path):
        try:
            with open(cache_meta_path, "r") as f:
                cached_state = json.load(f)
            if cached_state == current_state:
                print("⚡ [Cache Hit V5] Loading processed data (Blacklist verified)...")
                return pd.read_pickle(cache_x_path), pd.read_pickle(cache_y_path)
        except Exception:
            pass
            
    print("🔄 [Cache Miss V5] Rebuilding dataset (Blacklist updated or cache missing)...")
    
    all_features_dfs = []
    all_labels = []
    
    for file_path in feature_files:
        study_name = os.path.basename(file_path).replace("_pathway_abundance_features.csv", "").replace("_features.csv", "")
        
        if study_name in BLACKLIST_STUDIES:
            print(f"🚫 [Blacklist] Skipping study: {study_name}")
            continue
            
        try:
            df_feat = pd.read_csv(file_path, index_col=0)
            df_meta = pd.read_csv(os.path.join(data_folder, f"{study_name}_metadata.csv"), index_col=0)
            
            label_col = next((col for col in ["study_condition", "disease", "status", "disease_state", "Group", "group"] if col in df_meta.columns), None)
            if not label_col:
                label_col = next((col for col in df_meta.columns if any(k in col.lower() for k in ["condition", "disease", "status", "class", "group"])), None)
            
            if not label_col:
                continue
                
            df_meta[label_col] = df_meta[label_col].astype(str).str.lower().str.strip()
            control_kws = ["control", "healthy", "healthy_control", "con", "normal", "donor"]
            
            common_samples = df_feat.index.intersection(df_meta.index)
            if len(common_samples) == 0:
                continue
                
            df_feat_filtered = df_feat.loc[common_samples].copy()
            df_meta_filtered = df_meta.loc[common_samples]
            
            y_study = df_meta_filtered[label_col].apply(lambda val: 0 if any(k in val for k in control_kws) else 1)
            
            if len(y_study.unique()) < 2:
                print(f"⚠️  [Skip] {study_name} lacks multiple classes.")
                continue
                
            df_feat_filtered["Study"] = study_name
            all_features_dfs.append(df_feat_filtered)
            all_labels.append(y_study)
            print(f"✅ [Loaded] {study_name}: {len(common_samples)} samples synced.")
            
        except Exception as e:
            print(f"❌ [Error] {study_name}: {str(e)}")
            
    print("🔄 [Merging] Concatenating and cleaning data...")
    X_global = pd.concat(all_features_dfs, axis=0, sort=False).fillna(0.0)
    study_series = X_global["Study"]
    X_global = X_global.drop(columns=["Study"]).astype(np.float32)
    
    valid_mask = ~X_global.columns.str.lower().str.contains('|'.join(["unmapped", "unintegrated"]))
    X_global = X_global.loc[:, valid_mask]
    
    non_zero_counts = np.count_nonzero(X_global.values, axis=0)
    X_global = X_global[X_global.columns[non_zero_counts >= 5]]
    
    X_global["Study"] = study_series
    y_global = pd.concat(all_labels, axis=0)
    
    os.makedirs(cache_dir, exist_ok=True)
    X_global.to_pickle(cache_x_path)
    y_global.to_pickle(cache_y_path)
    with open(cache_meta_path, "w") as f:
        json.dump(current_state, f)
        
    print(f"🏆 [Success] Global V5 Dataset Built: {X_global.shape[0]} samples, {X_global.shape[1]-1} features.")
    return X_global, y_global

# ==============================================================================
# 2. PREPROCESSING PIPELINE FUNCTIONS
# ==============================================================================
def apply_preprocessing(X_train, X_test, config, feature_cols):
    X_tr, X_te = X_train.copy(), X_test.copy()
    current_features = feature_cols.copy()
    
    if config.get("rank", False):
        X_tr = pd.DataFrame(X_tr).rank(axis=1, method='min').values.astype(np.float32)
        X_te = pd.DataFrame(X_te).rank(axis=1, method='min').values.astype(np.float32)
    
    if config.get("sparsity", 0) > 0:
        non_zero = np.count_nonzero(X_tr > 0, axis=0)
        valid_idx = np.where(non_zero >= config["sparsity"])[0]
        X_tr, X_te = X_tr[:, valid_idx], X_te[:, valid_idx]
        current_features = [current_features[i] for i in valid_idx]
        
    if config.get("collapse", None):
        method = config["collapse"]
        pwy_groups = {}
        for idx, col in enumerate(current_features):
            pwy_groups.setdefault(col.split('|', 1)[0], []).append(idx)
        
        unique_pwys = list(pwy_groups.keys())
        
        if method in ["sum", "mean"]:
            proj = np.zeros((len(current_features), len(unique_pwys)), dtype=np.float32)
            for pwy_idx, pwy in enumerate(unique_pwys):
                indices = pwy_groups[pwy]
                proj[indices, pwy_idx] = 1.0 if method == "sum" else 1.0/len(indices)
            X_tr, X_te = X_tr @ proj, X_te @ proj
        elif method == "pca":
            X_tr_col = np.zeros((X_tr.shape[0], len(unique_pwys)), dtype=np.float32)
            X_te_col = np.zeros((X_te.shape[0], len(unique_pwys)), dtype=np.float32)
            pca = PCA(n_components=1, random_state=42)
            for pwy_idx, pwy in enumerate(unique_pwys):
                indices = pwy_groups[pwy]
                if len(indices) == 1:
                    X_tr_col[:, pwy_idx] = X_tr[:, indices[0]]
                    X_te_col[:, pwy_idx] = X_te[:, indices[0]]
                else:
                    X_tr_col[:, pwy_idx] = pca.fit_transform(X_tr[:, indices]).ravel()
                    X_te_col[:, pwy_idx] = pca.transform(X_te[:, indices]).ravel()
            X_tr, X_te = X_tr_col, X_te_col
        current_features = unique_pwys

    if config.get("oshrit_log", False):
        np.multiply(X_tr, 1e7, out=X_tr)
        np.add(X_tr, 0.1, out=X_tr)
        np.log10(X_tr, out=X_tr)
        
        np.multiply(X_te, 1e7, out=X_te)
        np.add(X_te, 0.1, out=X_te)
        np.log10(X_te, out=X_te)
        
        scaler = StandardScaler(copy=False)
        X_tr = scaler.fit_transform(X_tr)
        X_te = scaler.transform(X_te)

    return X_tr, X_te

# ==============================================================================
# 3. EVALUATION & TURBO OPTUNA
# ==============================================================================
def evaluate_method(X_train_full, y_train_full, X_test_final, y_test_final, feature_cols, config, lgb_params):
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    train_aucs, val_aucs = [], []
    
    if isinstance(y_train_full, pd.Series):
        y_train_full = y_train_full.reset_index(drop=True)
    
    for train_idx, val_idx in skf.split(X_train_full, y_train_full):
        X_tr, X_val = X_train_full[train_idx], X_train_full[val_idx]
        y_tr, y_val = y_train_full.iloc[train_idx], y_train_full.iloc[val_idx]
        
        if len(np.unique(y_tr)) < 2 or len(np.unique(y_val)) < 2:
            continue
            
        X_tr_proc, X_val_proc = apply_preprocessing(X_tr, X_val, config, feature_cols)
        
        clf = lgb.LGBMClassifier(**lgb_params)
        clf.fit(X_tr_proc, y_tr)
        
        train_aucs.append(roc_auc_score(y_tr, clf.predict_proba(X_tr_proc)[:, 1]))
        val_aucs.append(roc_auc_score(y_val, clf.predict_proba(X_val_proc)[:, 1]))
        
    mean_train_auc = np.mean(train_aucs) if train_aucs else 0.5
    mean_val_auc = np.mean(val_aucs) if val_aucs else 0.5
        
    X_train_proc, X_test_proc = apply_preprocessing(X_train_full, X_test_final, config, feature_cols)
    clf = lgb.LGBMClassifier(**lgb_params)
    clf.fit(X_train_proc, y_train_full)
    
    if len(np.unique(y_test_final)) > 1:
        test_auc = roc_auc_score(y_test_final, clf.predict_proba(X_test_proc)[:, 1])
    else:
        test_auc = 0.5
    
    return mean_train_auc, mean_val_auc, test_auc

def run_optuna_tuning(X_train_full, y_train_full, feature_cols, config):
    """
    ⚡ TURBO BOOST OPTUNA: 
    מבצע את העיבוד המקדים פעם אחת מחוץ לאופטונה. חוסך המון שעות!
    """
    if isinstance(y_train_full, pd.Series):
        y_train_full = y_train_full.reset_index(drop=True)
        
    try:
        X_t, X_v, y_t, y_v = train_test_split(X_train_full, y_train_full, test_size=0.2, stratify=y_train_full, random_state=42)
    except ValueError:
        X_t, X_v, y_t, y_v = train_test_split(X_train_full, y_train_full, test_size=0.2, random_state=42)

    X_t_proc, X_v_proc = apply_preprocessing(X_t, X_v, config, feature_cols)

    def objective(trial):
        params = {
            'n_estimators': trial.suggest_int('n_estimators', 20, 60),
            'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.2, log=True),
            'max_depth': trial.suggest_int('max_depth', 2, 5),
            'num_leaves': trial.suggest_int('num_leaves', 7, 20),
            'verbosity': -1,
            'n_jobs': -1
        }
        
        clf = lgb.LGBMClassifier(**params)
        clf.fit(X_t_proc, y_t)
        
        if len(np.unique(y_v)) > 1:
            val_auc = roc_auc_score(y_v, clf.predict_proba(X_v_proc)[:, 1])
        else:
            val_auc = 0.5
            
        return val_auc

    def progress_callback(study, trial):
        print(".", end="", flush=True)

    study = optuna.create_study(direction='maximize')
    study.optimize(objective, n_trials=10, callbacks=[progress_callback])
    
    try:
        best = study.best_params
        best['n_jobs'] = -1
        best['verbosity'] = -1
        return best
    except ValueError:
        return {'n_estimators': 30, 'learning_rate': 0.05, 'max_depth': 3, 'num_leaves': 10, 'verbosity': -1, 'n_jobs': -1}

# ==============================================================================
# 4. SAFE FILE SAVING (EXCEL LOCK PROTECTION)
# ==============================================================================
def safe_save_csv(df, base_path):
    """
    מנסה לשמור את ה-CSV. אם הקובץ פתוח באקסל (PermissionError), 
    הוא יוסיף חותמת זמן ייחודית כדי למנוע קריסה של עבודת שעות.
    """
    try:
        df.to_csv(base_path, index=False)
        return base_path
    except PermissionError:
        print(f"\n⚠️  אזהרה: הקובץ {os.path.basename(base_path)} פתוח בתוכנה אחרת (כנראה אקסל)!")
        timestamp = int(time.time())
        fallback_path = base_path.replace(".csv", f"_saved_at_{timestamp}.csv")
        df.to_csv(fallback_path, index=False)
        print(f"✅ שמרתי עותק גיבוי למניעת קריסה בנתיב: {fallback_path}")
        return fallback_path

# ==============================================================================
# 5. MAIN EXECUTOR & REPORT GENERATOR
# ==============================================================================
if __name__ == "__main__":
    print("\n" + "="*80)
    print("🔬 MICROBIOME INTRA-STUDY EVALUATOR (SUPER TURBO + ALL OPTUNA + SAFE SAVE)")
    print("="*80)
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.normpath(os.path.join(script_dir, '..', 'data'))
    output_dir = os.path.normpath(os.path.join(script_dir, '..', 'preProcessingResults'))
    os.makedirs(output_dir, exist_ok=True)
    
    X, y = load_real_microbiome_data(data_path)
    studies = X["Study"].unique()
    
    base_lgb_params = {'n_estimators': 50, 'learning_rate': 0.05, 'max_depth': 3, 'num_leaves': 7, 'verbosity': -1, 'n_jobs': -1}
    all_results = []
    
    configs = {
        "Raw": {},
        "Sparsity_10%": {'sparsity': 0.1},
        "Ranked": {'rank': True},
        "Collapse_Sum": {'collapse': 'sum'},
        "Collapse_PCA": {'collapse': 'pca'},
        "Oshrit_Log_Z": {'oshrit_log': True},
        "Rank_then_Collapse_Sum": {'rank': True, 'collapse': 'sum'},
        "Collapse_Sum_then_Log_Z": {'collapse': 'sum', 'oshrit_log': True},
        "All_Combined": {'sparsity': 0.1, 'collapse': 'sum', 'oshrit_log': True}
    }
    
    for idx, study in enumerate(studies, 1):
        study_mask = X["Study"] == study
        X_study = X[study_mask].drop(columns=["Study"])
        y_study = y[study_mask]
        
        print(f"\n[{idx}/{len(studies)}] Analyzing Study: {study} (N_Samples={len(y_study)})...")
        
        if len(y_study.unique()) < 2 or len(y_study) < 30:
            print(f"  ↳ Skipped (Insufficient cases/controls or too small)")
            continue
            
        non_zero_mask = np.any(X_study.values > 0, axis=0)
        X_study = X_study.iloc[:, non_zero_mask]
        feature_cols = list(X_study.columns)
        
        X_train, X_test, y_train, y_test = train_test_split(X_study.values, y_study, test_size=0.2, stratify=y_study, random_state=42)
        
        sparsity_th = max(1, int(0.1 * X_train.shape[0]))
        for conf_name in configs:
            if 'sparsity' in configs[conf_name]:
                configs[conf_name]['sparsity'] = sparsity_th
        
        study_res = {
            "Study_ID": study,
            "N_Samples": len(y_study),
            "N_Healthy": sum(y_study == 0),
            "N_Disease": sum(y_study == 1)
        }
        
        # הרצת כל הקונפיגורציות - גם עם מודל בסיס וגם עם אופטונה!
        for method_name, conf in configs.items():
            print(f"  ↳ {method_name}: Base...", end=" ")
            tr_auc, v_auc, te_auc = evaluate_method(X_train, y_train, X_test, y_test, feature_cols, conf, base_lgb_params)
            study_res[f"{method_name}_Base_Train"] = round(tr_auc, 4)
            study_res[f"{method_name}_Base_Val"] = round(v_auc, 4)
            study_res[f"{method_name}_Base_Test"] = round(te_auc, 4)
            
            print("Optuna", end="")
            best_params = run_optuna_tuning(X_train, y_train, feature_cols, conf)
            
            tr_auc_op, v_auc_op, te_auc_op = evaluate_method(X_train, y_train, X_test, y_test, feature_cols, conf, best_params)
            study_res[f"{method_name}_Opt_Train"] = round(tr_auc_op, 4)
            study_res[f"{method_name}_Opt_Val"] = round(v_auc_op, 4)
            study_res[f"{method_name}_Opt_Test"] = round(te_auc_op, 4)
            print(" ✅")
        
        all_results.append(study_res)

    if all_results:
        df_results = pd.DataFrame(all_results)
        
        # שימוש בשמירה בטוחה!
        base_csv_path = os.path.join(output_dir, "Intra_Study_Results.csv")
        saved_csv_path = safe_save_csv(df_results, base_csv_path)
        print(f"\n💾 Full detailed table exported to: {saved_csv_path}")
        
        # יצירת הגרף רק עבור עמודות ה-Test
        test_cols = [c for c in df_results.columns if c.endswith("_Test")]
        df_melt = df_results.melt(id_vars=["Study_ID"], value_vars=test_cols, var_name="Method", value_name="Test_AUC")
        df_melt["Method"] = df_melt["Method"].str.replace("_Test", "")
        
        # מיון השיטות מהגרועה לטובה
        median_scores = df_melt.groupby("Method")["Test_AUC"].median().sort_values()
        sorted_methods = median_scores.index.tolist()

        plt.figure(figsize=(20, 10)) # הגדלתי את הגרף כי עכשיו יש כפול שיטות
        sns.boxplot(data=df_melt, x="Method", y="Test_AUC", order=sorted_methods, color="whitesmoke", fliersize=0)
        sns.swarmplot(data=df_melt, x="Method", y="Test_AUC", order=sorted_methods, palette="Set1", size=5, alpha=0.7)
        
        plt.title("Intra-Study Test AUC: Baseline vs. Optuna (Disease Agnostic)", fontsize=18, fontweight='bold')
        plt.xticks(rotation=45, ha='right', fontsize=10) # סיבוב כדי שהתוויות לא יעלו אחת על השנייה
        plt.ylabel("Hold-out Test AUC", fontsize=14)
        plt.axhline(0.5, color='red', linestyle='--', linewidth=1.5, label='Random Guess (0.5)')
        plt.legend(loc="lower right")
        plt.ylim(0.3, 1.05)
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        plt.tight_layout()
        
        base_plot_path = os.path.join(output_dir, "Intra_Study_AUC_Comparison.png")
        # גם התמונה נשמרת בצורה שלא תדרוס ולא תקרוס
        try:
            plt.savefig(base_plot_path, dpi=300, bbox_inches='tight')
            print(f"✅ Visualization saved to: {base_plot_path}")
        except PermissionError:
            t = int(time.time())
            safe_plot = base_plot_path.replace(".png", f"_saved_{t}.png")
            plt.savefig(safe_plot, dpi=300, bbox_inches='tight')
            print(f"✅ Visualization safely saved to: {safe_plot}")
        plt.close()

        # Leaderboard משודרג
        df_test_only = df_results[test_cols]
        winners = df_test_only.idxmax(axis=1).value_counts().reset_index()
        winners.columns = ["Winning_Method", "Num_Wins"]
        winners["Winning_Method"] = winners["Winning_Method"].str.replace("_Test", "")
        winners["Win_Percentage"] = (winners["Num_Wins"] / len(df_results) * 100).round(1).astype(str) + "%"
        
        print("\n" + "="*60)
        print("🏆 LEADERBOARD: Which method achieved the highest Test AUC?")
        print("="*60)
        print(winners.to_string(index=False))
        print("="*60 + "\n")
        
        base_leaderboard_path = os.path.join(output_dir, "Intra_Study_Leaderboard.csv")
        safe_save_csv(winners, base_leaderboard_path)