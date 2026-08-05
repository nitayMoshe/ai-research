import pandas as pd
import numpy as np
import lightgbm as lgb
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score
import optuna
import os
import glob
import warnings
import matplotlib.pyplot as plt
import seaborn as sns

warnings.filterwarnings('ignore')
optuna.logging.set_verbosity(optuna.logging.ERROR)

# ==========================================
# 1. פונקציות העיבוד המקדים המקוריות שלכם
# ==========================================
def apply_preprocessing(X_tr, X_te, feature_cols):
    # Sparsity 10%
    sparsity_th = max(1, int(0.1 * X_tr.shape[0]))
    non_zero = np.count_nonzero(X_tr > 0, axis=0)
    valid_idx = np.where(non_zero >= sparsity_th)[0]
    X_tr, X_te = X_tr[:, valid_idx], X_te[:, valid_idx]
    current_features = [feature_cols[i] for i in valid_idx]
    
    # Collapse Sum
    pwy_groups = {}
    for idx, col in enumerate(current_features):
        pwy_groups.setdefault(col.split('|', 1)[0], []).append(idx)
    
    unique_pwys = list(pwy_groups.keys())
    proj = np.zeros((len(current_features), len(unique_pwys)), dtype=np.float32)
    for pwy_idx, pwy in enumerate(unique_pwys):
        indices = pwy_groups[pwy]
        proj[indices, pwy_idx] = 1.0
    X_tr, X_te = X_tr @ proj, X_te @ proj
    
    # Oshrit Log Z
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

# ==========================================
# 2. הרצת Optuna מהירה
# ==========================================
def run_optuna_and_evaluate(X_train, y_train, X_test, y_test, feature_cols):
    X_t, X_v, y_t, y_v = train_test_split(X_train, y_train, test_size=0.2, stratify=y_train, random_state=42)
    X_t_proc, X_v_proc = apply_preprocessing(X_t.copy(), X_v.copy(), feature_cols)
    
    def objective(trial):
        params = {
            'n_estimators': trial.suggest_int('n_estimators', 20, 60),
            'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.2, log=True),
            'max_depth': trial.suggest_int('max_depth', 2, 5),
            'num_leaves': trial.suggest_int('num_leaves', 7, 20),
            'verbosity': -1, 'n_jobs': -1
        }
        clf = lgb.LGBMClassifier(**params)
        clf.fit(X_t_proc, y_t)
        return roc_auc_score(y_v, clf.predict_proba(X_v_proc)[:, 1])

    study = optuna.create_study(direction='maximize')
    study.optimize(objective, n_trials=10) # 10 ניסיונות כמו בסקריפט המקורי
    
    best_params = study.best_params
    best_params.update({'verbosity': -1, 'n_jobs': -1})
    
    # הערכה סופית על קבוצת הבדיקה
    X_train_proc, X_test_proc = apply_preprocessing(X_train.copy(), X_test.copy(), feature_cols)
    final_clf = lgb.LGBMClassifier(**best_params)
    final_clf.fit(X_train_proc, y_train)
    
    return roc_auc_score(y_test, final_clf.predict_proba(X_test_proc)[:, 1])

# ==========================================
# 3. ניהול מבחן הערבוב (Permutation)
# ==========================================
def run_polyjuice_test():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_folder = os.path.normpath(os.path.join(script_dir, '..', 'data'))
    
    # 3 מחקרים אסטרטגיים לבדיקה מהירה אך מייצגת
    target_studies = ['IjazUZ_2017', 'HallAB_2017', 'HMP_2019_ibdmdb']
    results = []

    print("\n🔮 Starting The Polyjuice Permutation Test...")
    print("-" * 50)

    for study_name in target_studies:
        print(f"\n🧪 Loading {study_name}...")
        feat_file = os.path.join(data_folder, f"{study_name}_pathway_abundance_features.csv")
        meta_file = os.path.join(data_folder, f"{study_name}_metadata.csv")
        
        if not os.path.exists(feat_file):
            feat_file = os.path.join(data_folder, f"{study_name}_features.csv")
            
        try:
            df_feat = pd.read_csv(feat_file, index_col=0)
            df_meta = pd.read_csv(meta_file, index_col=0)
        except FileNotFoundError:
            print(f"⚠️ Could not find files for {study_name}, skipping.")
            continue

        # איתור תווית המחלה (לפי הלוגיקה שלכם)
        label_col = next((col for col in ["study_condition", "disease", "status", "disease_state", "Group", "group"] if col in df_meta.columns), None)
        df_meta[label_col] = df_meta[label_col].astype(str).str.lower().str.strip()
        common_samples = df_feat.index.intersection(df_meta.index)
        
        X = df_feat.loc[common_samples].fillna(0.0).values
        feature_cols = list(df_feat.columns)
        
        control_kws = ["control", "healthy", "healthy_control", "con", "normal", "donor"]
        y = df_meta.loc[common_samples, label_col].apply(lambda val: 0 if any(k in val for k in control_kws) else 1).values
        
        print(f"✅ Samples: {len(y)} | Healthy: {sum(y==0)} | Sick: {sum(y==1)}")
        
        # פיצול אמיתי
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)
        
        # --- שלב א': הערכה על נתונים אמיתיים ---
        print("   ⚔️ Running Optuna on REAL data...")
        real_auc = run_optuna_and_evaluate(X_train, y_train, X_test, y_test, feature_cols)
        print(f"   🎯 REAL Test AUC: {real_auc:.4f}")
        
        # --- שלב ב': הערכה על נתונים מעורבבים (Permutation) ---
        print("   🧪 Running Optuna on SHUFFLED data (x3 times)...")
        shuffled_aucs = []
        for i in range(3):
            # ערבוב של התוויות בלבד - ניתוק הקשר הביולוגי
            y_train_shuffled = np.random.permutation(y_train)
            y_test_shuffled = np.random.permutation(y_test)
            
            fake_auc = run_optuna_and_evaluate(X_train, y_train_shuffled, X_test, y_test_shuffled, feature_cols)
            shuffled_aucs.append(fake_auc)
            print(f"      - Fake Run {i+1}: AUC = {fake_auc:.4f}")
            
        mean_fake_auc = np.mean(shuffled_aucs)
        
        results.append({
            'Study': study_name,
            'Real_AUC': real_auc,
            'Shuffled_AUC': mean_fake_auc
        })

    # ==========================================
    # 4. ויזואליזציה של ההוכחה
    # ==========================================
    df_res = pd.DataFrame(results)
    df_res_melt = df_res.melt(id_vars='Study', var_name='Data_Type', value_name='AUC')
    df_res_melt['Data_Type'] = df_res_melt['Data_Type'].replace({'Real_AUC': 'Real Biological Data', 'Shuffled_AUC': 'Shuffled Fake Data'})

    plt.figure(figsize=(10, 6))
    sns.set_theme(style="whitegrid")
    
    ax = sns.barplot(data=df_res_melt, x='Study', y='AUC', hue='Data_Type', palette=['#27ae60', '#e74c3c'])
    plt.axhline(0.5, color='black', linestyle='--', alpha=0.7, label='Random Guess (0.5)')
    
    plt.title('Permutation Test: Real Signal vs. Random Noise', fontsize=16, fontweight='bold', pad=15)
    plt.ylabel('Test Set AUC', fontsize=12)
    plt.xlabel('Study ID', fontsize=12)
    plt.ylim(0.3, 1.05)
    plt.legend(title='Validation Type')

    for p in ax.patches:
        height = p.get_height()
        if pd.notnull(height) and height > 0:
            ax.annotate(f'{height:.2f}', (p.get_x() + p.get_width() / 2., height), 
                        ha='center', va='bottom', fontsize=10, color='black', xytext=(0, 5), textcoords='offset points')

    output_path = os.path.join(script_dir, '..', 'preProcessingResults', 'Polyjuice_Permutation_Test.png')
    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    print(f"\n📊 Proof Graph generated at: {output_path}")

if __name__ == "__main__":
    run_polyjuice_test()