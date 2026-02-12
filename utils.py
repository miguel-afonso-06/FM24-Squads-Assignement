import re
import pandas as pd

DEBUG = True

FOOT_MAPPING = {
    "Very Strong": 10,
    "Strong": 8,
    "Fairly Strong": 6,
    "Reasonable": 4,
    "Weak": 2,
    "Very Weak": 0
}

def parse_positions(pos_str):
    if pd.isna(pos_str):
        return []
    
    groups = pos_str.split(',')
    parsed_list = []

    for group in groups:
        group = group.strip()
        sides_match = re.search(r'\((.*?)\)', group)
        sides = list(sides_match.group(1)) if sides_match else ['']
        areas_part = re.sub(r'\(.*?\)', '', group).strip()
        areas = [a.strip() for a in areas_part.split('/')]
        
        for area in areas:
            for side in sides:
                parsed_list.append([area, side])
                
    return parsed_list

def calculate_feet_score(row):
    left_str = str(row.get('Left Foot', 'Weak')).strip()
    right_str = str(row.get('Right Foot', 'Weak')).strip()
    
    left_val = FOOT_MAPPING.get(left_str, 5)
    right_val = FOOT_MAPPING.get(right_str, 5)
    
    return (left_val + right_val) / 2

def calculate_all_role_scores(df, weights_df):
    df['Feet'] = df.apply(calculate_feet_score, axis=1)
    
    all_keys = weights_df.index.tolist()
    attributes = [a for a in all_keys if a in df.columns]
    
    for attr in attributes:
        df[attr] = pd.to_numeric(df[attr], errors='coerce').fillna(5)
            
    results = df[['Name']].copy()
    role_scores = {}

    for role in weights_df.columns:
        role_weights = weights_df[role].loc[attributes]
        weight_sum = role_weights.sum()
        if weight_sum == 0:
            role_scores[role] = 0
        else:
            role_scores[role] = df[attributes].dot(role_weights) / weight_sum

    results = pd.concat([results, pd.DataFrame(role_scores)], axis=1)
    return results

def parse_transfer_value(val_str):
    if pd.isna(val_str) or val_str == '€0' or val_str == '-':
        return 0.0
    
    try:
        val_str = val_str.replace('€', '').replace('£', '').strip()
        
        if '-' in val_str:
            parts = val_str.split('-')
            return (parse_transfer_value(parts[0]) + parse_transfer_value(parts[1])) / 2
        
        multiplier = 1
        if 'K' in val_str:
            multiplier = 1_000
            val_str = val_str.replace('K', '')
        elif 'M' in val_str:
            multiplier = 1_000_000
            val_str = val_str.replace('M', '')
            
        return float(val_str) * multiplier
    except:
        return 0.0
