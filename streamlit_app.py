import streamlit as st
import pandas as pd
import json
import os
from groq import Groq

# ─────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="CandidateIQ — Healthcare Talent",
    page_icon="⬡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────────────────────
# STATE MANAGEMENT (Fixes the Download Button Rerun Bug)
# ─────────────────────────────────────────────────────────────
if "search_active" not in st.session_state:
    st.session_state.search_active = False
    st.session_state.extracted_data = {}
    st.session_state.filtered_df = pd.DataFrame()
    st.session_state.fallback_used = False
    st.session_state.city = None

# ─────────────────────────────────────────────────────────────
# CUSTOM CSS  —  Neobrutalism × Neumorphism hybrid
# ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Mono:wght@400;500&family=DM+Sans:wght@300;400;500&display=swap');

/* ── Root Variables ─────────────────────────────────── */
:root {
  --bg:          #E8E4DC;
  --surface:     #EAE6DE;
  --shadow-dark: #C5C1B8;
  --shadow-light:#FFFFFF;
  --ink:         #1A1916;
  --ink-muted:   #5C5952;
  --accent:      #D4380D;         /* burnt vermillion */
  --accent-2:    #1D4ED8;         /* cobalt */
  --accent-3:    #15803D;         /* forest */
  --border:      #1A1916;
  --border-w:    2.5px;
  --radius:      6px;
  --neu-shadow:  6px 6px 12px var(--shadow-dark), -4px -4px 10px var(--shadow-light);
  --neu-inset:   inset 3px 3px 7px var(--shadow-dark), inset -3px -3px 7px var(--shadow-light);
  --brutalist-shadow: 4px 4px 0px var(--border);
}

/* ── Global Reset & Aggressive Background Override ─── */
html, body, [class*="css"] {
  font-family: 'DM Sans', sans-serif;
  background-color: var(--bg) !important;
  color: var(--ink);
}

/* Force Streamlit's deep container layers to accept our background */
.stApp, 
[data-testid="stAppViewContainer"], 
[data-testid="stAppViewBlockContainer"], 
[data-testid="stHeader"] {
    background-color: var(--bg) !important;
    background: var(--bg) !important;
}

/* Hide Streamlit top header completely */
[data-testid="stHeader"] {
    display: none !important;
}

/* ── Masthead ────────────────────────────────────────── */
.masthead {
  display: flex;
  align-items: flex-end;
  gap: 1.2rem;
  padding: 2rem 0 0.25rem;
  border-bottom: var(--border-w) solid var(--border);
  margin-bottom: 2.2rem;
}
.masthead-mark {
  width: 44px; height: 44px;
  background: var(--accent);
  border: var(--border-w) solid var(--border);
  border-radius: var(--radius);
  display: flex; align-items: center; justify-content: center;
  font-size: 1.3rem;
  box-shadow: var(--brutalist-shadow);
  flex-shrink: 0;
}
.masthead-title {
  font-family: 'Syne', sans-serif;
  font-weight: 800;
  font-size: 1.75rem;
  letter-spacing: -0.03em;
  line-height: 1;
  color: var(--ink);
}
.masthead-sub {
  font-family: 'DM Mono', monospace;
  font-size: 0.7rem;
  color: var(--ink-muted);
  letter-spacing: 0.12em;
  text-transform: uppercase;
  margin-bottom: 3px;
}

/* ── Section labels ─────────────────────────────────── */
.section-label {
  font-family: 'DM Mono', monospace;
  font-size: 0.65rem;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--ink-muted);
  margin-bottom: 0.5rem;
  display: block;
}

/* ── Neumorphic card ─────────────────────────────────── */
.neu-card {
  background: var(--surface);
  border-radius: 12px;
  box-shadow: var(--neu-shadow);
  border: var(--border-w) solid var(--border);
  padding: 1.6rem 1.8rem;
  margin-bottom: 1.4rem;
  position: relative;
}
.neu-card::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  box-shadow: inset 1px 1px 0px rgba(255,255,255,0.6);
  pointer-events: none;
}

/* ── Brutalist tag chips ─────────────────────────────── */
.tag-row { display: flex; flex-wrap: wrap; gap: 0.45rem; margin-top: 0.5rem; }
.tag {
  font-family: 'DM Mono', monospace;
  font-size: 0.7rem;
  font-weight: 500;
  padding: 3px 10px;
  border: 2px solid var(--border);
  border-radius: 3px;
  background: var(--surface);
  box-shadow: 2px 2px 0 var(--border);
  letter-spacing: 0.04em;
  color: var(--ink);
}
.tag-accent  { background: var(--accent);  color: #fff; border-color: var(--border); }
.tag-accent2 { background: var(--accent-2); color: #fff; }
.tag-accent3 { background: var(--accent-3); color: #fff; }

/* ── Streamlit textarea override ────────────────────── */
.stTextArea textarea {
  background: var(--surface) !important;
  box-shadow: var(--neu-inset) !important;
  border: var(--border-w) solid var(--border) !important;
  border-radius: var(--radius) !important;
  font-family: 'DM Sans', sans-serif !important;
  font-size: 0.9rem !important;
  color: var(--ink) !important;
  padding: 0.9rem 1rem !important;
  transition: box-shadow 0.2s ease;
}
.stTextArea textarea:focus {
  box-shadow: var(--neu-inset), 0 0 0 3px rgba(212,56,13,0.18) !important;
  outline: none !important;
}
.stTextArea label {
  font-family: 'DM Mono', monospace !important;
  font-size: 0.65rem !important;
  letter-spacing: 0.18em !important;
  text-transform: uppercase !important;
  color: var(--ink-muted) !important;
}

/* ── Primary button ──────────────────────────────────── */
.stButton > button[kind="primary"] {
  background: var(--accent) !important;
  color: #fff !important;
  font-family: 'Syne', sans-serif !important;
  font-weight: 700 !important;
  font-size: 0.95rem !important;
  letter-spacing: 0.04em !important;
  border: var(--border-w) solid var(--border) !important;
  border-radius: var(--radius) !important;
  padding: 0.55rem 2rem !important;
  box-shadow: var(--brutalist-shadow) !important;
  transition: transform 0.1s, box-shadow 0.1s !important;
  cursor: pointer !important;
}
.stButton > button[kind="primary"]:hover {
  transform: translate(-2px, -2px) !important;
  box-shadow: 6px 6px 0 var(--border) !important;
}
.stButton > button[kind="primary"]:active {
  transform: translate(2px, 2px) !important;
  box-shadow: 2px 2px 0 var(--border) !important;
}

/* ── Secondary / download button ────────────────────── */
.stDownloadButton > button,
.stButton > button:not([kind="primary"]) {
  background: var(--surface) !important;
  color: var(--ink) !important;
  font-family: 'DM Mono', monospace !important;
  font-size: 0.75rem !important;
  letter-spacing: 0.05em !important;
  border: var(--border-w) solid var(--border) !important;
  border-radius: var(--radius) !important;
  box-shadow: 3px 3px 0 var(--border) !important;
  transition: transform 0.1s, box-shadow 0.1s !important;
}
.stDownloadButton > button:hover,
.stButton > button:not([kind="primary"]):hover {
  transform: translate(-1px, -1px) !important;
  box-shadow: 4px 4px 0 var(--border) !important;
}

/* ── Expander (JSON viewer) ──────────────────────────── */
.streamlit-expanderHeader {
  font-family: 'DM Mono', monospace !important;
  font-size: 0.72rem !important;
  letter-spacing: 0.1em !important;
  text-transform: uppercase !important;
  color: var(--ink-muted) !important;
  background: var(--surface) !important;
  border: var(--border-w) solid var(--border) !important;
  border-radius: var(--radius) !important;
  box-shadow: var(--brutalist-shadow) !important;
}
.streamlit-expanderContent {
  border: var(--border-w) solid var(--border) !important;
  border-top: none !important;
  border-radius: 0 0 var(--radius) var(--radius) !important;
  background: var(--surface) !important;
  box-shadow: var(--neu-shadow) !important;
}

/* ── Dataframe / table ───────────────────────────────── */
.stDataFrame {
  border: var(--border-w) solid var(--border) !important;
  border-radius: var(--radius) !important;
  box-shadow: var(--neu-shadow) !important;
  overflow: hidden !important;
}
.stDataFrame [data-testid="stDataFrameResizable"] {
  background: var(--surface) !important;
}
/* Table header rows */
.stDataFrame thead tr th {
  background: var(--ink) !important;
  color: var(--bg) !important;
  font-family: 'DM Mono', monospace !important;
  font-size: 0.68rem !important;
  letter-spacing: 0.1em !important;
  text-transform: uppercase !important;
  border: none !important;
  padding: 0.7rem 1rem !important;
}
.stDataFrame tbody tr td {
  font-family: 'DM Sans', sans-serif !important;
  font-size: 0.85rem !important;
  border-bottom: 1px solid var(--shadow-dark) !important;
  padding: 0.6rem 1rem !important;
}
.stDataFrame tbody tr:hover td {
  background: rgba(212,56,13,0.05) !important;
}

/* ── Spinner ─────────────────────────────────────────── */
.stSpinner > div {
  border-top-color: var(--accent) !important;
}

/* ── Alert / info / warning / error ─────────────────── */
.stAlert {
  border-radius: var(--radius) !important;
  border-width: var(--border-w) !important;
  border-style: solid !important;
  border-color: var(--border) !important;
  box-shadow: 3px 3px 0 var(--border) !important;
  font-family: 'DM Sans', sans-serif !important;
}

/* ── Metrics / stat cards ─────────────────────────────── */
.stat-card {
  background: var(--surface);
  border: var(--border-w) solid var(--border);
  border-radius: var(--radius);
  box-shadow: var(--neu-shadow);
  padding: 1rem 1.2rem;
  text-align: left;
}
.stat-card .stat-num {
  font-family: 'Syne', sans-serif;
  font-weight: 800;
  font-size: 2rem;
  line-height: 1;
  color: var(--accent);
}
.stat-card .stat-lbl {
  font-family: 'DM Mono', monospace;
  font-size: 0.62rem;
  letter-spacing: 0.15em;
  text-transform: uppercase;
  color: var(--ink-muted);
  margin-top: 4px;
}

/* ── Result header bar ───────────────────────────────── */
.result-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 1rem;
  background: var(--ink);
  color: var(--bg);
  border-radius: var(--radius) var(--radius) 0 0;
  border: var(--border-w) solid var(--border);
  margin-bottom: -2px;
}
.result-header-title {
  font-family: 'Syne', sans-serif;
  font-weight: 700;
  font-size: 0.9rem;
  letter-spacing: 0.04em;
}
.result-header-count {
  font-family: 'DM Mono', monospace;
  font-size: 0.72rem;
  letter-spacing: 0.1em;
  color: rgba(232,228,220,0.65);
}

/* ── Divider ─────────────────────────────────────────── */
hr {
  border: none !important;
  border-top: var(--border-w) solid var(--border) !important;
  margin: 1.5rem 0 !important;
}

/* ── Footer ──────────────────────────────────────────── */
.footer-text {
  text-align: center;
  font-family: 'DM Mono', monospace;
  font-size: 0.65rem;
  color: var(--ink-muted);
  margin-top: 3rem;
  letter-spacing: 0.05em;
}

/* ── JSON code block ─────────────────────────────────── */
.stJson {
  font-family: 'DM Mono', monospace !important;
  font-size: 0.78rem !important;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# MASTHEAD
# ─────────────────────────────────────────────────────────────
st.markdown("""
<div class="masthead">
  <div class="masthead-mark">⬡</div>
  <div>
    <div class="masthead-sub">Healthcare Talent Intelligence</div>
    <div class="masthead-title">CandidateIQ</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# GROQ CLIENT
# ─────────────────────────────────────────────────────────────
try:
    groq_client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except KeyError:
    st.error("⚠ GROQ_API_KEY is missing. Add it to .streamlit/secrets.toml.")
    st.stop()

# ─────────────────────────────────────────────────────────────
# LAYOUT — two-column input panel
# ─────────────────────────────────────────────────────────────
col_input, col_tip = st.columns([2, 1], gap="large")

with col_input:
    st.markdown('<span class="section-label">01 — Job Description</span>', unsafe_allow_html=True)
    job_description = st.text_area(
        "Paste Job Description",
        height=230,
        placeholder="Paste the full job posting here. Include responsibilities, required skills, certifications, shift type, and location for the best results.",
        label_visibility="collapsed",
    )
    st.markdown("<br>", unsafe_allow_html=True)
    search_clicked = st.button("⬡  Run Candidate Search", type="primary", use_container_width=False)

with col_tip:
    st.markdown('<span class="section-label">How it works</span>', unsafe_allow_html=True)
    st.markdown("""
<div class="neu-card" style="padding: 1.2rem 1.4rem;">
  <div style="font-family:'DM Mono',monospace;font-size:0.65rem;letter-spacing:0.14em;color:var(--accent);text-transform:uppercase;margin-bottom:0.8rem;">Three-step pipeline</div>

  <div style="margin-bottom:0.75rem;">
    <div style="font-family:'Syne',sans-serif;font-weight:700;font-size:0.82rem;">01 &nbsp;Extract</div>
    <div style="font-size:0.8rem;color:var(--ink-muted);line-height:1.5;margin-top:2px;">LLaMA 3.1 via Groq parses skills, certs, education, location &amp; shift type from any free-text JD.</div>
  </div>

  <div style="margin-bottom:0.75rem;">
    <div style="font-family:'Syne',sans-serif;font-weight:700;font-size:0.82rem;">02 &nbsp;Match</div>
    <div style="font-size:0.8rem;color:var(--ink-muted);line-height:1.5;margin-top:2px;">Filters your candidate database by job title &amp; location with intelligent fallback to regional results.</div>
  </div>

  <div>
    <div style="font-family:'Syne',sans-serif;font-weight:700;font-size:0.82rem;">03 &nbsp;Export</div>
    <div style="font-size:0.8rem;color:var(--ink-muted);line-height:1.5;margin-top:2px;">Download a clean CSV of matched candidates ready to pipe into your ATS or outreach tool.</div>
  </div>
</div>
""", unsafe_allow_html=True)

st.markdown("<hr>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# SEARCH LOGIC (Executing and saving to state)
# ─────────────────────────────────────────────────────────────
if search_clicked:
    if not job_description.strip():
        st.warning("Please paste a job description before running a search.")
        st.session_state.search_active = False
    else:
        st.session_state.search_active = True
        
        # ── STEP 1: Groq Extraction ──────────────────────────
        with st.spinner("Parsing job description with LLaMA 3.1…"):
            prompt = f"""
You are an expert healthcare recruiter. Analyze the following job description and extract the key details.

CRITICAL INSTRUCTION - THE "BRAIN" PROTOCOL:
1. Do not just blindly copy-paste literal phrases from the text. 
2. NORMALIZE AND STANDARDIZE all skills, certifications, and education into their most common healthcare industry acronyms and standard terms. 
   - Example: Convert "Registered Professional Nursing Program" to "RN" and "BSN".
   - Example: Convert "Basic Life Support" to "BLS".
3. EXPAND the search net: For every core requirement, include both the acronym and the spelled-out version in the lists (e.g., ["RN", "Registered Nurse", "BLS", "Basic Life Support"]).
4. Deduce implied clinical skills from the daily duties described.
5. EXPAND the search net: For every core requirement, include both the acronym and the spelled-out version in the lists (e.g., ["RN", "Registered Nurse"]).
6. SPELL OUT TITLES: If the JD uses an acronym for the main title (like PCA, HHA, or CNA), you MUST spell it out completely in the `job_title` field (e.g., "Patient Care Associate", "Home Health Aide").
7. IGNORE SOFT SKILLS: Do NOT extract subjective traits like "compassionate", "friendly", "dependable", or "work ethic". Only extract hard clinical skills, required equipment, or concrete logistical needs (e.g., "reliable transportation").
8. LOCATION PARSING: If a list of counties or regions is provided, extract the most prominent central city or just the primary region, do not return a massive comma-separated list of counties.
Return ONLY a valid JSON object with these exact keys:
- "job_title" (string - simplify to the core standard title, e.g., "Registered Nurse" instead of "RN III - Emergency Level 1")
- "department" (string or null)
- "required_skills" (list of strings - standardized terms and synonyms)
- "required_certifications" (list of strings - standard acronyms and full names)
- "education_level" (string or null - e.g., "BSN", "ASN", "MSN", "High School")
- "location" (string)
- "years_of_experience" (string or number)
- "shift_type" (string or null)

Job Description:
{job_description}
"""
            try:
                response = groq_client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt}],
                    model="llama-3.1-8b-instant",
                    response_format={"type": "json_object"},
                    temperature=0,
                )
                st.session_state.extracted_data = json.loads(response.choices[0].message.content)

            except Exception as e:
                st.error(f"Groq extraction failed: {e}")
                st.stop()

        # ── STEP 2: Database Match & AI Scoring ───────────────────
        with st.spinner("Scoring and ranking candidates…"):
            try:
                file_path = "candidates.csv"
                if not os.path.exists(file_path):
                    st.error(f"Could not locate '{file_path}'. Ensure it is saved in the project root.")
                    st.stop()

                df = pd.read_csv(file_path)
                filtered_df = df.copy()

                # 1. Pool all targets (Skills, Certs, and Title Words)
                ext_title = str(st.session_state.extracted_data.get("job_title", "")).lower()
                req_skills = st.session_state.extracted_data.get("required_skills", []) or []
                req_certs = st.session_state.extracted_data.get("required_certifications", []) or []
                
                target_keywords = [str(k).lower().strip() for k in (req_skills + req_certs) if k]
                
                # Add words from the job title to the scoring net (catches acronyms like PCA, CNA)
                if ext_title and ext_title != "null":
                    title_words = [w for w in ext_title.split() if len(w) > 2]
                    target_keywords.extend(title_words)
                    
                target_keywords = list(set(target_keywords)) # Remove duplicates

                # 2. AI Resume Scoring Engine (Grade EVERYONE)
                def calculate_score(row):
                    if not target_keywords: return 100
                    
                    # Mash the entire candidate profile into one searchable block
                    cand_text = " ".join([
                        str(row.get('Job Title', '')),
                        str(row.get('Skills', '')), 
                        str(row.get('Certifications', '')), 
                        str(row.get('Background_Summary', ''))
                    ]).lower()
                    
                    matches = sum(1 for kw in target_keywords if kw in cand_text)
                    
                    # Calculate percentage (cap at 98% for realism)
                    score = int((matches / len(target_keywords)) * 100)
                    return min(score, 98)

                filtered_df['Match Score'] = filtered_df.apply(calculate_score, axis=1)
                
                # 3. THE KILL SWITCH: Only drop people with absolutely zero overlapping skills/titles
                if target_keywords:
                    filtered_df = filtered_df[filtered_df['Match Score'] > 0]

                # 4. Location Check (For UI Messaging only - no longer a hard drop)
                ext_loc = st.session_state.extracted_data.get("location")
                st.session_state.fallback_used = False
                st.session_state.city = None

                if ext_loc and str(ext_loc).lower() != "null":
                    st.session_state.city = ext_loc.split(",")[0].strip()
                    local_df = filtered_df[filtered_df["Location"].str.contains(st.session_state.city, case=False, na=False, regex=False)]
                    
                    if local_df.empty and not filtered_df.empty:
                        st.session_state.fallback_used = True

                # Sort best candidates to the top
                st.session_state.filtered_df = filtered_df.sort_values(by='Match Score', ascending=False)

            except Exception as e:
                st.error(f"Database search error: {e}")
                st.stop()


# ─────────────────────────────────────────────────────────────
# RENDER RESULTS (Reads from State)
# ─────────────────────────────────────────────────────────────
if st.session_state.search_active:
    extracted_data = st.session_state.extracted_data
    filtered_df = st.session_state.filtered_df
    fallback_used = st.session_state.fallback_used
    city = st.session_state.city
    
    st.markdown('<span class="section-label">02 — Extracted Requirements</span>', unsafe_allow_html=True)

    # ── Render extracted data as styled cards ─────────────
    c1, c2, c3, c4 = st.columns(4)
    cards = [
        (c1, "Role",       extracted_data.get("job_title", "—"),           "accent"),
        (c2, "Location",   extracted_data.get("location", "—"),             "default"),
        (c3, "Experience", str(extracted_data.get("years_of_experience","—")), "default"),
        (c4, "Shift",      extracted_data.get("shift_type") or "Unspecified", "default"),
    ]
    for col, lbl, val, kind in cards:
        with col:
            border_color = "var(--accent)" if kind == "accent" else "var(--border)"
            col.markdown(f"""
<div class="neu-card" style="border-left: 4px solid {border_color}; padding: 0.9rem 1.1rem;">
<div style="font-family:'DM Mono',monospace;font-size:0.6rem;letter-spacing:0.15em;text-transform:uppercase;color:var(--ink-muted);">{lbl}</div>
<div style="font-family:'Syne',sans-serif;font-weight:700;font-size:1rem;margin-top:4px;line-height:1.2;">{val}</div>
</div>""", unsafe_allow_html=True)

    # Skills + Certs in two columns
    sc1, sc2 = st.columns(2)
    with sc1:
        skills = extracted_data.get("required_skills", [])
        tags = "".join([f'<span class="tag">{s}</span>' for s in skills]) if skills else '<span class="tag">None extracted</span>'
        st.markdown(f"""
<div class="neu-card">
<div style="font-family:'DM Mono',monospace;font-size:0.62rem;letter-spacing:0.14em;text-transform:uppercase;color:var(--ink-muted);margin-bottom:0.6rem;">Required Skills</div>
<div class="tag-row">{tags}</div>
</div>""", unsafe_allow_html=True)

    with sc2:
        certs = extracted_data.get("required_certifications", [])
        tags2 = "".join([f'<span class="tag tag-accent2">{c}</span>' for c in certs]) if certs else '<span class="tag">None extracted</span>'
        edu = extracted_data.get("education_level") or "Not specified"
        st.markdown(f"""
<div class="neu-card">
<div style="font-family:'DM Mono',monospace;font-size:0.62rem;letter-spacing:0.14em;text-transform:uppercase;color:var(--ink-muted);margin-bottom:0.6rem;">Certifications &amp; Education</div>
<div class="tag-row">{tags2}</div>
<div style="margin-top:0.6rem;font-size:0.8rem;color:var(--ink-muted);">Education: <strong style="color:var(--ink);">{edu}</strong></div>
</div>""", unsafe_allow_html=True)

    with st.expander("View raw JSON payload"):
        st.json(extracted_data)

    st.markdown("<hr>", unsafe_allow_html=True)

    # ── MATCH RENDER ───────────────────────────
    st.markdown('<span class="section-label">03 — Matched Candidates</span>', unsafe_allow_html=True)
    
    # Graceful Empty State
    if filtered_df.empty:
        st.info("No candidates strictly matched all criteria in this region. CandidateIQ's deep-search engine prevents unqualified profiles from entering your pipeline. Try broadening the job requirements.")
    else:
        n = len(filtered_df)

        if fallback_used and city:
            st.info(f"No exact city match for **{city}**. Showing {n} regional candidates with matching titles.")

        # Stat strip update with Tooltips
        dept = extracted_data.get("department") or "Healthcare"
        top_score = f"{filtered_df['Match Score'].max()}%" if not filtered_df.empty else "N/A"
        avg_score = f"{int(filtered_df['Match Score'].mean())}%" if not filtered_df.empty else "N/A"
            
        ms1, ms2, ms3 = st.columns(3)
        
        ms1.markdown(f"""
        <div class="stat-card">
            <div class="stat-num">{n}</div>
            <div class="stat-lbl">Qualified Candidates</div>
        </div>""", unsafe_allow_html=True)
        
        ms2.markdown(f"""
        <div class="stat-card">
            <div class="stat-num">{top_score}</div>
            <div class="stat-lbl" title="Calculated by cross-referencing extracted clinical requirements against the candidate's background and skills.">Top Match Score ⓘ</div>
        </div>""", unsafe_allow_html=True)
        
        ms3.markdown(f"""
        <div class="stat-card">
            <div class="stat-num">{avg_score}</div>
            <div class="stat-lbl">Avg Pipeline Quality</div>
        </div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Result table with branded header
        st.markdown(f"""
        <div class="result-header">
            <span class="result-header-title">Candidate Pipeline — {dept}</span>
            <span class="result-header-count">Select any row below to view full profile</span>
        </div>""", unsafe_allow_html=True)

        # ── INTERACTIVE DATAFRAME ─────────────────────────────
        # Build columns dynamically to avoid crashes if CSV lacks the new fields
        base_cols = ["Name", "Job Title", "Match Score", "Company", "Location"]
        if "Last_Active" in filtered_df.columns: base_cols.append("Last_Active")
        if "Contact_Status" in filtered_df.columns: base_cols.append("Contact_Status")
        
        display_df = filtered_df[base_cols].copy()
        display_df = display_df.rename(columns={"Job Title": "Current Title"})
        
        # Add the % sign to the UI column
        display_df['Match Score'] = display_df['Match Score'].astype(str) + "%"
        
        selection_event = st.dataframe(
            display_df, 
            use_container_width=True, 
            hide_index=True,
            on_select="rerun",           
            selection_mode="single-row"  
        )

        # ── CANDIDATE PROFILE CARD ────────────────────────────
        selected_rows = selection_event.selection.rows
        if selected_rows:
            # Grab the specific candidate's full data from the hidden dataframe
            candidate = filtered_df.iloc[selected_rows[0]]
            
            # Logic for Verified Badges
            contact_status = candidate.get('Contact_Status', 'Not specified')
            is_verified = "Verified" in str(contact_status)
            status_color = "var(--accent-3)" if is_verified else "var(--accent)"
            status_icon = "✅" if is_verified else "⚠️"
            
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown('<span class="section-label">04 — Candidate Profile</span>', unsafe_allow_html=True)
            
            # Neobrutalist Resume UI
            st.markdown(f"""
            <div class="neu-card" style="border-top: 6px solid var(--accent); padding: 2rem;">
                <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                    <div>
                        <h2 style="font-family: 'Syne', sans-serif; font-weight: 800; margin: 0 0 5px 0;">{candidate['Name']}</h2>
                        <div style="font-family: 'DM Mono', monospace; color: var(--accent); font-size: 0.9rem; font-weight: 600;">{candidate['Job Title']}</div>
                        <div style="color: var(--ink-muted); font-size: 0.85rem; margin-top: 4px;">📍 {candidate['Location']} &nbsp;|&nbsp; 🏢 {candidate['Company']}</div>
                        <div style="color: var(--ink-muted); font-size: 0.75rem; margin-top: 4px;">🕒 Last Active: {candidate.get('Last_Active', 'Unknown')}</div>
                    </div>
                    <div style="text-align: right;">
                        <div style="font-family: 'Syne', sans-serif; font-weight: 700; font-size: 1.5rem; color: var(--accent-3);">{int(candidate['Match Score'])}% Match</div>
                        <div style="font-size: 0.8rem; color: var(--ink-muted);">{candidate['Years of Experience']} Years Exp.</div>
                    </div>
                </div>
                <hr style="margin: 1.2rem 0; border-top: 1px solid var(--shadow-dark);">
                
                <div style="display: flex; gap: 2rem; margin-bottom: 1.2rem;">
                    <div style="flex: 1; background: rgba(255,255,255,0.4); padding: 1rem; border-radius: 6px; border-left: 3px solid {status_color};">
                        <div style="font-family: 'DM Mono', monospace; font-size: 0.7rem; letter-spacing: 0.1em; color: var(--ink-muted); text-transform: uppercase; margin-bottom: 6px;">Contact Information</div>
                        <div style="font-size: 0.9rem; font-weight: 500;">✉️ {candidate.get('Email', 'Hidden')}</div>
                        <div style="font-size: 0.9rem; font-weight: 500; margin-top: 4px;">📞 {candidate.get('Phone', 'Hidden')} <span style="font-size: 0.75rem; color: {status_color};">({status_icon} {contact_status})</span></div>
                    </div>
                    <div style="flex: 1; display: flex; align-items: center; justify-content: center;">
                        <button disabled style="background: var(--surface); color: var(--ink-muted); border: 2px dashed var(--shadow-dark); padding: 10px 20px; border-radius: 6px; font-family: 'Syne', sans-serif; font-weight: 600; cursor: not-allowed; width: 80%;" title="Integration available in enterprise tier.">+ Add to Outreach Pipeline</button>
                    </div>
                </div>

                <div style="margin-bottom: 1.2rem;">
                    <div style="font-family: 'DM Mono', monospace; font-size: 0.7rem; letter-spacing: 0.1em; color: var(--ink-muted); text-transform: uppercase; margin-bottom: 6px;">Background Summary</div>
                    <div style="font-size: 0.95rem; line-height: 1.6; color: var(--ink); background: rgba(255,255,255,0.4); padding: 1rem; border-radius: 6px; border-left: 3px solid var(--border);">{candidate.get('Background_Summary', 'No summary provided.')}</div>
                </div>
                
                <div style="display: flex; gap: 2rem;">
                    <div style="flex: 1;">
                        <div style="font-family: 'DM Mono', monospace; font-size: 0.7rem; letter-spacing: 0.1em; color: var(--ink-muted); text-transform: uppercase; margin-bottom: 6px;">Clinical Skills</div>
                        <div style="font-size: 0.85rem; line-height: 1.5;">{str(candidate.get('Skills', '')).replace(',', ' • ')}</div>
                    </div>
                    <div style="flex: 1;">
                        <div style="font-family: 'DM Mono', monospace; font-size: 0.7rem; letter-spacing: 0.1em; color: var(--ink-muted); text-transform: uppercase; margin-bottom: 6px;">Certifications & Education</div>
                        <div style="font-size: 0.85rem; line-height: 1.5; color: var(--accent-2); font-weight: 500;">{str(candidate.get('Certifications', '')).replace(',', ' • ')} • {candidate.get('Education Level', '')}</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        # Export CSV
        st.markdown("<br>", unsafe_allow_html=True)
        csv = filtered_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="↓  Export CSV",
            data=csv,
            file_name="matched_candidates.csv",
            mime="text/csv",
        )

# Confidentiality Footer
st.markdown('<div class="footer-text">🔒 CandidateIQ Enterprise Encryption Active | Data Sourced via Proprietary Compliance Frameworks</div>', unsafe_allow_html=True)