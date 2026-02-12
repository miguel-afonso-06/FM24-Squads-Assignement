import pandas as pd
from utils import *

# From HTML to DataFrame
file = pd.read_html('Squad 25-11-10.html', encoding='utf-8', index_col=0,)
data = file[0]

# Position to List
"""
with open('dfCols.txt','w') as colstxt:
    with pd.option_context('display.max_rows',None):
        colstxt.write(str(data.dtypes))
"""

pos = data[['Position']].copy()

data['Position'] = data['Position'].apply(parse_positions)

# Calculate Feet
feet_df = data[['Left Foot', 'Right Foot']].copy()
feet_df = feet_df.map(lambda x: feet_table.get(x, x))

data['Left Foot'] = feet_df['Left Foot']
data['Right Foot'] = feet_df['Right Foot']

data['Feet'] = data[['Left Foot', 'Right Foot']].sum(axis=1)

"""
with pd.option_context("display.max_columns", None):
    print(data)
"""

# ...existing code...

attrbutes_weights = attrbutes_weights_df()

# Convert attribute columns to numeric
attribute_cols = [col for col in attrbutes_weights.columns if col != 'Roles']
attrbutes_weights[attribute_cols] = attrbutes_weights[attribute_cols].apply(pd.to_numeric, errors='coerce')

# Find columns that exist in both dataframes
attribute_cols = [col for col in attrbutes_weights.columns if col != 'Roles' and col in data.columns]

squad_role_score = pd.concat([
    data[['Name']],
    pd.DataFrame(
        0.0,
        index=data.index,
        columns=attrbutes_weights['Roles'].unique()
    )
], axis=1)

# Calculate weighted score for each role
for role in attrbutes_weights['Roles'].unique():
    role_weights = attrbutes_weights[attrbutes_weights['Roles'] == role][attribute_cols]
    weight_sum = role_weights.sum(axis=1).values[0]
    
    # Weighted average: sum(player_attr * weight) / sum(weights)
    squad_role_score[role] = (
        round(data[attribute_cols].mul(role_weights.values[0]) / weight_sum,2)
    ).sum(axis=1)

#print(squad_role_score)

# Getting a squad depth list for given roles
give_tactic = [
    [["GK"], "Sweeper Keeper (At)"],
    [["D", "R"], "Complete Wing-Back (Su)"],
    [["D", "C"], "Central Defender (De)"],
    [["D", "C"], "Central Defender (De)"],
    [["D", "L"], "Complete Wing-Back (At)"],
    [["DM"], "Ball Winning Midfielder DM (De)"],
    [["M", "C"], "Mezzala (Su)"],
    [["M", "C"], "Advanced Playmaker CM (At)"],
    [["AM", "R"], "Winger (At)"],
    [["AM", "L"], "Inside Forward (Su)"],
    [["ST", "C"], "Advanced Forward (At)"],
]

from potentialEstimation import *

# Run the tactical calculation
potential_report = calculate_tactical_potential(data, squad_role_score, give_tactic)

# Filter out players who don't fit the tactic and sort by potential
final_view = potential_report[potential_report['Tactical Role'] != "No Tactic Match"].sort_values(by='Potential Estimate', ascending=False)

#print(final_view.head(20))

# Add this at the end of htmlReader.py or ensure the function returns these columns
def get_final_squad_df(data, squad_role_score, tactic):
    # Call the potential function we created previously
    report = calculate_tactical_potential(data, squad_role_score, tactic)
    
    # Merge with original data to keep 'Value_Num' and 'Personality' for the selection script
    report['Value_Num'] = data['Transfer Value'].apply(parse_transfer_value)
    report['Personality'] = data['Personality']
    
    # Add a 'Keep' flag: Potential > 13.0 or Current > 12.0 is usually worth keeping
    report['Worth_Keeping'] = (report['Potential Estimate'] >= 13.0) | (report['Current Quality'] >= 11.5)
    
    return report

# Final run
from squad_selection import organize_squads

report_df = get_final_squad_df(data, squad_role_score, give_tactic)
squad_plan = organize_squads(report_df, give_tactic)

""" with pd.option_context('display.max_rows', None) and pd.option_context('display.max_columns', None):
    print(squad_plan.sort_values(by=['Decision', 'Potential Estimate'], ascending=[True, False]))
 """
output_df = squad_plan.sort_values(by=['Decision', 'Potential Estimate'], ascending=[True, False])
output_df.to_csv('squadSelectionOutput.csv')