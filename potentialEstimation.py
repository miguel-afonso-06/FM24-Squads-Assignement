# potentialEstimation.py
import pandas as pd

DEBUG = True

# Softened Personality multipliers to prevent "Negative Growth"
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
    # Reduced weight so mental "DNA" doesn't ruin Potential Estimate
    det = pd.to_numeric(row.get('Det', 10), errors='coerce') or 10
    wor = pd.to_numeric(row.get('Wor', 10), errors='coerce') or 10
    team = pd.to_numeric(row.get('Tea', 10), errors='coerce') or 10
    avg = (det + wor + team) / 3
    return 1.0 + ((avg - 10) / 40) # Max +/- 0.25 impact

def age_multiplier(age):
    if age <= 18: return 1.4
    if age <= 21: return 1.2
    if age <= 24: return 1.1
    return 1.0

def calculate_tactical_potential(df, role_scores_df, tactic):
    results = []
    tactical_roles = [role for pos, role in tactic]
    
    for idx, row in df.iterrows():
        uid = idx
        scores_row = role_scores_df[role_scores_df.index == uid]
        if scores_row.empty: continue

        eligible = scores_row[tactical_roles].iloc[0]
        role_score = eligible.max()
        age = pd.to_numeric(row.get('Age', 25), errors='coerce') or 25
        
        personality = str(row.get('Personality', 'Balanced')).strip()
        p_factor = PERSONALITY_MAP.get(personality, 1.0)
        
        # New Potential Calculation: Base CQ * multipliers
        raw_pe = role_score * age_multiplier(age) * dna_factor(row) * p_factor
        
        # Logic check: Potential cannot be lower than Current Quality
        pe = max(role_score, raw_pe)

        results.append({
            'UID': idx,
            'Name': row['Name'],
            'Current Quality': round(role_score, 2),
            'Potential Estimate': round(pe, 2),
            'Tactical Role': eligible.idxmax(),
            'Personality_Factor': p_factor
        })
    results_df = pd.DataFrame(results).set_index('UID')
    # if DEBUG: print(f"[DEBUG] potentialEstimation.calculate_tactical_potential results_df:\n{results_df}")
    return results_df