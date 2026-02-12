# squad_selection.py
import pandas as pd

DEBUG = True

def organize_squads(df, tactic):
    df = df.copy()
    df['Decision'] = "Unassigned"
    df['Squad'] = "None"
    df['Assigned Role'] = "None"
    if DEBUG: print(f"[DEBUG] tactic:\n{tactic}")
    
    # Financial/Tactical Constants
    ASSET_VALUE_THRESHOLD = 5000000  # €5M
    DEPTH_THRESHOLD = 1.5           # Max CQ distance for "Emergency Backup"

    # 1. Fill Tactical Slots (Senior, B, U23, U19)
    squad_configs = [
        {'name': 'Senior Team', 'slots': [1, 2]},
        {'name': 'B Team', 'slots': [1, 2]},
        {'name': 'U23 Team', 'slots': [1, 2]},
        {'name': 'U19 Team', 'slots': [1, 2]}
    ]

    for squad in squad_configs:
        for slot in squad['slots']:
            for _, role in tactic:
                eligible = df[(df['Decision'] == "Unassigned") & 
                              (df['Tactical Role'] == role)]
                if eligible.empty: continue
                
                # Senior Team priorities Current Quality; Others prioritize Potential
                sort_col = 'Current Quality' if squad['name'] == 'Senior Team' else 'Potential Estimate'
                pick = eligible.sort_values(sort_col, ascending=False).index[0]
                
                df.at[pick, 'Decision'] = f"{squad['name']} #{slot}"
                df.at[pick, 'Squad'] = squad['name']
                df.at[pick, 'Assigned Role'] = role

    # 2. Get Senior Team Minimum Quality for comparison
    senior_min_cq = df[df['Squad'] == 'Senior Team']['Current Quality'].min() if not df[df['Squad'] == 'Senior Team'].empty else 10.0

    # 3. Post-assignment Logic (The "Safety Net")
    for idx, row in df[df['Decision'] == "Unassigned"].iterrows():
        # A. The Financial Safety Net (González/Guerini Case)
        if row['Value_Num'] >= ASSET_VALUE_THRESHOLD:
            df.at[idx, 'Decision'] = "Loan Out (Asset)"
            df.at[idx, 'Squad'] = "External"

        # B. The Emergency Depth / André Luiz Tier
        # If they are within 1.5 CQ of the starters but have low value/growth
        elif row['Current Quality'] >= (senior_min_cq - DEPTH_THRESHOLD):
            df.at[idx, 'Decision'] = "Emergency Backup"
            df.at[idx, 'Squad'] = "B Team" # Keeping them local but ready

        # C. The Elite Prospect Protection (Top 10% of Club Potential)
        elif row['Potential Estimate'] >= df['Potential Estimate'].quantile(0.90):
            df.at[idx, 'Decision'] = "Loan Out (Prospect)"
            df.at[idx, 'Squad'] = "External"

        # D. The Deadwood (Low CQ, Low PQ, Low Value)
        else:
            if row['Value_Num'] > 100000:
                df.at[idx, 'Decision'] = "Sell"
            else:
                df.at[idx, 'Decision'] = "Release"

    return df