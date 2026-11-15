import pandas as pd
from geopy.distance import geodesic
from scipy.spatial import cKDTree
import numpy as np

def datasetMatching():

    flag_list = ["LeeCounty", "CapeCoral"]

    for flag in flag_list:

        # === Step 1: Load CSVs ===
        if flag == "LeeCounty":
            df = pd.read_csv("<path to LCDA dataset for Lee County>")

            # Function to combine columns, skipping "<Null>" and NaN
            def combine_columns(df, cols):
                return df[cols].apply(
                    lambda row: " ".join([str(v) for v in row if pd.notna(v) and str(v) != "<Null>"]),
                    axis=1
                )

            # Group columns by type
            destroyed_cols = [col for col in df.columns if "destroyed damage" in col.lower()]
            major_cols = [col for col in df.columns if "major damage" in col.lower()]
            minor_cols = [col for col in df.columns if "minor damage" in col.lower()]
            affected_cols = [col for col in df.columns if "affected damage" in col.lower()]

            # Combine them into new columns without "<Null>"
            df["DescribesDestroyed"] = combine_columns(df, destroyed_cols)
            df["DescribesMajor"] = combine_columns(df, major_cols)
            df["DescribesMinor"] = combine_columns(df, minor_cols)
            df["DescribesAffected"] = combine_columns(df, affected_cols)

            df_LCDA = df

        elif flag == "CapeCoral":
            df_LCDA = pd.read_csv("<path to LCDA dataset for Cape Coral>")

        df_LCPA = pd.read_csv("<path to LCPA dataset>")

        # === Step 2: Drop rows with missing coordinates ===
        df_LCDA = df_LCDA.dropna(subset=['Latitude', 'Longitude']).reset_index(drop=True)
        df_LCPA = df_LCPA.dropna(subset=['Latitude', 'Longitude']).reset_index(drop=True)

        # === Step 3: Initialize match codes ===
        df_LCDA['match_code_LCPA'] = np.nan
        df_LCPA['match_code_LCPA'] = np.nan

        ### ========== First Match: LCDA <-> LCPA ==========
        coords_LCDA_array = np.radians(df_LCDA[['Latitude', 'Longitude']].values)
        coords_LCPA_array = np.radians(df_LCPA[['Latitude', 'Longitude']].values)

        tree_LCPA = cKDTree(coords_LCPA_array)
        radius = 30 / 6371000  # 30 meters in radians
        matches = tree_LCPA.query_ball_point(coords_LCDA_array, radius)

        candidates = []
        for i, candidate_indices in enumerate(matches):
            for j in candidate_indices:
                dist = geodesic(
                    (df_LCDA.loc[i, 'Latitude'], df_LCDA.loc[i, 'Longitude']),
                    (df_LCPA.loc[j, 'Latitude'], df_LCPA.loc[j, 'Longitude'])
                ).meters
                if dist <= 30:
                    candidates.append((i, j, dist))

        candidates.sort(key=lambda x: x[2])
        matched_LCDA = set()
        matched_LCPA = set()
        match_id = 1

        for i, j, dist in candidates:
            if i not in matched_LCDA and j not in matched_LCPA:
                df_LCDA.at[i, 'match_code_LCPA'] = match_id
                df_LCPA.at[j, 'match_code_LCPA'] = match_id
                matched_LCDA.add(i)
                matched_LCPA.add(j)
                match_id += 1

        # === Step 6: Prepare final merged DataFrame ===
        if flag == "LeeCounty":
            df_LCDA_filtered = df_LCDA[[
                'Latitude', 'Longitude', 'Type of damage?', 'DescribesDestroyed', 'DescribesMajor', 'DescribesMinor',
                'DescribesAffected', 'Notes (optional)', 'DamageLevel *', 'BldgValue *', 'EstLoss *', 'match_code_LCPA'
            ]]

        elif flag == "CapeCoral":
            df_LCDA_filtered = df_LCDA[[
                'Latitude', 'Longitude', 'primaryCause', 'secondaryCause', 'damage', 'structureValue', "description",
                'totalCost', 'match_code_LCPA'
            ]]

        df_LCPA_matched = df_LCPA[df_LCPA['match_code_LCPA'].notna()][[
            'match_code_LCPA', 'Use Code Description', 'Number of Stories', 'Year of Built', 'Retrofit Year',
            'Roof Retrofit Year'
        ]]

        df_merged = df_LCDA_filtered.merge(df_LCPA_matched, on='match_code_LCPA', how='left')

        if flag == "LeeCounty":
            df_merged_LeeCounty = df_merged

        elif flag == "CapeCoral":
            df_merged_CapeCoral = df_merged


    return df_merged_LeeCounty, df_merged_CapeCoral