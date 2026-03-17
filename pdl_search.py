# ─────────────────────────────────────────────────────────────
# pdl_search.py
# Standalone module — prod-api-testing branch
# Place this file in the same directory as streamlit_app.py
# ─────────────────────────────────────────────────────────────

import requests
import pandas as pd

REQUIRED_COLUMNS = [
    "Name", "Job Title", "Skills", "Certifications", "Location",
    "Background_Summary", "Years of Experience", "Email", "Phone",
    "Company", "Last_Active", "Contact_Status", "Education Level",
]

PDL_ENDPOINT = "https://api.peopledatalabs.com/v5/person/search"


# ─────────────────────────────────────────────────────────────
# QUERY BUILDER
# ─────────────────────────────────────────────────────────────

def build_pdl_query(extracted: dict) -> dict:
    job_title = extracted.get("job_title", "")
    location  = extracted.get("location", "")
    skills    = extracted.get("required_skills", []) or []
    certs     = extracted.get("required_certifications", []) or []
    all_keywords = list(set([s.lower().strip() for s in skills + certs if s]))

    must_clauses = []

    if job_title:
        must_clauses.append({
            "match": {
                "job_title": {
                    "query": job_title,
                    "operator": "or",
                    "fuzziness": "AUTO"
                }
            }
        })

    if location:
        city = location.split(",")[0].strip()
        must_clauses.append({
            "bool": {
                "should": [
                    {"match": {"location_locality": city}},
                    {"match": {"location_region": location}},
                ]
            }
        })

    should_clauses = [{"match": {"skills": kw}} for kw in all_keywords]

    return {
        "bool": {
            "must": must_clauses,
            "should": should_clauses,
        }
    }


# ─────────────────────────────────────────────────────────────
# PDL API CALL
# ─────────────────────────────────────────────────────────────

def fetch_pdl_candidates(extracted: dict, api_key: str, size: int = 10) -> list:
    query   = build_pdl_query(extracted)
    headers = {"Content-Type": "application/json", "X-Api-Key": api_key}
    payload = {
        "query": query,
        "size": min(size, 10),
        "pretty": False,
        "dataset": "resume,contact,location",
    }

    try:
        response = requests.post(PDL_ENDPOINT, headers=headers, json=payload, timeout=15)
        response.raise_for_status()
        data     = response.json()
        profiles = data.get("data", [])
        print(f"[PDL] Returned {len(profiles)} profiles | Total available: {data.get('total', 'unknown')}")
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
# FIELD HELPERS
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
# MAPPER
# ─────────────────────────────────────────────────────────────

def map_pdl_to_dataframe(profiles: list) -> pd.DataFrame:
    if not profiles:
        return pd.DataFrame(columns=REQUIRED_COLUMNS)

    rows = []
    for p in profiles:
        first = p.get("first_name", "") or ""
        last  = p.get("last_name", "")  or ""
        name  = f"{first} {last}".strip() or "Unknown"

        job_title_obj = p.get("job_title", "") or ""
        job_title     = job_title_obj.get("name", "N/A") if isinstance(job_title_obj, dict) else str(job_title_obj) or "N/A"

        company_obj = p.get("job_company_name", "") or ""
        company     = str(company_obj) if company_obj else "N/A"

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
# PUBLIC ENTRY POINT
# ─────────────────────────────────────────────────────────────

def get_candidates_from_pdl(extracted: dict, api_key: str) -> pd.DataFrame:
    """
    Single function called by streamlit_app.py.
    Replaces pd.read_csv("candidates.csv") in Step 2.
    """
    profiles = fetch_pdl_candidates(extracted, api_key)
    return map_pdl_to_dataframe(profiles)


# ─────────────────────────────────────────────────────────────
# CORESIGNAL STUB — wire in when licensed
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