# core/logic/full_match_pipeline.py
"""
Builds all matching artifacts from CSVs:
- Saves originals (ForayFungi2023, MycoBankList)   [can skip with SKIP_SAVE_ORIGINALS=1]
- Computes:
    * ForayPerfectMatch (3 columns all equal)
    * ForayMismatchExplanation (mismatch category + the 3 names)
    * ForayPerfectMycoMatch (perfect + exact MycoBank hit)
    * ForayMismatchMycoScores (scores + chosen MycoBank candidate with TAXON/UPDATED expl)

Speed notes:
- RapidFuzz releases the GIL, so threading helps — we reuse one ThreadPoolExecutor.
- First-letter bucketing shrinks the candidate pool drastically.
- LRU cache avoids re-scoring repeated strings.
"""

import os
import pandas as pd
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor
from rapidfuzz import fuzz

from core.models import ForayFungi2023, MycoBankList

FORAY_PATH = "data/2023ForayNL_Fungi.csv"
MYCOBANK_PATH = "data/MBList.csv"


# ---------- helpers ----------
def _norm(s: str) -> str:
    return (s or "").strip()


def _preferred_name(taxon_name: str, current_name: str) -> str:
    """Prefer current name; else taxon name."""
    return _norm(current_name) or _norm(taxon_name)


def _choose_workers() -> int:
    """
    Thread count policy:
      - env override: PIPELINE_WORKERS
      - else: 2 * CPU, clamped to [4, 16]
    """
    override = os.getenv("PIPELINE_WORKERS")
    if override and override.isdigit():
        return max(1, int(override))
    cpu = os.cpu_count() or 4
    return min(16, max(4, cpu * 2))


def _env_truthy(name: str) -> bool:
    return (os.getenv(name) or "").strip().lower() in {"1", "true", "yes", "y"}


# ---------- main pipeline ----------
def run_pipeline():
    # IO
    foray_usecols = ["id", "genus_and_species_org_entry", "genus_and_species_conf", "genus_and_species_foray_name"]
    myco_usecols = [
        "MycoBank #",
        "Taxon name",
        "Current name.Taxon name",
        "Authors",
        "Year of effective publication",
        "Hyperlink",
    ]

    # Fail fast if files are missing (clearer error than pandas)
    if not os.path.exists(FORAY_PATH):
        raise FileNotFoundError(f"Missing Foray CSV: {FORAY_PATH}")
    if not os.path.exists(MYCOBANK_PATH):
        raise FileNotFoundError(f"Missing MycoBank CSV: {MYCOBANK_PATH}")

    print(f"📁 Loading data files...")
    print(f"   📄 Foray data: {FORAY_PATH}")
    print(f"   📄 MycoBank data: {MYCOBANK_PATH}")
    
    foray_df = pd.read_csv(FORAY_PATH, encoding="latin-1", dtype=str, usecols=foray_usecols).fillna("")
    myco_df = pd.read_csv(MYCOBANK_PATH, encoding="latin-1", dtype=str, usecols=myco_usecols).fillna("")
    
    print(f"✅ Data loaded: {len(foray_df):,} Foray records, {len(myco_df):,} MycoBank records")

    # Normalize columns to match DB schema
    myco_df = myco_df.rename(
        columns={
            "MycoBank #": "mycobank_id_raw",
            "Taxon name": "taxon_name",
            "Current name.Taxon name": "current_name",
            "Year of effective publication": "year",
            "Hyperlink": "hyperlink",
        }
    )
    for col in ["mycobank_id_raw", "taxon_name", "current_name", "year", "hyperlink"]:
        myco_df[col] = myco_df[col].map(_norm)
    # authors column name sometimes differs; normalize it
    if "Authors" in myco_df.columns:
        myco_df["authors"] = myco_df["Authors"].map(_norm)
    elif "authors" in myco_df.columns:
        myco_df["authors"] = myco_df["authors"].map(_norm)
    else:
        myco_df["authors"] = ""

    # Build grouped candidates for the old matching logic:
    # key: first letter (upper), value: list of tuples (taxon, current, row_data_dict)
    print(f"🔍 Building MycoBank search index by first letter...")
    
    grouped_candidates: dict[str, list[tuple[str, str, dict]]] = {}
    for _, r in myco_df.iterrows():
        taxon = _norm(r["taxon_name"])
        updated = _norm(r["current_name"])
        row_dict = {
            "mycobank_id": _norm(r["mycobank_id_raw"]),
            "taxon_name": taxon,
            "current_name": updated,
            "authors": _norm(r["authors"]),
            "year": _norm(r["year"]),
            "hyperlink": _norm(r["hyperlink"]),
        }
        key = (_preferred_name(taxon, updated)[:1] or taxon[:1] or updated[:1] or "#").upper()
        grouped_candidates.setdefault(key, []).append((taxon, updated, row_dict))
    
    print(f"✅ Search index built: {len(grouped_candidates)} letter groups, avg {len(myco_df)/len(grouped_candidates):.0f} records/group")

    # Optional: save originals (idempotent; can skip to speed re-runs)
    if not _env_truthy("SKIP_SAVE_ORIGINALS"):
        _save_originals(foray_df, myco_df)

    # Outputs collected for your management command
    perfect_list = []      # ForayPerfectMatch
    mismatch_list = []     # ForayMismatchExplanation
    perfect_myco = []      # ForayPerfectMycoMatch
    mismatch_scores = []   # ForayMismatchMycoScores (+ chosen candidate)

    # ---- your old matching logic, with tiny tweaks & cache ----
    @lru_cache(maxsize=100_000)
    def best_match(query: str, source: str):
        """
        Returns (best_row_dict or None, best_score:int, explanation:str).
        explanation ∈ {'ORG → TAXON','ORG → UPDATED','CONF → TAXON','CONF → UPDATED',
                       'FORAY → TAXON','FORAY → UPDATED'}
        """
        q = _norm(query)
        if not q:
            return None, 0, ""
        first_letter = q[0].upper()
        candidates = grouped_candidates.get(first_letter, [])

        best_score = 0
        best_row = None
        explanation = ""

        # RapidFuzz happily compares raw strings; no need to pre-lower.
        for taxon, updated, row_data in candidates:
            score_taxon = fuzz.ratio(q, taxon) if taxon else 0
            score_updated = fuzz.ratio(q, updated) if updated else 0

            if score_taxon >= score_updated and score_taxon > best_score:
                best_score = score_taxon
                best_row = row_data
                explanation = f"{source} → TAXON"
            elif score_updated > score_taxon and score_updated > best_score:
                best_score = score_updated
                best_row = row_data
                explanation = f"{source} → UPDATED"

        return best_row, int(best_score), explanation

    def row_work(ex: ThreadPoolExecutor, fid: str, a: str, b: str, c: str):
        # 1) Perfect within-Foray
        if a == b == c:
            perfect_list.append({"foray_id": fid, "name": a})
            # Try exact in Myco (prefer rows with current_name). Score==100 ensures exact.
            row, score, _ = best_match(a, "FORAY")
            if row and score == 100:
                perfect_myco.append(
                    {
                        "foray_id": fid,
                        "mycobank_id": row["mycobank_id"],
                        "mycobank_name": _preferred_name(row["taxon_name"], row["current_name"]),
                    }
                )
            return

        # 2) Mismatch classification
        if a == b:
            explanation = "ORG_CONF_MATCH"
        elif a == c:
            explanation = "ORG_FORAY_MATCH"
        elif b == c:
            explanation = "CONF_FORAY_MATCH"
        else:
            explanation = "ALL_DIFFERENT"

        mismatch_list.append(
            {"foray_id": fid, "org_entry": a, "conf_name": b, "foray_name": c, "explanation": explanation}
        )

        # 3) Compute three best candidates (parallel on a shared executor)
        f_org = ex.submit(best_match, a, "ORG")
        f_conf = ex.submit(best_match, b, "CONF")
        f_foray = ex.submit(best_match, c, "FORAY")
        org_row, org_score, org_expl = f_org.result()
        conf_row, conf_score, conf_expl = f_conf.result()
        foray_row, foray_score, foray_expl = f_foray.result()

        # 4) Pick the single best overall candidate among the three
        triplets = [
            ("org", org_score, org_row, org_expl),
            ("conf", conf_score, conf_row, conf_expl),
            ("foray", foray_score, foray_row, foray_expl),
        ]
        triplets.sort(key=lambda t: t[1], reverse=True)
        _, best_score, best_row, best_expl = triplets[0]

        mb_id = None
        mb_name = None
        if best_row and best_score > 0:
            mb_id = best_row["mycobank_id"]
            mb_name = _preferred_name(best_row["taxon_name"], best_row["current_name"])

        mismatch_scores.append(
            {
                "foray_id": fid,
                "org_score": org_score,
                "conf_score": conf_score,
                "foray_score": foray_score,
                "mycobank_id": mb_id,         # chosen candidate
                "mycobank_name": mb_name,     # preferred (current or taxon)
                "mycobank_expl": best_expl,   # ORG/CONF/FORAY → TAXON/UPDATED
            }
        )

    # Iterate rows with a single shared executor (lower overhead)
    total = len(foray_df)
    workers = _choose_workers()
    print(f"🧵 Starting matching pipeline with {workers} workers for {total:,} Foray records...")
    
    import time
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for i, row in enumerate(foray_df.itertuples(index=False), start=1):
            fid = _norm(row.id)
            a = _norm(row.genus_and_species_org_entry)
            b = _norm(row.genus_and_species_conf)
            c = _norm(row.genus_and_species_foray_name)
            row_work(ex, fid, a, b, c)
            
            # Enhanced progress reporting
            if i % 100 == 0 or i == total:
                elapsed = time.time() - start_time
                rate = i / elapsed if elapsed > 0 else 0
                remaining = (total - i) / rate if rate > 0 else 0
                
                perfect_count = len(perfect_list)
                mismatch_count = len(mismatch_list)
                
                print(f"📊 Progress: {i:,}/{total:,} ({i/total*100:.1f}%) | "
                      f"Perfect: {perfect_count} | Mismatches: {mismatch_count} | "
                      f"Rate: {rate:.1f}/sec | ETA: {remaining:.0f}s")

    elapsed_total = time.time() - start_time
    print(f"✅ Matching pipeline completed in {elapsed_total:.1f} seconds!")
    print(f"📈 Final Results: {len(perfect_list)} perfect matches, {len(mismatch_list)} mismatches")
    return perfect_list, mismatch_list, perfect_myco, mismatch_scores


def _save_originals(foray_df: pd.DataFrame, myco_df: pd.DataFrame):
    """Persist source rows once so your detail view can fetch originals from DB."""
    # Foray originals
    for _, r in foray_df.iterrows():
        ForayFungi2023.objects.update_or_create(
            foray_id=_norm(r["id"]),
            defaults={
                "genus_and_species_org_entry": _norm(r["genus_and_species_org_entry"]),
                "genus_and_species_conf": _norm(r["genus_and_species_conf"]),
                "genus_and_species_foray_name": _norm(r["genus_and_species_foray_name"]),
            },
        )
    # Myco originals
    for _, r in myco_df.iterrows():
        MycoBankList.objects.update_or_create(
            mycobank_id=_norm(r["mycobank_id_raw"]),
            defaults={
                "taxon_name": _norm(r["taxon_name"]),
                "current_name": _norm(r["current_name"]),
                "authors": _norm(r["authors"]),
                "year": _norm(r["year"]),
                "hyperlink": _norm(r["hyperlink"]),
            },
        )
