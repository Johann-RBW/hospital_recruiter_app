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

CRITICAL INSTRUCTION: Do not just look for explicit keywords. Deduce and extrapolate required skills,
certifications, and experience levels from the context of daily responsibilities, patient care duties,
and tools mentioned in the text.

Return ONLY a valid JSON object with these exact keys:
- "job_title" (string)
- "department" (string or null)
- "required_skills" (list of strings)
- "required_certifications" (list of strings)
- "education_level" (string or null)
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

                # 1. Title match (Base Filter)
                extracted_title = st.session_state.extracted_data.get("job_title")
                if extracted_title and str(extracted_title).lower() != "null":
                    core_title = " ".join(
                        str(extracted_title).replace("(", "").replace(")", "").split()[:2]
                    )
                    filtered_df = filtered_df[
                        filtered_df["Job Title"].str.contains(core_title, case=False, na=False, regex=False)
                    ]

                # 2. Location match with fallback (Base Filter)
                extracted_location = st.session_state.extracted_data.get("location")
                location_matched_df = filtered_df.copy()
                
                st.session_state.fallback_used = False
                st.session_state.city = None

                if extracted_location and str(extracted_location).lower() != "null":
                    st.session_state.city = extracted_location.split(",")[0].strip()
                    location_matched_df = filtered_df[
                        filtered_df["Location"].str.contains(st.session_state.city, case=False, na=False, regex=False)
                    ]

                if location_matched_df.empty and not filtered_df.empty:
                    st.session_state.fallback_used = True
                else:
                    filtered_df = location_matched_df

                # 3. AI Resume Scoring Engine
                # Pool all extracted requirements
                req_skills = st.session_state.extracted_data.get("required_skills", []) or []
                req_certs = st.session_state.extracted_data.get("required_certifications", []) or []
                target_keywords = [str(k).lower().strip() for k in (req_skills + req_certs) if k]

                def calculate_score(row):
                    if not target_keywords:
                        return 100 # If Groq found 0 requirements, assume 100% match based on title alone
                    
                    # Mash candidate data together into a "resume block"
                    cand_text = " ".join([
                        str(row.get('Skills', '')),
                        str(row.get('Certifications', '')),
                        str(row.get('Background_Summary', ''))
                    ]).lower()
                    
                    # Count matches
                    matches = sum(1 for kw in target_keywords if kw in cand_text)
                    return int((matches / len(target_keywords)) * 100)

                # Apply the score
                filtered_df['Match Score'] = filtered_df.apply(calculate_score, axis=1)
                
                # THE KILL SWITCH: Drop anyone with a 0% skill match
                if target_keywords:
                    filtered_df = filtered_df[filtered_df['Match Score'] > 0]

                # Sort best candidates to the top
                filtered_df = filtered_df.sort_values(by='Match Score', ascending=False)
                    
                st.session_state.filtered_df = filtered_df

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
    
    if filtered_df.empty:
        st.warning("No candidates matched the extracted requirements in the current database. Try broadening the job description.")
    else:
        n = len(filtered_df)

        if fallback_used and city:
            st.info(f"No exact city match for **{city}**. Showing {n} regional candidates with matching titles.")

        # Stat strip update
        dept = extracted_data.get("department") or "Healthcare"
        top_score = f"{filtered_df['Match Score'].max()}%" if not filtered_df.empty else "N/A"
        avg_score = f"{int(filtered_df['Match Score'].mean())}%" if not filtered_df.empty else "N/A"
            
        ms1, ms2, ms3 = st.columns(3)
        for col, num, lbl in [
            (ms1, n,              "Qualified Candidates"),
            (ms2, top_score,      "Top Match Score"),
            (ms3, avg_score,      "Avg Match Score"),
        ]:
            with col:
                col.markdown(f"""
<div class="stat-card">
<div class="stat-num">{num}</div>
<div class="stat-lbl">{lbl}</div>
</div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Result table with branded header
        st.markdown(f"""
<div class="result-header">
<span class="result-header-title">Candidate Results — {dept}</span>
<span class="result-header-count">{n} record{'s' if n!=1 else ''}</span>
</div>""", unsafe_allow_html=True)

        # Format display dataframe
        display_cols = ["Name", "Job Title", "Match Score", "Company", "Location", "Email", "Phone"]
        display_df = filtered_df[display_cols].copy()
        display_df = display_df.rename(columns={"Job Title": "Current Title"})
        
        # Add the % sign to the UI column
        display_df['Match Score'] = display_df['Match Score'].astype(str) + "%"
        
        st.dataframe(display_df, use_container_width=True, hide_index=True)

        # Export (Keep numeric scores for the CSV)
        st.markdown("<br>", unsafe_allow_html=True)
        csv = filtered_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="↓  Export CSV",
            data=csv,
            file_name="matched_candidates.csv",
            mime="text/csv",
        )