import pandas as pd
from utils import debug_nan

DEBUG = False

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
    
    for idx, row in df.iterrows():
        scores_row = role_scores_df[role_scores_df.index == idx]
        if scores_row.empty:
            scores_row = pd.DataFrame(columns=role_scores_df.columns, index=[idx])

        player_positions = row.get('Position_List', [])
        eligible_roles = []

        for pos_side, role_name in tactic:
            for player_pos_side in player_positions:
                # Flatten single-element lists and allow DM/no-side matching
                if isinstance(player_pos_side, list):
                    player_pos_side_flat = [p for p in player_pos_side if p]
                else:
                    player_pos_side_flat = [player_pos_side]

                # Match if any position in tactic matches player
                if all(p in player_pos_side_flat for p in pos_side):
                    eligible_roles.append(role_name)

        if eligible_roles:
            eligible = scores_row[eligible_roles].iloc[0]
            role_score = eligible.max()
        else:
            role_score = None

        age = pd.to_numeric(row.get('Age', 25), errors='coerce')
        age = 25 if pd.isna(age) else age

        personality = str(row.get('Personality', 'Balanced')).strip()
        p_factor = PERSONALITY_MAP.get(personality, 1.0)

        raw_pe = role_score * age_multiplier(age) * dna_factor(row) * p_factor if role_score is not None else None
        pe = max(role_score, raw_pe) if role_score is not None else None

        results.append({
            'UID': idx,
            'Name': row['Name'],
            'Current Quality': round(role_score, 2) if role_score is not None else None,
            'Potential Estimate': round(pe, 2) if pe is not None else None,
            'Tactical Role': eligible_roles[0] if eligible_roles else None,
            'Personality_Factor': p_factor
        })

    final_df = pd.DataFrame(results).set_index('UID', drop=False)

    # Merge role scores back in
    role_scores_only = role_scores_df.copy()
    role_scores_only.index = role_scores_only.index.astype(final_df.index.dtype)
    final_df = pd.concat([final_df, role_scores_only], axis=1)
    final_df = final_df.loc[:, ~final_df.columns.duplicated()]

    # debug_nan(final_df, "calculate_tactical_potential")
    return final_df
