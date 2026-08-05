import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import os
import glob

def build_and_analyze_bipartite_graph(df, study_name, output_dir):
    """
    בונה גרף דו-צדדי, מחשבת דרגות רגילות וממושקלות, שומרת קבצים 
    בתיקייה ייעודית לכל מחקר, ומציירת היסטוגרמות.
    """
    print(f"--- 🧙‍♂️ Analyzing: {study_name} ---")
    
    # יצירת תיקייה אישית לניסוי הנוכחי בתוך תיקיית התוצאות
    study_output_dir = os.path.join(output_dir, study_name)
    if not os.path.exists(study_output_dir):
        os.makedirs(study_output_dir)
    
    B = nx.Graph()
    pathways = set()
    bacteria = set()
    
    # 1. בניית הגרף והקשתות
    for col in df.columns:
        if '|' in col:
            try:
                pathway, bug = col.split('|', 1)
            except ValueError:
                continue 
                
            B.add_node(pathway, bipartite=0)
            B.add_node(bug, bipartite=1)
            pathways.add(pathway)
            bacteria.add(bug)
            
            weight = df[col].mean()
            if weight > 0:
                B.add_edge(pathway, bug, weight=weight)
                
    if len(B.nodes()) == 0:
        return {"Study": study_name, "Total_Pathways": 0, "Total_Bacteria": 0}

    # 2. חישוב דרגות
    degrees = dict(B.degree())
    weighted_degrees = dict(B.degree(weight='weight'))
    
    pathway_degrees = {n: d for n, d in degrees.items() if B.nodes[n]['bipartite'] == 0}
    bacteria_degrees = {n: d for n, d in degrees.items() if B.nodes[n]['bipartite'] == 1}
    
    pathway_w_degrees = {n: d for n, d in weighted_degrees.items() if B.nodes[n]['bipartite'] == 0}
    bacteria_w_degrees = {n: d for n, d in weighted_degrees.items() if B.nodes[n]['bipartite'] == 1}

    # 3. יצירת טבלה מפורטת לכל צומת ושמירתה בתיקיית הניסוי
    node_data = []
    for node in B.nodes():
        node_type = "Pathway" if B.nodes[node]['bipartite'] == 0 else "Bacteria"
        node_data.append({
            "Node_Name": node,
            "Type": node_type,
            "Degree": degrees[node],
            "Weighted_Degree": weighted_degrees[node]
        })
    
    pd.DataFrame(node_data).to_csv(os.path.join(study_output_dir, f"{study_name}_detailed_degrees.csv"), index=False)

    # 4. מציאת ה"אלופים"
    most_conn_pathway = max(pathway_degrees, key=pathway_degrees.get) if pathway_degrees else "None"
    most_conn_bacteria = max(bacteria_degrees, key=bacteria_degrees.get) if bacteria_degrees else "None"
    most_w_conn_pathway = max(pathway_w_degrees, key=pathway_w_degrees.get) if pathway_w_degrees else "None"
    most_w_conn_bacteria = max(bacteria_w_degrees, key=bacteria_w_degrees.get) if bacteria_w_degrees else "None"

    # 5. ציור והיסטוגרמות (נשמרות בתוך תיקיית הניסוי)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    
    if pathway_degrees:
        ax1.hist(list(pathway_degrees.values()), bins=20, color='lightcoral', edgecolor='black')
        ax1.set_title('Pathways Degree Histogram')
        
    if bacteria_degrees:
        ax2.hist(list(bacteria_degrees.values()), bins=20, color='skyblue', edgecolor='black')
        ax2.set_title('Bacteria Degree Histogram')
        
    plt.suptitle(f'Network Structure - {study_name}')
    plt.savefig(os.path.join(study_output_dir, f"{study_name}_histograms.png"))
    plt.close()
    
    return {
        "Study": study_name,
        "Total_Pathways": len(pathways),
        "Total_Bacteria": len(bacteria),
        "Avg_Degree": round(sum(degrees.values()) / len(B), 2),
        "Avg_Weighted_Degree": round(sum(weighted_degrees.values()) / len(B), 2),
        "Most_Connected_Pathway": most_conn_pathway,
        "Most_Connected_Bacteria": most_conn_bacteria
    }

def run_marvel_phase_1(data_folder, output_folder):
    print("\n🎬 Initiating Phase 1: Solo Studies Analysis...")
    all_summaries = []
    feature_files = glob.glob(os.path.join(data_folder, "*_features.csv"))
    
    for file_path in feature_files:
        study_name = os.path.basename(file_path).replace("_pathway_abundance_features.csv", "").replace("_features.csv", "")
        df = pd.read_csv(file_path, index_col=0)
        all_summaries.append(build_and_analyze_bipartite_graph(df, study_name, output_folder))
        
    pd.DataFrame(all_summaries).to_csv(os.path.join(output_folder, "Solo_Studies_Summary.csv"), index=False)

def run_marvel_phase_2_endgame(data_folder, output_folder):
    print("\n🌍 Initiating Phase 2: Global Network...")
    feature_files = glob.glob(os.path.join(data_folder, "*_features.csv"))
    all_dfs = [pd.read_csv(f, index_col=0) for f in feature_files]
    
    if all_dfs:
        global_df = pd.concat(all_dfs, axis=0).fillna(0)
        global_stats = build_and_analyze_bipartite_graph(global_df, "GLOBAL_NETWORK", output_folder)
        pd.DataFrame([global_stats]).to_csv(os.path.join(output_folder, "Global_Network_Summary.csv"), index=False)

if __name__ == "__main__":
    # מצב ניסוי - החלף ל-../data כדי להריץ על הכל
    INPUT_DATA_DIR = "../data" 
    OUTPUT_RESULTS_DIR = "../results"
    
    run_marvel_phase_1(INPUT_DATA_DIR, OUTPUT_RESULTS_DIR)
    run_marvel_phase_2_endgame(INPUT_DATA_DIR, OUTPUT_RESULTS_DIR)