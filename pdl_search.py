# ─────────────────────────────────────────────────────────────
# pdl_search.py  —  prod-api-testing branch
# PDL free-tier compatible. SQL only, no Elasticsearch syntax.
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
# 1. SQL QUERY BUILDER
# Key design decision: NO skills in the SQL filter.
#
# Why: PDL free tier uses normalized skill tags ("physical therapy",
# "home health") — Groq extracts narrative phrases ("NYS Licensure",
# "Multidisciplinary Approach") that never match PDL's taxonomy.
# Putting skills in SQL guarantees zero results.
#
# Instead: SQL = broad title + location funnel only.
# The Python sift + LLM judge downstream handle all skill precision.
# ─────────────────────────────────────────────────────────────

def _safe(s: str) -> str:
    """Escape single quotes for PDL SQL."""
    return s.replace("'", "''")


def _parse_location(location: str):
    """Returns (city, state) tuple from 'City, ST' string."""
    parts = [p.strip() for p in location.split(",")]
    city  = parts[0] if parts else ""
    state = parts[1] if len(parts) > 1 else ""
    return city, state


def build_sql_city_state(job_title: str, city: str, state: str) -> str:
    """Tightest query: title + city + state."""
    return (
        f"SELECT * FROM person "
        f"WHERE job_title LIKE '%{_safe(job_title)}%' "
        f"AND location_locality LIKE '%{_safe(city)}%' "
        f"AND location_region LIKE '%{_safe(state)}%' "
        f"LIMIT 10"
    )


def build_sql_state_only(job_title: str, state: str) -> str:
    """Wider: title + state only — drops city requirement."""
    return (
        f"SELECT * FROM person "
        f"WHERE job_title LIKE '%{_safe(job_title)}%' "
        f"AND location_region LIKE '%{_safe(state)}%' "
        f"LIMIT 10"
    )


def build_sql_title_only(job_title: str) -> str:
    """Widest: title only — any location. Last resort."""
    return (
        f"SELECT * FROM person "
        f"WHERE job_title LIKE '%{_safe(job_title)}%' "
        f"LIMIT 10"
    )


# ─────────────────────────────────────────────────────────────
# 2. PDL API CALL  —  Geographic expansion ladder
#
# Tier 1: title + city + state   (most precise)
# Tier 2: title + state          (drops city — covers whole state)
# Tier 3: title only             (national — any location)
#
# Each tier only fires if the previous returned zero data rows.
# Prints which tier succeeded so you can see it in the terminal.
# ─────────────────────────────────────────────────────────────

def fetch_pdl_candidates(extracted: dict, api_key: str) -> list:
    job_title = extracted.get("job_title", "").strip()
    location  = extracted.get("location", "").strip()
    city, state = _parse_location(location)

    headers = {
        "Content-Type": "application/json",
        "X-Api-Key": api_key,
    }

    def _run(sql: str, label: str) -> list:
        print(f"[PDL] {label}: {sql}")
        payload  = {"sql": sql, "size": 10, "pretty": False}
        resp     = requests.post(PDL_SQL_ENDPOINT, headers=headers, json=payload, timeout=15)
        resp.raise_for_status()
        data     = resp.json()
        profiles = data.get("data", [])
        total    = data.get("total", 0)
        print(f"[PDL] {label} → {len(profiles)} profiles returned | {total} total in index")
        return profiles

    try:
        # Tier 1 — city + state
        if city and state:
            profiles = _run(build_sql_city_state(job_title, city, state), "Tier 1 (city+state)")
            if profiles:
                return profiles
            print("[PDL] Tier 1 empty — expanding to state-wide.")

        # Tier 2 — state only
        if state:
            profiles = _run(build_sql_state_only(job_title, state), "Tier 2 (state only)")
            if profiles:
                return profiles
            print("[PDL] Tier 2 empty — expanding to national.")

        # Tier 3 — title only, anywhere
        profiles = _run(build_sql_title_only(job_title), "Tier 3 (title only / national)")
        if profiles:
            return profiles

        print("[PDL] All tiers exhausted — no profiles found.")
        return []

    except requests.exceptions.HTTPError:
        try:
            err = resp.json().get("error", {}).get("message", "")
            print(f"[PDL] HTTP {resp.status_code}: {err}")
        except Exception:
            pass
        return []
    except requests.exceptions.Timeout:
        print("[PDL] Timed out.")
        return []
    except Exception as e:
        print(f"[PDL] Error: {e}")
        return []


# ─────────────────────────────────────────────────────────────
# 3. FIELD HELPERS
# ─────────────────────────────────────────────────────────────

def _extract_years_experience(profile: dict) -> str:
    experience = profile.get("experience", []) or []
    if not experience:
        return "N/A"
    return f"{len(experience)}+ roles"


def _extract_skills(profile: dict) -> str:
    raw = profile.get("skills", []) or []
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
    parts = [
        profile.get("location_locality", ""),
        profile.get("location_region", ""),
        profile.get("location_country", ""),
    ]
    return ", ".join(p for p in parts if p) or "Unknown"


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
    """Called by streamlit_app.py. Replaces pd.read_csv('candidates.csv')."""
    profiles = fetch_pdl_candidates(extracted, api_key)
    return map_pdl_to_dataframe(profiles)


# ─────────────────────────────────────────────────────────────
# 6. CORESIGNAL STUB
# ─────────────────────────────────────────────────────────────

def _is_profile_thin(profile: dict) -> bool:
    return not profile.get("summary") and len(profile.get("skills", []) or []) < 3


def enrich_with_coresignal(profile: dict, api_key: str) -> dict:
    """
    STUB — wire in when licensed.
    Waterfall becomes:
      enriched = [enrich_with_coresignal(p, cs_key) if _is_profile_thin(p) else p for p in profiles]
    """
    return profile


# ─────────────────────────────────────────────────────────────
# 7. TEST HARNESS  —  python pdl_search.py
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import os, json

    MOCK = {
        "job_title": "Physical Therapist",
        "location": "Albany, NY",
        "required_skills": ["home health", "patient assessment", "rehabilitation"],
        "required_certifications": ["PT", "NYS license"],
    }

    KEY = os.environ.get("PDL_API_KEY", "")
    if not KEY:
        print("Set PDL_API_KEY env var first.")
    else:
        df = get_candidates_from_pdl(MOCK, KEY)
        print(f"\n✅ Shape: {df.shape}")
        if not df.empty:
            print(json.dumps(df.iloc[0].to_dict(), indent=2))
        else:
            print("No profiles returned across all tiers.")