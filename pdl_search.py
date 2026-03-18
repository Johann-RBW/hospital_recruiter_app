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
# 1. SQL BUILDERS
# ─────────────────────────────────────────────────────────────

def _safe(s: str) -> str:
    return s.replace("'", "''")


def _parse_location(location: str):
    parts = [p.strip() for p in location.split(",")]
    city  = parts[0] if parts else ""
    state = parts[1] if len(parts) > 1 else ""
    return city, state


def build_sql_city_state(job_title: str, city: str, state: str) -> str:
    return (
        f"SELECT * FROM person "
        f"WHERE job_title LIKE '%{_safe(job_title)}%' "
        f"AND location_locality LIKE '%{_safe(city)}%' "
        f"AND location_region LIKE '%{_safe(state)}%' "
        f"AND location_country = 'united states'"
    )


def build_sql_state_only(job_title: str, state: str) -> str:
    return (
        f"SELECT * FROM person "
        f"WHERE job_title LIKE '%{_safe(job_title)}%' "
        f"AND location_region LIKE '%{_safe(state)}%' "
        f"AND location_country = 'united states'"
    )


def build_sql_us_only(job_title: str) -> str:
    return (
        f"SELECT * FROM person "
        f"WHERE job_title LIKE '%{_safe(job_title)}%' "
        f"AND location_country = 'united states'"
    )


def build_sql_title_only(job_title: str) -> str:
    return (
        f"SELECT * FROM person "
        f"WHERE job_title LIKE '%{_safe(job_title)}%'"
    )


# ─────────────────────────────────────────────────────────────
# 2. API CALL + TIER LADDER
# ─────────────────────────────────────────────────────────────

def _run_query(sql: str, label: str, api_key: str, verbose: bool = False) -> list:
    print(f"[PDL] {label}: {sql}")
    headers = {"Content-Type": "application/json", "X-Api-Key": api_key}
    payload = {"sql": sql, "size": 10, "pretty": False}
    resp    = requests.post(PDL_SQL_ENDPOINT, headers=headers, json=payload, timeout=15)

    if verbose:
        print(f"[PDL] HTTP status: {resp.status_code}")
        print(f"[PDL] Raw response: {resp.text[:500]}")

    if resp.status_code == 404:
        print(f"[PDL] {label} → 0 profiles | 0 total")
        return []

    resp.raise_for_status()
    data     = resp.json()
    profiles = data.get("data", [])
    total    = data.get("total", 0)
    print(f"[PDL] {label} → {len(profiles)} profiles returned | {total} total in index")
    return profiles


def fetch_pdl_candidates(extracted: dict, api_key: str, verbose: bool = False) -> list:
    job_title   = extracted.get("job_title", "").strip()
    location    = extracted.get("location", "").strip()
    city, state = _parse_location(location)

    try:
        if city and state:
            profiles = _run_query(build_sql_city_state(job_title, city, state), "Tier 1 (city+state+US)", api_key, verbose)
            if profiles:
                return profiles
            print("[PDL] Tier 1 empty — expanding to state-wide.")

        if state:
            profiles = _run_query(build_sql_state_only(job_title, state), "Tier 2 (state+US)", api_key, verbose)
            if profiles:
                return profiles
            print("[PDL] Tier 2 empty — expanding to US-wide.")

        profiles = _run_query(build_sql_us_only(job_title), "Tier 3 (US national)", api_key, verbose)
        if profiles:
            return profiles
        print("[PDL] Tier 3 empty — expanding to global.")

        profiles = _run_query(build_sql_title_only(job_title), "Tier 4 (global)", api_key, verbose)
        if profiles:
            return profiles

        print("[PDL] All tiers exhausted — no profiles found.")
        return []

    except requests.exceptions.HTTPError as e:
        print(f"[PDL] HTTP error: {e}")
        return []
    except requests.exceptions.Timeout:
        print("[PDL] Timed out.")
        return []
    except Exception as e:
        print(f"[PDL] Unexpected error: {type(e).__name__}: {e}")
        return []


# ─────────────────────────────────────────────────────────────
# 3. FIELD HELPERS
#
# PDL free tier returns many fields as booleans instead of real
# values — true = "data exists, upgrade to see it".
# Every helper below is defensively typed: if a field isn't the
# expected type, we return a safe placeholder rather than crash.
# ─────────────────────────────────────────────────────────────

def _safe_str(value, fallback: str = "N/A") -> str:
    """Return value as string only if it's actually a string. Otherwise fallback."""
    if isinstance(value, str) and value.strip():
        return value.strip()
    return fallback


def _safe_list(value) -> list:
    """Return value only if it's actually a list. Otherwise empty list."""
    if isinstance(value, list):
        return value
    return []


def _extract_years_experience(profile: dict) -> str:
    experience = _safe_list(profile.get("experience"))
    if not experience:
        return "N/A"
    return f"{len(experience)}+ roles"


def _extract_skills(profile: dict) -> str:
    raw   = _safe_list(profile.get("skills"))
    names = []
    for s in raw:
        if isinstance(s, dict):
            name = s.get("name", "")
            if isinstance(name, str) and name:
                names.append(name)
        elif isinstance(s, str) and s:
            names.append(s)
    return ", ".join(names)


def _extract_certifications(profile: dict) -> str:
    raw   = _safe_list(profile.get("certifications"))
    names = []
    for c in raw:
        if isinstance(c, dict):
            name = c.get("name", "")
            if isinstance(name, str) and name:
                names.append(name)
        elif isinstance(c, str) and c:
            names.append(c)
    return ", ".join(names)


def _extract_education(profile: dict) -> str:
    edu = _safe_list(profile.get("education"))
    if not edu:
        return "N/A"
    top = edu[0]
    if not isinstance(top, dict):
        return "N/A"

    degrees_raw = top.get("degrees")
    degree      = ""
    if isinstance(degrees_raw, list) and degrees_raw:
        degree = degrees_raw[0] if isinstance(degrees_raw[0], str) else ""

    school_raw = top.get("school")
    school     = ""
    if isinstance(school_raw, dict):
        school = _safe_str(school_raw.get("name"), "")

    if degree and school:
        return f"{degree} — {school}"
    return degree or school or "N/A"


def _build_location_string(profile: dict) -> str:
    parts = [
        _safe_str(profile.get("location_locality"), ""),
        _safe_str(profile.get("location_region"), ""),
        _safe_str(profile.get("location_country"), ""),
    ]
    return ", ".join(p for p in parts if p) or "Unknown"


def _build_background_summary(profile: dict) -> str:
    summary = profile.get("summary", "")
    if isinstance(summary, str) and len(summary) > 40:
        return summary

    headline   = _safe_str(profile.get("headline"), "")
    experience = _safe_list(profile.get("experience"))
    recent_job = ""

    if experience and isinstance(experience[0], dict):
        exp       = experience[0]
        title     = exp.get("title", {})
        title_str = _safe_str(title.get("name") if isinstance(title, dict) else None, "")
        company   = exp.get("company", {})
        co_str    = _safe_str(company.get("name") if isinstance(company, dict) else None, "")
        if title_str and co_str:
            recent_job = f"Most recently served as {title_str} at {co_str}."

    parts = [p for p in [headline, recent_job] if p]
    return " ".join(parts) if parts else "No summary available."


def _resolve_contact(profile: dict, field: str, list_field: str = None) -> str:
    """
    PDL free tier: contact fields are booleans (True = exists but gated).
    PDL paid tier: contact fields are real strings/lists.
    This handles both cleanly.
    """
    # Try direct field first
    val = profile.get(field)
    if isinstance(val, str) and len(val) > 3:
        return val  # Paid tier — real value

    # Try list field (e.g. personal_emails, phone_numbers)
    if list_field:
        lst = profile.get(list_field)
        if isinstance(lst, list) and lst and isinstance(lst[0], str):
            return lst[0]  # Paid tier — real value in list

    # Boolean flags: True means data exists but is paywalled
    bool_flag = profile.get(field) or (profile.get(list_field) if list_field else None)
    if bool_flag is True:
        return "Available on licensed plan"

    return "Not Available"


# ─────────────────────────────────────────────────────────────
# 4. COLUMN MAPPER
# ─────────────────────────────────────────────────────────────

def map_pdl_to_dataframe(profiles: list) -> pd.DataFrame:
    if not profiles:
        return pd.DataFrame(columns=REQUIRED_COLUMNS)

    rows = []
    for p in profiles:
        if not isinstance(p, dict):
            continue

        first = _safe_str(p.get("first_name"), "")
        last  = _safe_str(p.get("last_name"),  "")
        name  = f"{first} {last}".strip() or "Unknown"

        job_title_raw = p.get("job_title", "")
        if isinstance(job_title_raw, dict):
            job_title = _safe_str(job_title_raw.get("name"), "N/A")
        else:
            job_title = _safe_str(job_title_raw, "N/A")

        company = _safe_str(p.get("job_company_name"), "N/A")

        email = _resolve_contact(p, "work_email", "personal_emails")
        # work_email on free tier is a bool — also check recommended_personal_email
        if email == "Not Available":
            rec = p.get("recommended_personal_email")
            if rec is True:
                email = "Available on licensed plan"

        phone          = _resolve_contact(p, "mobile_phone", "phone_numbers")
        has_contact    = email != "Not Available" or phone != "Not Available"
        contact_status = "Verified" if has_contact else "Pending Verification"

        last_updated = p.get("last_updated") or p.get("job_last_verified") or ""
        last_active  = last_updated[:10] if isinstance(last_updated, str) and last_updated else "Unknown"

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
    return not profile.get("summary") and len(_safe_list(profile.get("skills"))) < 3


def enrich_with_coresignal(profile: dict, api_key: str) -> dict:
    """
    STUB — wire in when licensed.
    Waterfall:
      enriched = [enrich_with_coresignal(p, cs_key) if _is_profile_thin(p) else p for p in profiles]
    """
    return profile


# ─────────────────────────────────────────────────────────────
# 7. TEST HARNESS  —  python pdl_search.py
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import os, json

    KEY = os.environ.get("PDL_API_KEY", "")
    if not KEY:
        print("❌ PDL_API_KEY not found in environment.")
        print("   Run:  export PDL_API_KEY='your-key-here'  then retry.")
        exit(1)

    print(f"✅ Key loaded: {KEY[:6]}{'*' * (len(KEY) - 6)}\n")

    MOCK = {
        "job_title": "Physical Therapist",
        "location": "Albany, NY",
        "required_skills": ["home health", "patient assessment", "rehabilitation"],
        "required_certifications": ["PT", "NYS license"],
    }

    profiles = fetch_pdl_candidates(MOCK, KEY, verbose=True)

    print(f"\n--- RESULT ---")
    print(f"Total profiles returned: {len(profiles)}")

    if profiles:
        df = map_pdl_to_dataframe(profiles)
        print(f"\nDataFrame shape: {df.shape}")
        print(f"\nFirst mapped row:")
        print(json.dumps(df.iloc[0].to_dict(), indent=2))
        print(f"\nAll names in result:")
        for i, row in df.iterrows():
            print(f"  {i+1}. {row['Name']} | {row['Job Title']} | {row['Location']}")
    else:
        print("No profiles returned across all tiers.")