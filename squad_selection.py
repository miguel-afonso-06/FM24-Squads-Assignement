import pandas as pd
import re
from datetime import datetime
from utils import debug_nan

DEBUG = False


def parse_dob_and_reference_year(dob_str):
    if not isinstance(dob_str, str):
        return None, None

    date_match = re.search(r"(\d{1,2}/\d{1,2}/\d{4})", dob_str)
    age_match = re.search(r"\((\d+)\s+years?\s+old\)", dob_str)

    if not date_match or not age_match:
        return None, None

    birth_date = datetime.strptime(date_match.group(1), "%d/%m/%Y")
    shown_age = int(age_match.group(1))
    inferred_year = birth_date.year + shown_age

    return birth_date, inferred_year


def age_on_jan_first(birth_date, year):
    jan_first = datetime(year, 1, 1)
    age = jan_first.year - birth_date.year
    if birth_date.month > 1 or (birth_date.month == 1 and birth_date.day > 1):
        age -= 1
    return age


def organize_squads(df, tactic, roles_df):
    df = df.copy()
    df['Decision'] = "Unassigned"
    df['Squad'] = "None"
    df['Assigned Role'] = "None"

    # ================= AGE ELIGIBILITY =================
    eligibility_u19 = {}
    eligibility_u23 = {}

    if DEBUG:
        print("\n========== AGE ELIGIBILITY DEBUG ==========")
        print("\nColumns in DF:")
        print(df.columns.tolist())
        print("\nPrint the Position_List column in DF:")
        print(df['Position_List'])
        print("\nSample Date of Birth values:")
        print(df["DoB"].head(10))

    for idx, row in df.iterrows():
        birth_date, ref_year = parse_dob_and_reference_year(row.get("DoB"))

        if birth_date and ref_year:
            age_jan1 = age_on_jan_first(birth_date, ref_year)
            eligibility_u19[idx] = age_jan1 <= 18
            eligibility_u23[idx] = age_jan1 <= 22

            if DEBUG:
                print(
                    f"{row.get('Name')} | DoB: {birth_date.date()} | "
                    f"RefYear: {ref_year} | Age Jan1: {age_jan1} | "
                    f"U19: {eligibility_u19[idx]} | U23: {eligibility_u23[idx]}"
                )
        else:
            eligibility_u19[idx] = False
            eligibility_u23[idx] = False

            if DEBUG:
                print(
                    f"{row.get('Name')} | DoB parsing FAILED -> {row.get('DoB')}"
                )

    if DEBUG:
        print("===========================================\n")

    # ================= ROLE -> POSITIONS MAPPING =================
    # Accept either:
    # 1) dict: {role_name: [["AREA", "SIDE"], ["AREA"], ...]}
    # 2) DataFrame with the old shape containing a "Positions" field per role
    def normalize_role_positions(raw_positions):
        normalized = []
        for pos in raw_positions or []:
            if not isinstance(pos, (list, tuple)) or len(pos) == 0:
                continue
            area = str(pos[0]).strip()
            side = str(pos[1]).strip() if len(pos) > 1 else ''
            normalized.append([area, side])
        return normalized

    role_to_positions = {}
    if isinstance(roles_df, dict):
        for role_name, raw_positions in roles_df.items():
            role_to_positions[role_name] = normalize_role_positions(raw_positions)
    elif isinstance(roles_df, pd.DataFrame):
        for role_name in roles_df.columns:
            try:
                raw_positions = roles_df.at[0, role_name]["Positions"]
            except Exception:
                raw_positions = []
            role_to_positions[role_name] = normalize_role_positions(raw_positions)

    # ================= DYNAMIC THRESHOLDS =================
    ASSET_VALUE_THRESHOLD = df['Value_Num'].quantile(0.75)
    DEPTH_THRESHOLD = 1 # with 1.5 -> 14 EB; 
    squad_value_q25 = df['Value_Num'].quantile(0.25)

    squad_configs = [
        {'name': 'Senior Team', 'slots': [1, 2]},
        {'name': 'B Team', 'slots': [1, 2]},
        {'name': 'U23 Team', 'slots': [1, 2]},
        {'name': 'U19 Team', 'slots': [1, 2]}
    ]

    # ================= Tactical Slot Filling =================
    for squad in squad_configs:

        if DEBUG:
            print(f"\n---- Filling {squad['name']} ----")

        for slot in squad['slots']:
            for _, role in tactic:
                role = role.strip()

                # Filter unassigned players
                eligible = df[df['Decision'] == "Unassigned"]

                if role not in role_to_positions:
                    if DEBUG:
                        print(f"Role {role} not in role_to_positions, skipping")
                    continue

                # Get eligible positions for this role
                role_positions = role_to_positions.get(role, [])  # list of [area, side]

                # Filter players who can play at least one of the role positions
                def can_play_role(pos_list):
                    for area, side in pos_list:
                        for r_area, r_side in role_positions:
                            # side can be empty or must match
                            if area == r_area and (side == r_side or r_side == ''):
                                return True
                    return False

                eligible = eligible[eligible['Position_List'].apply(can_play_role)]

                if DEBUG:
                    print(f"{squad['name']} | Role: {role} | After role filter: {len(eligible)}")

                # Age filters
                if squad['name'] == 'U23 Team':
                    eligible = eligible[
                        eligible.index.map(lambda x: eligibility_u23.get(x, False))
                    ]
                    if DEBUG:
                        print(f"After U23 age filter: {len(eligible)}")

                if squad['name'] == 'U19 Team':
                    eligible = eligible[
                        eligible.index.map(lambda x: eligibility_u19.get(x, False))
                    ]
                    if DEBUG:
                        print(f"After U19 age filter: {len(eligible)}")

                if eligible.empty:
                    continue

                # Senior / other selection logic unchanged
                if squad['name'] == 'Senior Team':
                    pick = eligible.sort_values(role, ascending=False).index[0]
                else:
                    eligible = eligible.assign(
                        DevScore=(0.4 * eligible[role]) +
                                (0.6 * eligible['Potential Estimate'])
                    )
                    pick = eligible.sort_values('DevScore', ascending=False).index[0]

                if DEBUG:
                    print(f"Selected: {df.at[pick, 'Name']}")

                df.at[pick, 'Decision'] = f"{squad['name']} #{slot}"
                df.at[pick, 'Squad'] = squad['name']
                df.at[pick, 'Assigned Role'] = role

    # ================= Backup Reference =================
    senior_df = df[df['Squad'] == 'Senior Team']
    senior_mean_cq = senior_df['Current Quality'].mean() if not senior_df.empty else 10.0

    # ================= Post-assignment Logic =================
    for idx, row in df[df['Decision'] == "Unassigned"].iterrows():

        growth = (
            row['Potential Estimate'] - row['Current Quality']
            if pd.notna(row['Potential Estimate']) and pd.notna(row['Current Quality'])
            else 0
        )

        if row.get('Value_Num', 0) >= ASSET_VALUE_THRESHOLD:
            df.at[idx, 'Decision'] = "Loan Out (Asset)"
            df.at[idx, 'Squad'] = "External"

        elif row.get('Current Quality', 0) >= (senior_mean_cq - DEPTH_THRESHOLD):
            df.at[idx, 'Decision'] = "Emergency Backup"
            df.at[idx, 'Squad'] = "B Team"

        elif pd.notna(row.get('Potential Estimate')) and (
            row['Potential Estimate'] >= df['Potential Estimate'].quantile(0.85)
            and growth >= 1.5
        ):
            df.at[idx, 'Decision'] = "Loan Out (Prospect)"
            df.at[idx, 'Squad'] = "External"

        else:
            role_cols = [
                c for c in df.columns
                if c not in [
                    'Decision', 'Squad', 'Assigned Role', 'Name',
                    'Current Quality', 'Potential Estimate', 'Value_Num'
                ]
                and pd.api.types.is_numeric_dtype(df[c])
            ]

            best_role_score = row[role_cols].max(skipna=True) if role_cols else 0

            if role_cols:
                role_quantile = df[role_cols].quantile(0.75).max()
            else:
                role_quantile = 0

            if best_role_score >= role_quantile or growth >= 1.5:
                df.at[idx, 'Decision'] = "Loan Out (Prospect)"
                df.at[idx, 'Squad'] = "External"
            else:
                if row.get('Value_Num', 0) >= squad_value_q25:
                    df.at[idx, 'Decision'] = "Sell"
                else:
                    df.at[idx, 'Decision'] = "Release"
    if DEBUG: print(f"[DEBUG] organize_squads.df:\n{df}\n")
    # debug_nan(df, "organize_squads")
    return df
