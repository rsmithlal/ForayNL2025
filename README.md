# ForayNL2025 — Django App

A small Django app for **Foray name matching** with **MycoBank** context.

- Browse **perfect/partial** Foray matches
- **Review** mismatches and record validated names
- See **MycoBank** exact hits and **similarity scores**

> This branch excludes large SQLite files. See `.gitignore`.

---

## Table of Contents

- [Project Structure](#project-structure)
- [Features](#features)
- [How Matching Works (Why)](#how-matching-works-why)
- [Prerequisites](#prerequisites)
- [Quickstart](#quickstart)
- [Run the Pipeline (optional)](#run-the-pipeline-optional)
- [Key Pages](#key-pages)
- [Data Models](#data-models)
- [Management Commands](#management-commands)

---

## Project Structure

```
FORAY_DJANGO/
  manage.py
  config/
    __init__.py
    settings.py
    urls.py
    wsgi.py
    asgi.py
  core/
    __init__.py
    admin.py
    apps.py
    forms.py
    models.py
    urls.py
    views.py
    logic/
      full_match_pipeline.py        # main matching pipeline
    management/
      commands/
        load_full_pipeline.py       # CLI to run the pipeline + populate tables
    templates/
      core/
        dashboard.html
        match_browser.html
        review_form.html
        review_done.html
        view_reviewed.html
        detail.html
        myco_perfect.html
        myco_mismatch.html
    static/                         # (can be empty)
    data/
requirements.txt
README.md
.gitignore
```

---

## Features

- **Match Browser**: filter by match category, search, **export CSV**.
- **Review Flow**: step through mismatches, save validated name, or **Skip** (mark **Pending**) and continue.
- **Reviewed List**: view all reviewed items; **Reopen** to send back into review.
- **MycoBank Views**:
  - **Perfect + MycoBank**: 3-column Foray perfect matches with exact Myco hit.
  - **Mismatch → Myco scores**: show RapidFuzz scores for ORG/CONF/FORAY vs Myco, plus one **chosen MycoBank candidate**.
- **Detail Page**: combines best available result + original Foray/MycoBank rows (when stored).

---

## How Matching Works (Why)

- MycoBank records can have both **Taxon name** and **Current name**.
- We **prefer Current name** when present; else fall back to Taxon name.
- For **perfect Foray triples** (ORG == CONF == FORAY):
  - If there’s an **exact** (score 100) Myco match by current/taxon name, store it as **ForayPerfectMycoMatch**.
- For **mismatches**:
  - Compute **RapidFuzz** similarity for each of the three Foray names (ORG/CONF/FORAY) against Myco candidates grouped by first letter.
  - Pick the **best overall** candidate; store its **MycoBank ID/Name** and an explanation like `ORG → UPDATED` (meaning ORG matched Myco **Current name**) or `CONF → TAXON`, etc.

This makes the pipeline fast and the UI always shows the **most informative** Myco name.

---

## Prerequisites

- **Python** 3.11+ (3.12 OK)
- **pip**
- (Windows) **PowerShell** recommended

Python packages (see `requirements.txt`):
- `Django==5.2.4`
- `pandas>=2.2`
- `rapidfuzz>=3.9`
- `django-widget-tweaks>=1.5`

---

## Quickstart

> Run commands **inside** `FORAY_DJANGO/` so relative paths (like `data/…`) work.

### 1) Clone and switch to the code branch
```bash
git clone https://github.com/PeikeCong/ForayNL2025.git
cd ForayNL2025
git switch FORAY_DJANGO
cd FORAY_DJANGO
```

### 2) Create & activate a virtual environment

**Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip setuptools wheel
```

**macOS/Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip setuptools wheel
```

### 3) Install dependencies
```bash
# from FORAY_DJANGO
pip install -r ../requirements.txt
```

### 4) Initialize the database
```bash
python manage.py makemigrations
python manage.py migrate
```

### 5) Run the dev server
```bash
python manage.py runserver
```
Open: <http://127.0.0.1:8000/>

---

## Run the Pipeline (optional)

Place data under **`FORAY_DJANGO/data/`** (kept **out of git**):

- `2023ForayNL_Fungi.csv`
- `MBList.csv`

Then:
```bash
python manage.py load_full_pipeline
```

This will:

- Fill:
  - `ForayPerfectMatch`
  - `ForayMismatchExplanation`
  - `ForayPerfectMycoMatch` (when there’s an exact Myco hit)
  - `ForayMismatchMycoScores` (scores + chosen Myco candidate)
- Save original **Foray** rows; save only **needed** MycoBank rows (fast).

---

## Key Pages

- `/` — Dashboard
- `/matches/` — Match Browser (filter/search, CSV export)
- `/review/` — Review flow (Save Only, Save & Next, **Skip → Pending**)
- `/reviewed/` — Reviewed list (with **Reopen** → PENDING)
- `/myco/perfect/` — Perfect Foray + exact MycoBank
- `/myco/mismatch/` — Mismatch with scores + chosen Myco name
- `/detail/<FORAY_ID>/` — Rich detail view

---

## Data Models

- **ForayFungi2023**: Foray originals (id, org/conf/foray text columns)
- **MycoBankList**: Myco originals (subset; only needed rows)
- **ForayMatch**: 3-column Foray comparison categories (ALL_MATCH, …)
- **ForayPerfectMatch**: Foray perfect triples (name)
- **ForayMismatchExplanation**: mismatch record + `explanation`
- **ForayPerfectMycoMatch**: perfect triple + exact Myco hit (id/name)
- **ForayMismatchMycoScores**: three scores + chosen Myco (id/name) and optional `mycobank_expl`
- **ReviewedMatch**: review workflow (`validated_name`, `reviewer_name`, `status ∈ {REVIEWED,PENDING,SKIPPED}`)

---

## Management Commands

- `python manage.py load_full_pipeline`  
  Runs the full pipeline and populates all result tables (clears them first).

You can add more commands under `core/management/commands/`.

---

## Git Hygiene (code-only)

This branch’s `.gitignore` blocks:

- DBs: `FORAY_DJANGO/db.sqlite3`
- Data: `FORAY_DJANGO/data/**`, `*.csv`, `*.tsv`, `*.xlsx`, `*.xls`
- Virtual envs: `.venv/`, `env/`, `venv/`
- Editor caches: `.vscode/`, `.idea/`, `__pycache__/`, etc.

**If you accidentally add large files**:
```bash
# remove from index only (keep files locally)
git rm -r --cached -- FORAY_DJANGO/db.sqlite3 FORAY_DJANGO/data
git rm --cached -- *.csv *.tsv *.xlsx *.xls
git commit -m "chore: remove large files from index"
git push
```

To publish a **clean code-only** branch (no history with big files), create an **orphan** branch and add just the code:
```bash
git switch --orphan FORAY_DJANGO
git rm -r --cached .
git add .gitignore README.md requirements.txt FORAY_DJANGO
git commit -m "chore: code-only initial commit"
git push -u origin FORAY_DJANGO
```

