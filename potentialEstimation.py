import pandas as pd

DEBUG = True

PERSONALITY_MAP = {
    'Model Citizen': 1.15, 'Professional': 1.15, 'Model Professional': 1.15, 'Perfectionist': 1.15,
    'Resolute': 1.10, 'Iron-Willed': 1.10, 'Driven': 1.10,
    'Very Ambitious': 1.05, 'Ambitious': 1.05, 'Determined': 1.05, 'Fairly Professional': 1.05,
    'Fairly Sporting': 1.02, 'Balanced': 1.00, 'Fairly Determined': 1.00, 'Fairly Ambitious': 1.00,
    'Resilient': 1.02,
    'Fickle': 0.95, 'Temperamental': 0.92, 'Light-Hearted': 0.95, 'Realist': 1.00,
    'Casual': 0.90, 'Slack': 0.90, 'Low Determination': 0.90, 'Unambitious': 0.90
}

def dna_factor(row):
    det = pd.to_numeric(row.get('Det', 10), errors='coerce')
    wor = pd.to_numeric(row.get('Wor', 10), errors='coerce')
    team = pd.to_numeric(row.get('Tea', 10), errors='coerce')

    det = 10 if pd.isna(det) else det
    wor = 10 if pd.isna(wor) else wor
    team = 10 if pd.isna(team) else team

    avg = (det + wor + team) / 3
    return 1.0 + ((avg - 10) / 40)

def age_multiplier(age):
    if age <= 18: return 1.4
    if age <= 21: return 1.2
    if age <= 24: return 1.1
    return 1.0

def calculate_tactical_potential(df, role_scores_df, tactic):
    results = []
    tactical_roles = [role for pos, role in tactic]
    
    for idx, row in df.iterrows():
        scores_row = role_scores_df[role_scores_df.index == idx]
        if scores_row.empty:
            continue

        eligible = scores_row[tactical_roles].iloc[0]
        role_score = eligible.max()
        age = pd.to_numeric(row.get('Age', 25), errors='coerce')
        age = 25 if pd.isna(age) else age
        
        personality = str(row.get('Personality', 'Balanced')).strip()
        p_factor = PERSONALITY_MAP.get(personality, 1.0)
        
        raw_pe = role_score * age_multiplier(age) * dna_factor(row) * p_factor
        pe = max(role_score, raw_pe)

        results.append({
            'UID': idx,
            'Name': row['Name'],
            'Current Quality': round(role_score, 2),
            'Potential Estimate': round(pe, 2),
            'Tactical Role': eligible.idxmax(),
            'Personality_Factor': p_factor
        })

        final_df = pd.DataFrame(results).set_index('UID', drop=False)

        # merge role score columns back in
        role_scores_only = role_scores_df.copy()
        role_scores_only.index = role_scores_only.index.astype(str)

        # final_df = final_df.join(role_scores_only, how='left')
        if DEBUG: print(f"[DEBUG] final_df row 0:\n{final_df.head(1)}\n[DEBUG] role_scores_only row 0:\n{role_scores_only.head(1)}")
        final_df = pd.concat([final_df, role_scores_only], axis=1)

        return final_df