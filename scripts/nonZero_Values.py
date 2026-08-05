import pandas as pd
import numpy as np
import os
import glob
import plotly.express as px
import time

def plot_interactive_multiverse():
    # הגדרת נתיבים
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.normpath(os.path.join(script_dir, '..', 'data'))
    
    feature_files = glob.glob(os.path.join(data_dir, "*_features.csv"))
    
    if not feature_files:
        print("❌ Could not find feature files in the data folder!")
        return
        
    print(f"🦸‍♂️ Assembling {len(feature_files)} datasets for interactive plots...\n")
    
    all_percentage_data = [] 
    all_count_data = []
    
    for file_path in feature_files:
        start_time = time.time()
        filename = os.path.basename(file_path)
        study_name = filename.split('_')[0] 
        print(f"⏳ Processing {study_name}...", end="", flush=True)
        
        try:
            df = pd.read_csv(file_path, index_col=0, engine='pyarrow')
        except ValueError:
            df = pd.read_csv(file_path, index_col=0)
        
        valid_cols = ~df.columns.str.lower().str.contains('unmapped|unintegrated')
        df = df.loc[:, valid_cols]
        
        # חישוב מספר דגימות וגם אחוזי המסלולים (Non-Zero)
        nonzero_counts_raw = np.count_nonzero(df.values > 0, axis=0)
        nonzero_percentage = (nonzero_counts_raw / len(df)) * 100
        
        # טבלאות זמניות לכל מחקר
        temp_pct_df = pd.DataFrame({
            'Percentage': nonzero_percentage,
            'Study': study_name
        })
        all_percentage_data.append(temp_pct_df)
        
        temp_count_df = pd.DataFrame({
            'SampleCount': nonzero_counts_raw,
            'Study': study_name
        })
        all_count_data.append(temp_count_df)
        
        print(f" ✅ Done in {time.time() - start_time:.1f}s")

    print("\n🎨 Generating interactive plots...")
    
    plot_pct_df = pd.concat(all_percentage_data, ignore_index=True)
    plot_count_df = pd.concat(all_count_data, ignore_index=True)
    
    # ==========================================
    # גרף 1: אחוזים כללי
    # ==========================================
    fig_pct = px.histogram(plot_pct_df, 
                       x="Percentage", 
                       color="Study", 
                       nbins=100,         
                       opacity=0.4,       
                       barmode="overlay", 
                       title="The Multiverse of Pathways: Non-Zero Values Percentage Distribution")
    
    fig_pct.update_layout(
        xaxis_title="Percentage of Samples with Non-Zero Value (%)",
        yaxis_title="Frequency (Number of Pathways)",
        legend_title="Study Cohort",
        hovermode="x",
        xaxis=dict(range=[0, 100], rangeslider=dict(visible=True)),
        updatemenus=[
            dict(
                type="buttons",
                direction="left",
                buttons=list([
                    dict(args=[{"xaxis.range": [0, 20]}], label="🔍 Zoom 0-20%", method="relayout"),
                    dict(args=[{"xaxis.range": [0, 100]}], label="🔄 Reset View (0-100%)", method="relayout")
                ]),
                pad={"r": 10, "t": 10},
                showactive=True,
                x=0.0, xanchor="left", y=1.18, yanchor="top"
            )
        ]
    )
    output_pct_path = os.path.join(data_dir, "Interactive_Pathways_Percentage_Distribution.html")
    fig_pct.write_html(output_pct_path)
    
    # ==========================================
    # גרף 2: מספר דגימות ממשי (Counts מלא)
    # ==========================================
    fig_count = px.histogram(plot_count_df, 
                               x="SampleCount", 
                               color="Study", 
                               nbins=100,         
                               opacity=0.4,       
                               barmode="overlay", 
                               title="The Multiverse of Pathways: Non-Zero Values Sample Count Distribution")
    
    fig_count.update_layout(
        xaxis_title="Number of Samples with Non-Zero Value",
        yaxis_title="Frequency (Number of Pathways)",
        legend_title="Study Cohort",
        hovermode="x",
        xaxis=dict(rangeslider=dict(visible=True))
    )
    output_count_path = os.path.join(data_dir, "Interactive_Pathways_Counts_Distribution.html")
    fig_count.write_html(output_count_path)

    # ==========================================
    # גרף 3: זום ממוקד לטווח 0-19 ברזולוציה של 1 (קאט-אוף)
    # ==========================================
    # סינון הנתונים אך ורק לטווח המבוקש
    zoom_df = plot_count_df[plot_count_df['SampleCount'] <= 19]
    
    fig_zoom = px.histogram(zoom_df, 
                            x="SampleCount", 
                            color="Study", 
                            opacity=0.5,       
                            barmode="overlay", 
                            title="Cutoff Zone Zoom: Pathways with 0 to 19 Non-Zero Samples")
    
    fig_zoom.update_layout(
        xaxis_title="Exact Number of Non-Zero Samples",
        yaxis_title="Frequency (Number of Pathways)",
        legend_title="Study Cohort",
        hovermode="x",
        bargap=0.1,
        xaxis=dict(
            tickmode='linear',
            tick0=0,
            dtick=1,  # מציג כל מספר שלם בנפרד על הציר
            range=[-0.5, 19.5]
        )
    )
    
    # כפיית רוחב בינים מדויק של 1 לכל עמודה
    fig_zoom.update_traces(xbins=dict(start=-0.5, end=19.5, size=1))
    
    output_zoom_path = os.path.join(data_dir, "Interactive_Pathways_Zoom_0_19.html")
    fig_zoom.write_html(output_zoom_path)
    
    print(f"\n✅ All done! Interactive graphs are saved at:")
    print(f"   1. Percentage Plot: {output_pct_path}")
    print(f"   2. Sample Counts Plot (Full): {output_count_path}")
    print(f"   3. Cutoff Zoom Plot (0-19): {output_zoom_path}")
    print("🌐 Double-click the .html files to open them in your web browser.")

if __name__ == "__main__":
    plot_interactive_multiverse()