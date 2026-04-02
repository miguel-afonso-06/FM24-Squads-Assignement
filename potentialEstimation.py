import pandas as pd
from utils import debug_nan

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
    # Returns a normalized factor roughly between 0.8 and 1.25
    return 1.0 + ((avg - 10) / 40)

def age_growth_probability(age):
    """Returns the maximum percentage of the 'gap' to 20 a player can close."""
    if age <= 18: return 0.70  # High growth potential
    if age <= 21: return 0.45  # Significant growth
    if age <= 24: return 0.20  # Late development
    if age <= 27: return 0.05  # Peak/Minimal growth
    return 0.0

def calculate_tactical_potential(df, role_scores_df, tactic):
    results = []
    
    for idx, row in df.iterrows():
        # if DEBUG: print(f"[DEBUG] row:\n{row}\n")
        scores_row = role_scores_df[role_scores_df.index == idx]
        if scores_row.empty:
            scores_row = pd.DataFrame(columns=role_scores_df.columns, index=[idx])

        player_positions = row.get('Position_List', [])
        """ with pd.option_context('display.max_columns', None, 'display.max_rows', None):
            if DEBUG: print(f"[DEBUG] player_positions:\n{player_positions}\n") """
        eligible_roles = []

        # if DEBUG: print(f"[DEBUG] tactic:\n{tactic}\n")
        for pos_side, role_name in tactic:
            # if DEBUG: print(f"[DEBUG] pos_side:\n{pos_side}\n")
            for player_pos_side in player_positions:
                if isinstance(player_pos_side, list):
                    player_pos_side_flat = [p for p in player_pos_side if p]
                else:
                    player_pos_side_flat = [player_pos_side,]
                """ with pd.option_context('display.max_columns', None, 'display.max_rows', None):
                    if DEBUG: print(f"[DEBUG] player_pos_side_flat:\n{player_pos_side_flat}\n") """
                
                
                if all(p in player_pos_side_flat for p in pos_side):
                    eligible_roles.append(role_name)

        if DEBUG:
            # 1. Perform the comprehension first
            result = [p for p in pos_side if p in player_pos_side_flat]

            # 2. Use the bound variable in the print statement
            print(f"[DEBUG] positions eligibility:\n"
                F"name: {row['Name']}\n"
                f"player_positions: {player_positions}\n"
                f"player_pos_side: {player_pos_side}\n"
                f"player_pos_side_flat: {player_pos_side_flat}\n"
                f"pos_side: {pos_side}\n"
                f"eligible:\n{result if len(result) == len(pos_side) else None}")

        if eligible_roles:
            eligible = scores_row[eligible_roles].iloc[0]
            """ with pd.option_context('display.max_columns', None, 'display.max_rows', None):
                if DEBUG: print(f"[DEBUG] eligible:\n{eligible}\n") """
            role_score = eligible.max()
        else:
            role_score = None

        age = pd.to_numeric(row.get('Age', 25), errors='coerce')
        age = 25 if pd.isna(age) else age

        personality = str(row.get('Personality', 'Balanced')).strip()
        p_factor = PERSONALITY_MAP.get(personality, 1.0)

        if role_score is not None:
            # NEW GAP-CLOSING FORMULA:
            # growth_prob is how efficiently they close the gap to 20.0
            # DNA and Personality act as modifiers to their age-based growth ceiling.
            dna = dna_factor(row)
            growth_prob = age_growth_probability(age) * ((dna + p_factor) / 2)
            
            # Potential = Current + (Remaining Room * Probability)
            pe = role_score + (20.0 - role_score) * growth_prob
            pe = min(20.0, max(role_score, pe))
        else:
            pe = None

        results.append({
            'UID': idx,
            'Name': row['Name'],
            'Current Quality': round(role_score, 2) if role_score is not None else None,
            'Potential Estimate': round(pe, 2) if pe is not None else None,
            'Tactical Role': eligible_roles[0] if eligible_roles else None,
            'Personality_Factor': p_factor
        })

    final_df = pd.DataFrame(results).set_index('UID', drop=False)

    role_scores_only = role_scores_df.copy()
    role_scores_only.index = role_scores_only.index.astype(final_df.index.dtype)
    final_df = pd.concat([final_df, role_scores_only], axis=1)
    final_df = final_df.loc[:, ~final_df.columns.duplicated()]
    # debug_nan(final_df, "calculate_tactical_potential")
    """ with pd.option_context('display.max_columns', None, 'display.max_rows', None):
        if DEBUG: print(f"[DEBUG] final_df:\n{final_df}\n") """

    return final_df