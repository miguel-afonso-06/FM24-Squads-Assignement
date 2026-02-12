# utils.py

import re
import pandas as pd

DEBUG = True

def parse_positions(pos_str):
    if pd.isna(pos_str):
        return []
    
    # 1. Split by comma to get main groups: ['DM', ' M/AM(RC)', ' ST(C)']
    groups = pos_str.split(',')
    parsed_list = []

    for group in groups:
        group = group.strip()
        
        # 2. Extract sides in parentheses (e.g., 'RC' from 'AM(RC)')
        sides_match = re.search(r'\((.*?)\)', group)
        sides = list(sides_match.group(1)) if sides_match else ['']
        
        # 3. Remove the parentheses part to get the areas: 'M/AM'
        areas_part = re.sub(r'\(.*?\)', '', group).strip()
        
        # 4. Handle the slash (e.g., 'M/AM' -> ['M', 'AM'])
        areas = [a.strip() for a in areas_part.split('/')]
        
        # 5. Combine Areas and Sides
        # For 'M/AM(RC)', this creates [M, R], [M, C], [AM, R], [AM, C]
        for area in areas:
            for side in sides:
                parsed_list.append([area, side])
                
    return parsed_list

def attrbutes_weights_df():
    attrbutes_weights = pd.read_json('attributes_weights.json')
    return attrbutes_weights

#print(attrbutes_weights_df())

FOOT_MAPPING = {
    "Very Strong": 10,
    "Strong": 8,
    "Fairly Strong":6,
    "Reasonable":4,
    "Weak":2,
    "Very Weak":0
}

def calculate_feet_score(row):
    """Calculates the 'Feet' value based on Left and Right foot strings."""
    left_str = str(row.get('Left Foot', 'Weak')).strip()
    right_str = str(row.get('Right Foot', 'Weak')).strip()
    
    left_val = FOOT_MAPPING.get(left_str, 5)
    right_val = FOOT_MAPPING.get(right_str, 5)
    
    # We take the average to match your 16 and 14 examples
    return (left_val + right_val) / 2

# Add this to utils.py

def calculate_all_role_scores(df, weights_df):
    # 1. Create the 'Feet' column dynamically
    df['Feet'] = df.apply(calculate_feet_score, axis=1)
    
    # 2. Get attributes from JSON
    all_keys = weights_df.index.tolist()
    
    # 3. FILTER: Now 'Feet' will be included because it exists in df.columns
    attributes = [a for a in all_keys if a in df.columns]
    
    # 4. Clean data and ensure numeric
    for attr in attributes:
        df[attr] = pd.to_numeric(df[attr], errors='coerce').fillna(5)
            
    results = df[['Name']].copy()
    
    # 5. Calculate weighted averages
    role_scores = {}
    for role in weights_df.columns:
        role_weights = weights_df[role].loc[attributes]
        role_scores[role] = df[attributes].dot(role_weights) / role_weights.sum()
    results = pd.concat([results, pd.DataFrame(role_scores)], axis=1)
        
    return results

def parse_transfer_value(val_str):
    """Converts FM transfer value strings (e.g., '€10M - €20M') to a float average."""
    if pd.isna(val_str) or val_str == '€0' or val_str == '-':
        return 0.0
    
    try:
        # Remove currency and whitespace
        val_str = val_str.replace('€', '').replace('£', '').strip()
        
        # Handle ranges by taking the average
        if '-' in val_str:
            parts = val_str.split('-')
            return (parse_transfer_value(parts[0]) + parse_transfer_value(parts[1])) / 2
        
        # Convert suffixes
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