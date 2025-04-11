import pandas as pd
from tqdm import tqdm
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from rapidfuzz import fuzz

# Step 1: Load Foray data
foray_df = pd.read_csv("data/2023ForayNL_Fungi.csv", encoding='latin-1')[
    ["id", "genus_and_species_foray_name", "genus_and_species_org_entry"]
].rename(columns={
    "id": "Foray_ID",
    "genus_and_species_foray_name": "Foray_Name",
    "genus_and_species_org_entry": "Org_Entry"
})

# Step 2: Load MycoBank data
myco_df = pd.read_csv("data/MBList.csv", encoding='latin-1')[
    ["MycoBank #", "Taxon name", "Current name.Taxon name"]
].rename(columns={
    "MycoBank #": "MycoBank_ID",
    "Taxon name": "Taxon_Name",
    "Current name.Taxon name": "Updated_Taxon_Name"
})

# Step 3: Add Status column
def is_valid_update(updated, original):
    invalid_values = {"", "-", "—", "--", "n/a", "none", "null", "na"}
    if pd.isna(updated):
        return False
    updated = str(updated).strip().lower()
    original = str(original).strip().lower()
    return updated not in invalid_values and updated != original

myco_df["Status"] = myco_df.apply(
    lambda row: "UPDATED" if is_valid_update(row["Updated_Taxon_Name"], row["Taxon_Name"]) else "SAME",
    axis=1
)

# Step 4: Group MycoBank entries by first letter of Taxon_Name and/or Updated_Taxon_Name
grouped_candidates = defaultdict(list)

for _, row in myco_df.iterrows():
    taxon = str(row["Taxon_Name"]).strip()
    updated = str(row["Updated_Taxon_Name"]).strip() if pd.notna(row["Updated_Taxon_Name"]) else ""
    first_letters = set()

    if taxon:
        first_letters.add(taxon[0].upper())
    if updated:
        first_letters.add(updated[0].upper())

    for letter in first_letters:
        grouped_candidates[letter].append((taxon, updated, row))

# Step 5: Matching function
def best_match(query, source):  # source = "Foray_Name" or "Org_Entry"
    if not query:
        return None, 0, ""
    first_letter = query[0].upper()
    candidates = grouped_candidates.get(first_letter, [])

    best_score = 0
    best_row = None
    explanation = ""

    for taxon, updated, row_data in candidates:
        score_taxon = fuzz.ratio(query, taxon)
        score_updated = fuzz.ratio(query, updated) if updated else 0

        if score_taxon >= score_updated and score_taxon > best_score:
            best_score = score_taxon
            best_row = row_data
            explanation = "FORAY → TAXON" if source == "Foray_Name" else "ORG → TAXON"
        elif score_updated > score_taxon and score_updated > best_score:
            best_score = score_updated
            best_row = row_data
            explanation = "FORAY → UPDATED" if source == "Foray_Name" else "ORG → UPDATED"

    return best_row, best_score, explanation

def match_row(row):
    fid = row["Foray_ID"]
    foray_name = str(row["Foray_Name"]).strip()
    org_entry = str(row["Org_Entry"]).strip()

    matched_row, score, explanation = best_match(foray_name, "Foray_Name")
    if matched_row is None:
        matched_row, score, explanation = best_match(org_entry, "Org_Entry")

    if matched_row is not None:
        return {
            "Foray_ID": fid,
            "Foray_Name": foray_name,
            "Org_Entry": org_entry,
            "Taxon_Name": matched_row["Taxon_Name"],
            "Updated_Taxon_Name": matched_row["Updated_Taxon_Name"],
            "MycoBank_ID": matched_row["MycoBank_ID"],
            "Status": matched_row["Status"],
            "Similarity": score,
            "Explanation": explanation
        }
    else:
        return {
            "Foray_ID": fid,
            "Foray_Name": foray_name,
            "Org_Entry": org_entry,
            "Taxon_Name": None,
            "Updated_Taxon_Name": None,
            "MycoBank_ID": None,
            "Status": "NO_MATCH",
            "Similarity": 0,
            "Explanation": "No match found"
        }

# Step 6: Run with ThreadPoolExecutor and tqdm
with ThreadPoolExecutor() as executor:
    rows = [row for _, row in foray_df.iterrows()]
    results = list(tqdm(executor.map(match_row, rows), total=len(rows), desc="Matching"))

# Step 7: Save result
result_df = pd.DataFrame(results)
result_df.to_csv("data/matching_result_apr_2025.csv", index=False)

print("Done")
