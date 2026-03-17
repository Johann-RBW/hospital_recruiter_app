# ─────────────────────────────────────────────────────────────
# pdl_search.py
# prod-api-testing branch
# Uses PDL's SQL endpoint — compatible with free tier.
# Place in the same directory as streamlit_app.py
# ─────────────────────────────────────────────────────────────

import requests
import pandas as pd

REQUIRED_COLUMNS = [
    "Name", "Job Title", "Skills", "Certifications", "Location",
    "Background_Summary", "Years of Experience", "Email", "Phone",
    "Company", "Last_Active", "Contact_Status", "Education Level",
]

PDL_SQL_ENDPOINT = "https://api.peopledatalabs.com/v5/person/search"


# ─────────────────────────────────────────────────────────────
# 1. SQL QUERY BUILDER  (free-tier compatible)
# ─────────────────────────────────────────────────────────────

def build_pdl_sql(extracted: dict) -> str:
    """
    Builds a PDL SQL string from Groq-extracted fields.
    PDL's SQL dialect supports: SELECT, WHERE, AND, OR, LIKE, LIMIT.
    Free tier supports this fully — Elasticsearch syntax does NOT work on free.

    Strategy: job_title + location as primary filters (broad),
    skills folded in as OR clauses so the LLM judge does the
    real precision work downstream.
    """
    job_title = extracted.get("job_title", "").strip()
    location  = extracted.get("location", "").strip()
    skills    = extracted.get("required_skills", []) or []
    certs     = extracted.get("required_certifications", []) or []

    conditions = []

    # ── Job title filter ──────────────────────────────────────
    if job_title:
        title_clean = job_title.replace("'", "''")
        conditions.append(f"job_title LIKE '%{title_clean}%'")

    # ── Location filter ───────────────────────────────────────
    if location:
        parts     = [p.strip() for p in location.split(",")]
        city      = parts[0].replace("'", "''") if parts else ""
        state     = parts[1].replace("'", "''") if len(parts) > 1 else ""
        loc_parts = []
        if city:
            loc_parts.append(f"location_locality LIKE '%{city}%'")
        if state:
            loc_parts.append(f"location_region LIKE '%{state}%'")
        if loc_parts:
            conditions.append(f"({' OR '.join(loc_parts)})")

    # ── Skills / certs as soft OR filter ─────────────────────
    # Cap at 5 keywords to keep SQL clean on free tier.
    all_keywords = list(set([
        s.strip().replace("'", "''")
        for s in (skills + certs)
        if s and len(s.strip()) > 1
    ]))[:5]

    if all_keywords:
        skill_clauses = [f"skills LIKE '%{kw}%'" for kw in all_keywords]
        conditions.append(f"({' OR '.join(skill_clauses)})")

    # ── Assemble final SQL ────────────────────────────────────
    if not conditions:
        return "SELECT * FROM person WHERE job_title LIKE '%therapist%' LIMIT 10"

    where_clause = " AND ".join(conditions)
    sql = f"SELECT * FROM person WHERE {where_clause} LIMIT 10"

    print(f"[PDL] SQL query: {sql}")
    return sql


def _build_fallback_sql(extracted: dict) -> str:
    """Title + location only — drops skills filter. Last resort before empty state."""
    job_title = extracted.get("job_title", "").strip().replace("'", "''")
    location  = extracted.get("location", "").strip()
    parts     = [p.strip() for p in location.split(",")]
    city      = parts[0].replace("'", "''") if parts else ""
    state     = parts[1].replace("'", "''") if len(parts) > 1 else ""

    conditions = []
    if job_title:
        conditions.append(f"job_title LIKE '%{job_title}%'")
    if city or state:
        loc_parts = []
        if city:
            loc_parts.append(f"location_locality LIKE '%{city}%'")
        if state:
            loc_parts.append(f"location_region LIKE '%{state}%'")
        conditions.append(f"({' OR '.join(loc_parts)})")

    if not conditions:
        return f"SELECT * FROM person WHERE job_title LIKE '%{job_title}%' LIMIT 10"

    return f"SELECT * FROM person WHERE {' AND '.join(conditions)} LIMIT 10"


# ─────────────────────────────────────────────────────────────
# 2. PDL API CALL
# ─────────────────────────────────────────────────────────────

def fetch_pdl_candidates(extracted: dict, api_key: str) -> list:
    """
    Executes the PDL SQL search and returns raw person records.
    Automatically retries with a relaxed title+location query
    if the full query returns zero results.
    """
    headers = {
        "Content-Type": "application/json",
        "X-Api-Key": api_key,
    }

    def _run_query(sql: str) -> list:
        payload  = {"sql": sql, "size": 10, "pretty": False}
        response = requests.post(PDL_SQL_ENDPOINT, headers=headers, json=payload, timeout=15)
        response.raise_for_status()
        data     = response.json()
        profiles = data.get("data", [])
        total    = data.get("total", 0)
        print(f"[PDL] Returned {len(profiles)} profiles | Total available: {total}")
        return profiles

    try:
        profiles = _run_query(build_pdl_sql(extracted))

        if not profiles:
            print("[PDL] Zero results — retrying with title+location only.")
            profiles = _run_query(_build_fallback_sql(extracted))

        return profiles

    except requests.exceptions.HTTPError:
        try:
            err_body = response.json()
            print(f"[PDL] HTTP {response.status_code}: {err_body.get('error', {}).get('message', '')}")
        except Exception:
            pass
        return []
    except requests.exceptions.Timeout:
        print("[PDL] Request timed out after 15s.")
        return []
    except Exception as e:
        print(f"[PDL] Unexpected error: {e}")
        return []


# ─────────────────────────────────────────────────────────────
# 3. FIELD HELPERS
# ─────────────────────────────────────────────────────────────

def _extract_years_experience(profile: dict) -> str:
    experience = profile.get("experience", []) or []
    if not experience:
        return "N/A"
    return str(len(experience)) + "+ roles"


def _extract_skills(profile: dict) -> str:
    raw   = profile.get("skills", []) or []
    names = []
    for s in raw:
        if isinstance(s, dict):
            names.append(s.get("name", ""))
        elif isinstance(s, str):
            names.append(s)
    return ", ".join(filter(None, names))


def _extract_certifications(profile: dict) -> str:
    raw = profile.get("certifications", []) or []
    return ", ".join([c.get("name", "") for c in raw if isinstance(c, dict)])


def _extract_education(profile: dict) -> str:
    edu = profile.get("education", []) or []
    if not edu:
        return "N/A"
    top    = edu[0]
    degree = top.get("degrees", [""])[0] if top.get("degrees") else ""
    school = top.get("school", {}).get("name", "") if isinstance(top.get("school"), dict) else ""
    if degree and school:
        return f"{degree} — {school}"
    return degree or school or "N/A"


def _build_location_string(profile: dict) -> str:
    city    = profile.get("location_locality", "")
    region  = profile.get("location_region", "")
    country = profile.get("location_country", "")
    parts   = [p for p in [city, region, country] if p]
    return ", ".join(parts) if parts else "Unknown"


def _build_background_summary(profile: dict) -> str:
    summary = profile.get("summary", "")
    if summary and len(summary) > 40:
        return summary
    headline   = profile.get("headline", "")
    experience = profile.get("experience", []) or []
    recent_job = ""
    if experience:
        exp       = experience[0]
        title     = exp.get("title", {})
        title_str = title.get("name", "") if isinstance(title, dict) else str(title)
        company   = exp.get("company", {})
        co_str    = company.get("name", "") if isinstance(company, dict) else str(company)
        if title_str and co_str:
            recent_job = f"Most recently served as {title_str} at {co_str}."
    parts = [p for p in [headline, recent_job] if p]
    return " ".join(parts) if parts else "No summary available."


# ─────────────────────────────────────────────────────────────
# 4. COLUMN MAPPER
# ─────────────────────────────────────────────────────────────

def map_pdl_to_dataframe(profiles: list) -> pd.DataFrame:
    if not profiles:
        return pd.DataFrame(columns=REQUIRED_COLUMNS)

    rows = []
    for p in profiles:
        first = p.get("first_name", "") or ""
        last  = p.get("last_name",  "") or ""
        name  = f"{first} {last}".strip() or "Unknown"

        job_title_raw = p.get("job_title", "") or ""
        job_title     = job_title_raw.get("name", "N/A") if isinstance(job_title_raw, dict) else str(job_title_raw) or "N/A"

        company_raw = p.get("job_company_name", "") or ""
        company     = str(company_raw) if company_raw else "N/A"

        email          = p.get("work_email") or (p.get("personal_emails") or [None])[0] or "Not Available"
        phone          = p.get("mobile_phone") or (p.get("phone_numbers") or [None])[0] or "Upgrade to access"
        contact_status = "Verified" if p.get("work_email") else "Pending Verification"
        last_updated   = p.get("last_updated", "")
        last_active    = last_updated[:10] if last_updated else "Unknown"

        rows.append({
            "Name":                name,
            "Job Title":           job_title,
            "Skills":              _extract_skills(p),
            "Certifications":      _extract_certifications(p),
            "Location":            _build_location_string(p),
            "Background_Summary":  _build_background_summary(p),
            "Years of Experience": _extract_years_experience(p),
            "Email":               email,
            "Phone":               phone,
            "Company":             company,
            "Last_Active":         last_active,
            "Contact_Status":      contact_status,
            "Education Level":     _extract_education(p),
        })

    return pd.DataFrame(rows, columns=REQUIRED_COLUMNS)


# ─────────────────────────────────────────────────────────────
# 5. PUBLIC ENTRY POINT
# ─────────────────────────────────────────────────────────────

def get_candidates_from_pdl(extracted: dict, api_key: str) -> pd.DataFrame:
    """
    Called by streamlit_app.py Step 2.
    Replaces pd.read_csv("candidates.csv").
    """
    profiles = fetch_pdl_candidates(extracted, api_key)
    return map_pdl_to_dataframe(profiles)


# ─────────────────────────────────────────────────────────────
# 6. CORESIGNAL STUB — wire in when licensed
# ─────────────────────────────────────────────────────────────

def _is_profile_thin(profile: dict) -> bool:
    skills_count = len(profile.get("skills", []) or [])
    has_summary  = bool(profile.get("summary", ""))
    return not has_summary and skills_count < 3


def enrich_with_coresignal(profile: dict, api_key: str) -> dict:
    """
    STUB — Coresignal enrichment for thin PDL profiles.
    TODO when licensed:
      1. Hit Coresignal /v1/linkedin/member/search with profile linkedin_url
      2. Merge returned fields into the PDL profile dict
      3. Waterfall in get_candidates_from_pdl():
         enriched = [enrich_with_coresignal(p, cs_key) if _is_profile_thin(p) else p for p in profiles]
    """
    return profile  # pass-through until wired


# ── Quick test harness ────────────────────────────────────────
if __name__ == "__main__":
    import os

    MOCK_EXTRACTED = {
        "job_title": "Physical Therapist",
        "location": "Albany, NY",
        "required_skills": ["home health", "patient assessment", "rehabilitation"],
        "required_certifications": ["PT", "NYS license"],
        "years_of_experience": 2,
        "shift_type": None,
    }

    KEY = os.environ.get("PDL_API_KEY", "")
    if not KEY:
        print("Set PDL_API_KEY env var to test.")
    else:
        import json
        df = get_candidates_from_pdl(MOCK_EXTRACTED, KEY)
        print(f"\n✅ DataFrame shape: {df.shape}")
        print(f"Columns: {list(df.columns)}")
        if not df.empty:
            print("\nFirst record:\n")
            print(json.dumps(df.iloc[0].to_dict(), indent=2))
        else:
            print("No profiles returned.")