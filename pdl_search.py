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
# No LIMIT in SQL — PDL rejects it. Size passed via payload.
# No skills in SQL — Groq phrases never match PDL's taxonomy.
# All queries pin to USA via location_country to avoid
# international noise on the free tier dataset.
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
    """Tier 3: US-wide. Drops state — keeps country filter."""
    return (
        f"SELECT * FROM person "
        f"WHERE job_title LIKE '%{_safe(job_title)}%' "
        f"AND location_country = 'united states'"
    )


def build_sql_title_only(job_title: str) -> str:
    """Tier 4: Global title match. Absolute last resort."""
    return (
        f"SELECT * FROM person "
        f"WHERE job_title LIKE '%{_safe(job_title)}%'"
    )


# ─────────────────────────────────────────────────────────────
# 2. SINGLE API CALL HELPER
# PDL returns HTTP 404 for "no records" — treat as empty, not error.
# ─────────────────────────────────────────────────────────────

def _run_query(sql: str, label: str, api_key: str, verbose: bool = False) -> list:
    print(f"[PDL] {label}: {sql}")
    headers = {"Content-Type": "application/json", "X-Api-Key": api_key}
    payload = {"sql": sql, "size": 10, "pretty": False}
    resp    = requests.post(PDL_SQL_ENDPOINT, headers=headers, json=payload, timeout=15)

    if verbose:
        print(f"[PDL] HTTP status: {resp.status_code}")
        print(f"[PDL] Raw response: {resp.text[:500]}")

    # 404 = valid "no results" response on PDL — not a real HTTP error
    if resp.status_code == 404:
        print(f"[PDL] {label} → 0 profiles | 0 total")
        return []

    resp.raise_for_status()
    data     = resp.json()
    profiles = data.get("data", [])
    total    = data.get("total", 0)
    print(f"[PDL] {label} → {len(profiles)} profiles returned | {total} total in index")
    return profiles


# ─────────────────────────────────────────────────────────────
# 3. GEOGRAPHIC EXPANSION LADDER
# Tier 1: title + city + state + US
# Tier 2: title + state + US
# Tier 3: title + US only (national)
# Tier 4: title only, global (absolute last resort)
# ─────────────────────────────────────────────────────────────

def fetch_pdl_candidates(extracted: dict, api_key: str, verbose: bool = False) -> list:
    job_title   = extracted.get("job_title", "").strip()
    location    = extracted.get("location", "").strip()
    city, state = _parse_location(location)

    try:
        # Tier 1 — city + state + US
        if city and state:
            profiles = _run_query(
                build_sql_city_state(job_title, city, state),
                "Tier 1 (city+state+US)", api_key, verbose
            )
            if profiles:
                return profiles
            print("[PDL] Tier 1 empty — expanding to state-wide.")

        # Tier 2 — state + US
        if state:
            profiles = _run_query(
                build_sql_state_only(job_title, state),
                "Tier 2 (state+US)", api_key, verbose
            )
            if profiles:
                return profiles
            print("[PDL] Tier 2 empty — expanding to US-wide.")

        # Tier 3 — US national
        profiles = _run_query(
            build_sql_us_only(job_title),
            "Tier 3 (US national)", api_key, verbose
        )
        if profiles:
            return profiles
        print("[PDL] Tier 3 empty — expanding to global.")

        # Tier 4 — global, title only
        profiles = _run_query(
            build_sql_title_only(job_title),
            "Tier 4 (global)", api_key, verbose
        )
        if profiles:
            return profiles

        print("[PDL] All tiers exhausted — no profiles found.")
        return []

    except requests.exceptions.HTTPError as e:
        try:
            err = resp.json().get("error", {}).get("message", "")
            print(f"[PDL] HTTP error: {err}")
        except Exception:
            print(f"[PDL] HTTP error: {e}")
        return []
    except requests.exceptions.Timeout:
        print("[PDL] Timed out.")
        return []
    except Exception as e:
        print(f"[PDL] Unexpected error: {type(e).__name__}: {e}")
        return []


# ─────────────────────────────────────────────────────────────
# 4. FIELD HELPERS
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
# 5. COLUMN MAPPER
#
# IMPORTANT — PDL free tier contact field behavior:
# Fields like "work_email", "mobile_phone", "personal_emails"
# are returned as BOOLEANS (true/false) on free tier, not strings.
# true  = "this person has this data, upgrade to see it"
# false = "we don't have this data at all"
#
# We map these to human-readable UI strings accordingly.
# ─────────────────────────────────────────────────────────────

def _resolve_contact_field(value, field_label: str) -> str:
    """
    Handles PDL's free-tier boolean contact fields.
    - If it's already a real string (paid tier): return it
    - If True (bool): data exists but is gated
    - If False / None: data not available
    """
    if isinstance(value, str) and len(value) > 3:
        return value                          # Paid tier — real value
    if value is True:
        return f"Available on licensed plan"  # Free tier — exists but gated
    return "Not Available"


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

        # ── Contact fields ─────────────────────────────────────
        # Free tier: these come back as True/False booleans
        # Paid tier: these come back as actual strings
        raw_email   = p.get("work_email") or (p.get("personal_emails") or [None])[0]
        raw_phone   = p.get("mobile_phone") or (p.get("phone_numbers") or [None])[0]

        # Check the top-level boolean flags PDL provides
        has_email   = p.get("work_email") or p.get("recommended_personal_email") or p.get("personal_emails")
        has_phone   = p.get("mobile_phone") or p.get("phone_numbers")

        email = _resolve_contact_field(raw_email, "email")
        if email == "Not Available" and has_email:
            email = "Available on licensed plan"

        phone = _resolve_contact_field(raw_phone, "phone")
        if phone == "Not Available" and has_phone:
            phone = "Available on licensed plan"

        # Contact status: "Verified" if PDL confirmed they have contact data
        contact_status = "Verified" if (has_email or has_phone) else "Pending Verification"

        last_updated = p.get("last_updated", "") or p.get("job_last_verified", "")
        last_active  = last_updated[:10] if last_updated else "Unknown"

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
# 6. PUBLIC ENTRY POINT
# ─────────────────────────────────────────────────────────────

def get_candidates_from_pdl(extracted: dict, api_key: str) -> pd.DataFrame:
    """Called by streamlit_app.py. Replaces pd.read_csv('candidates.csv')."""
    profiles = fetch_pdl_candidates(extracted, api_key)
    return map_pdl_to_dataframe(profiles)


# ─────────────────────────────────────────────────────────────
# 7. CORESIGNAL STUB
# ─────────────────────────────────────────────────────────────

def _is_profile_thin(profile: dict) -> bool:
    return not profile.get("summary") and len(profile.get("skills", []) or []) < 3


def enrich_with_coresignal(profile: dict, api_key: str) -> dict:
    """
    STUB — wire in when licensed.
    Waterfall:
      enriched = [enrich_with_coresignal(p, cs_key) if _is_profile_thin(p) else p for p in profiles]
    """
    return profile


# ─────────────────────────────────────────────────────────────
# 8. TEST HARNESS  —  python pdl_search.py
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
        print(f"\nFirst profile name:     {profiles[0].get('full_name')}")
        print(f"Job title:              {profiles[0].get('job_title')}")
        print(f"Location country:       {profiles[0].get('location_country')}")
        print(f"Location region:        {profiles[0].get('location_region')}")
        print(f"Location locality:      {profiles[0].get('location_locality')}")
        print(f"work_email field:       {profiles[0].get('work_email')}")
        print(f"mobile_phone field:     {profiles[0].get('mobile_phone')}")
        print(f"personal_emails field:  {profiles[0].get('personal_emails')}")
        print(f"\nMapped DataFrame row:")
        df = map_pdl_to_dataframe(profiles)
        print(json.dumps(df.iloc[0].to_dict(), indent=2))
    else:
        print("No profiles returned across all tiers.")