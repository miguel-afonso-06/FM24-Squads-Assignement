import pandas as pd

DEBUG = True

def organize_squads(df, tactic):
    df = df.copy()
    df['Decision'] = "Unassigned"
    df['Squad'] = "None"
    df['Assigned Role'] = "None"
    
    ASSET_VALUE_THRESHOLD = 5000000
    DEPTH_THRESHOLD = 1.5

    squad_configs = [
        {'name': 'Senior Team', 'slots': [1, 2]},
        {'name': 'B Team', 'slots': [1, 2]},
        {'name': 'U23 Team', 'slots': [1, 2]},
        {'name': 'U19 Team', 'slots': [1, 2]}
    ]

    # 1️⃣ Tactical Slot Filling (Hybrid weighting fix)
    for squad in squad_configs:
        for slot in squad['slots']:
            for _, role in tactic:
                role = role.strip()
                eligible = df[df['Decision'] == "Unassigned"]

                if role not in df.columns:
                    continue

                # keep only players that actually have a score for this role
                eligible = eligible[eligible[role].notna()]

                if eligible.empty:
                    continue

                if squad['name'] == 'Senior Team':
                    pick = eligible.sort_values(role, ascending=False).index[0]
                else:
                    eligible = eligible.assign(
                        DevScore=(0.4 * eligible[role]) +
                                 (0.6 * eligible['Potential Estimate'])
                    )
                    pick = eligible.sort_values('DevScore', ascending=False).index[0]

                df.at[pick, 'Decision'] = f"{squad['name']} #{slot}"
                df.at[pick, 'Squad'] = squad['name']
                df.at[pick, 'Assigned Role'] = role

    # 2️⃣ Use MEAN instead of MIN (Fixed)
    senior_df = df[df['Squad'] == 'Senior Team']
    senior_mean_cq = senior_df['Current Quality'].mean() if not senior_df.empty else 10.0

    # 3️⃣ Post-assignment Logic
    for idx, row in df[df['Decision'] == "Unassigned"].iterrows():

        growth = row['Potential Estimate'] - row['Current Quality']

        if row['Value_Num'] >= ASSET_VALUE_THRESHOLD:
            df.at[idx, 'Decision'] = "Loan Out (Asset)"
            df.at[idx, 'Squad'] = "External"

        elif row['Current Quality'] >= (senior_mean_cq - DEPTH_THRESHOLD):
            df.at[idx, 'Decision'] = "Emergency Backup"
            df.at[idx, 'Squad'] = "B Team"

        # Refined Elite Prospect rule
        elif (
            row['Potential Estimate'] >= df['Potential Estimate'].quantile(0.85)
            and growth >= 1.5
        ):
            df.at[idx, 'Decision'] = "Loan Out (Prospect)"
            df.at[idx, 'Squad'] = "External"

        else:
            if row['Value_Num'] > 100000:
                df.at[idx, 'Decision'] = "Sell"
            else:
                df.at[idx, 'Decision'] = "Release"

    return df
