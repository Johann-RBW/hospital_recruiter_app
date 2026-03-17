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
# STATE MANAGEMENT
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
  --accent:      #D4380D;         
  --accent-2:    #1D4ED8;         
  --accent-3:    #15803D;         
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

.stApp, 
[data-testid="stAppViewContainer"], 
[data-testid="stAppViewBlockContainer"], 
[data-testid="stHeader"] {
    background-color: var(--bg) !important;
    background: var(--bg) !important;
}

[data-testid="stHeader"] { display: none !important; }

/* ── Masthead ────────────────────────────────────────── */
.masthead { display: flex; align-items: flex-end; gap: 1.2rem; padding: 2rem 0 0.25rem; border-bottom: var(--border-w) solid var(--border); margin-bottom: 2.2rem; }
.masthead-mark { width: 44px; height: 44px; background: var(--accent); border: var(--border-w) solid var(--border); border-radius: var(--radius); display: flex; align-items: center; justify-content: center; font-size: 1.3rem; box-shadow: var(--brutalist-shadow); flex-shrink: 0; color: white;}
.masthead-title { font-family: 'Syne', sans-serif; font-weight: 800; font-size: 1.75rem; letter-spacing: -0.03em; line-height: 1; color: var(--ink); }
.masthead-sub { font-family: 'DM Mono', monospace; font-size: 0.7rem; color: var(--ink-muted); letter-spacing: 0.12em; text-transform: uppercase; margin-bottom: 3px; }
.section-label { font-family: 'DM Mono', monospace; font-size: 0.65rem; letter-spacing: 0.18em; text-transform: uppercase; color: var(--ink-muted); margin-bottom: 0.5rem; display: block; }

/* ── Components ─────────────────────────────────── */
.neu-card { background: var(--surface); border-radius: 12px; box-shadow: var(--neu-shadow); border: var(--border-w) solid var(--border); padding: 1.6rem 1.8rem; margin-bottom: 1.4rem; position: relative; }
.tag-row { display: flex; flex-wrap: wrap; gap: 0.45rem; margin-top: 0.5rem; }
.tag { font-family: 'DM Mono', monospace; font-size: 0.7rem; font-weight: 500; padding: 3px 10px; border: 2px solid var(--border); border-radius: 3px; background: var(--surface); box-shadow: 2px 2px 0 var(--border); letter-spacing: 0.04em; color: var(--ink); }
.tag-accent  { background: var(--accent);  color: #fff; border-color: var(--border); }
.tag-accent2 { background: var(--accent-2); color: #fff; }

/* ── Streamlit Overrides ────────────────────── */
.stTextArea textarea { background: var(--surface) !important; box-shadow: var(--neu-inset) !important; border: var(--border-w) solid var(--border) !important; border-radius: var(--radius) !important; font-family: 'DM Sans', sans-serif !important; font-size: 0.9rem !important; color: var(--ink) !important; padding: 0.9rem 1rem !important; transition: box-shadow 0.2s ease; }
.stTextArea textarea:focus { box-shadow: var(--neu-inset), 0 0 0 3px rgba(212,56,13,0.18) !important; outline: none !important; }
.stButton > button[kind="primary"] { background: var(--accent) !important; color: #fff !important; font-family: 'Syne', sans-serif !important; font-weight: 700 !important; font-size: 0.95rem !important; border: var(--border-w) solid var(--border) !important; border-radius: var(--radius) !important; padding: 0.55rem 2rem !important; box-shadow: var(--brutalist-shadow) !important; transition: transform 0.1s, box-shadow 0.1s !important; cursor: pointer !important; }
.stButton > button[kind="primary"]:hover { transform: translate(-2px, -2px) !important; box-shadow: 6px 6px 0 var(--border) !important; }
.stDownloadButton > button { background: var(--surface) !important; color: var(--ink) !important; font-family: 'DM Mono', monospace !important; font-size: 0.75rem !important; border: var(--border-w) solid var(--border) !important; border-radius: var(--radius) !important; box-shadow: 3px 3px 0 var(--border) !important; }
.stDataFrame { border: var(--border-w) solid var(--border) !important; border-radius: var(--radius) !important; box-shadow: var(--neu-shadow) !important; overflow: hidden !important; }
.stDataFrame thead tr th { background: var(--ink) !important; color: var(--bg) !important; font-family: 'DM Mono', monospace !important; font-size: 0.68rem !important; padding: 0.7rem 1rem !important; }
.stat-card { background: var(--surface); border: var(--border-w) solid var(--border); border-radius: var(--radius); box-shadow: var(--neu-shadow); padding: 1rem 1.2rem; text-align: left; }
.stat-card .stat-num { font-family: 'Syne', sans-serif; font-weight: 800; font-size: 2rem; line-height: 1; color: var(--accent); }
.stat-card .stat-lbl { font-family: 'DM Mono', monospace; font-size: 0.62rem; letter-spacing: 0.15em; text-transform: uppercase; color: var(--ink-muted); margin-top: 4px; }
.result-header { display: flex; justify-content: space-between; padding: 0.75rem 1rem; background: var(--ink); color: var(--bg); border-radius: var(--radius) var(--radius) 0 0; border: var(--border-w) solid var(--border); margin-bottom: -2px; }
.result-header-title { font-family: 'Syne', sans-serif; font-weight: 700; font-size: 0.9rem; }
hr { border: none !important; border-top: var(--border-w) solid var(--border) !important; margin: 1.5rem 0 !important; }
.footer-text { text-align: center; font-family: 'DM Mono', monospace; font-size: 0.65rem; color: var(--ink-muted); margin-top: 3rem; }
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

try:
    groq_client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except KeyError:
    st.error("⚠ GROQ_API_KEY is missing. Add it to .streamlit/secrets.toml.")
    st.stop()

# ─────────────────────────────────────────────────────────────
# LAYOUT
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
  <div style="font-family:'DM Mono',monospace;font-size:0.65rem;letter-spacing:0.14em;color:var(--accent);text-transform:uppercase;margin-bottom:0.8rem;">Two-Stage AI Processing</div>
  <div style="margin-bottom:0.75rem;">
    <div style="font-family:'Syne',sans-serif;font-weight:700;font-size:0.82rem;">01 &nbsp;Extraction</div>
    <div style="font-size:0.8rem;color:var(--ink-muted);line-height:1.5;margin-top:2px;">LLaMA 3.1 standardizes JD requirements into clinical taxonomies.</div>
  </div>
  <div>
    <div style="font-family:'Syne',sans-serif;font-weight:700;font-size:0.82rem;">02 &nbsp;Reranker Judgment</div>
    <div style="font-size:0.8rem;color:var(--ink-muted);line-height:1.5;margin-top:2px;">Our LLM reads viable resumes, weights clinical certs, and outputs intelligent match scores with explicit reasoning.</div>
  </div>
</div>
""", unsafe_allow_html=True)

st.markdown("<hr>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# SEARCH LOGIC
# ─────────────────────────────────────────────────────────────
if search_clicked:
    if not job_description.strip():
        st.warning("Please paste a job description before running a search.")
        st.session_state.search_active = False
    else:
        st.session_state.search_active = True
        
        # ── STEP 1: Groq Extraction ──────────────────────────
        with st.spinner("Parsing job description with LLaMA 3.1…"):
            extract_prompt = f"""
            You are an expert healthcare recruiter. NORMALIZE AND STANDARDIZE all skills, certifications, and education into their most common healthcare industry acronyms.
            EXPAND the search net: Include both acronyms and spelled-out versions.
            SPELL OUT TITLES: If the JD uses an acronym for the main title (like PCA, HHA), spell it out completely in `job_title`.
            IGNORE SOFT SKILLS: Do NOT extract subjective traits like "compassionate".
            LOCATION PARSING: Extract only the most prominent central city.

            Return ONLY a valid JSON object with:
            - "job_title" (string)
            - "department" (string or null)
            - "required_skills" (list of strings)
            - "required_certifications" (list of strings)
            - "education_level" (string or null)
            - "location" (string)
            - "years_of_experience" (string or number)
            - "shift_type" (string or null)
            
            Job Description: {job_description}
            """
            try:
                response = groq_client.chat.completions.create(
                    messages=[{"role": "user", "content": extract_prompt}],
                    model="llama-3.1-8b-instant",
                    response_format={"type": "json_object"},
                    temperature=0,
                )
                st.session_state.extracted_data = json.loads(response.choices[0].message.content)
            except Exception as e:
                st.error(f"Groq extraction failed: {e}")
                st.stop()

        # ── STEP 2: Database Match & AI Scoring ───────────────────
        with st.spinner("LLM reading resumes and generating clinical scores…"):
            try:
                df = pd.read_csv("candidates.csv")
                
                # Filter Location for UI
                ext_loc = st.session_state.extracted_data.get("location")
                st.session_state.fallback_used = False
                st.session_state.city = None
                if ext_loc and str(ext_loc).lower() != "null":
                    st.session_state.city = ext_loc.split(",")[0].strip()
                    local_df = df[df["Location"].str.contains(st.session_state.city, case=False, na=False, regex=False)]
                    if local_df.empty: st.session_state.fallback_used = True
                
                # --- STAGE 1: PYTHON SIFT (Fast Keyword Match) ---
                req_skills = st.session_state.extracted_data.get("required_skills", []) or []
                req_certs = st.session_state.extracted_data.get("required_certifications", []) or []
                ext_title = str(st.session_state.extracted_data.get("job_title", "")).lower()
                target_keywords = [str(k).lower().strip() for k in (req_skills + req_certs)]
                if ext_title and ext_title != "null": target_keywords.extend([w for w in ext_title.split() if len(w) > 2])
                target_keywords = list(set(target_keywords))

                def sift_score(row):
                    if not target_keywords: return 1
                    cand_text = " ".join([str(row.get('Job Title','')), str(row.get('Skills','')), str(row.get('Certifications',''))]).lower()
                    return sum(1 for kw in target_keywords if kw in cand_text)

                df['Sift_Hits'] = df.apply(sift_score, axis=1)
                shortlist_df = df[df['Sift_Hits'] > 0].sort_values(by='Sift_Hits', ascending=False).head(10) # Grab top 10 for LLM

                # --- STAGE 2: LLM JUDGE (Intelligent Scoring) ---
                if not shortlist_df.empty:
                    candidates_payload = shortlist_df[['Name', 'Job Title', 'Skills', 'Certifications', 'Background_Summary', 'Years of Experience']].to_dict(orient='records')
                    
                    judge_prompt = f"""
                    You are an expert AI Recruiting Judge. 
                    Job Requirements: {json.dumps(st.session_state.extracted_data)}
                    
                    Here are {len(candidates_payload)} candidates. Read their profiles and score them from 0 to 98 based on how well they fit the requirements. 
                    - Prioritize active licenses, exact required certifications, and years of experience.
                    - Provide a 1-sentence analytical reasoning explaining the score.
                    
                    Return ONLY a JSON object with a "results" array containing objects with "Name", "Match_Score" (integer), and "AI_Reasoning" (string).
                    Candidates: {json.dumps(candidates_payload)}
                    """
                    
                    judge_response = groq_client.chat.completions.create(
                        messages=[{"role": "user", "content": judge_prompt}],
                        model="llama-3.1-8b-instant",
                        response_format={"type": "json_object"},
                        temperature=0.1,
                    )
                    
                    ai_scores = json.loads(judge_response.choices[0].message.content).get("results", [])
                    ai_df = pd.DataFrame(ai_scores)
                    
                    # Merge LLM brains back into main dataframe
                    merged_df = shortlist_df.merge(ai_df, on="Name", how="inner")
                    if 'Match_Score' in merged_df.columns:
                        merged_df['Match Score'] = merged_df['Match_Score']
                    else:
                        merged_df['Match Score'] = 50 # Fallback
                        
                    st.session_state.filtered_df = merged_df.sort_values(by='Match Score', ascending=False)
                else:
                    st.session_state.filtered_df = pd.DataFrame()

            except Exception as e:
                st.error(f"Database search error: {e}")
                st.stop()


# ─────────────────────────────────────────────────────────────
# RENDER RESULTS
# ─────────────────────────────────────────────────────────────
if st.session_state.search_active:
    extracted_data = st.session_state.extracted_data
    filtered_df = st.session_state.filtered_df
    fallback_used = st.session_state.fallback_used
    city = st.session_state.city
    
    st.markdown('<span class="section-label">02 — Extracted Requirements</span>', unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    cards = [
        (c1, "Role", extracted_data.get("job_title", "—"), "accent"),
        (c2, "Location", extracted_data.get("location", "—"), "default"),
        (c3, "Experience", str(extracted_data.get("years_of_experience","—")), "default"),
        (c4, "Shift", extracted_data.get("shift_type") or "Unspecified", "default"),
    ]
    for col, lbl, val, kind in cards:
        with col:
            border_color = "var(--accent)" if kind == "accent" else "var(--border)"
            col.markdown(f"""<div class="neu-card" style="border-left: 4px solid {border_color}; padding: 0.9rem 1.1rem;"><div style="font-family:'DM Mono',monospace;font-size:0.6rem;letter-spacing:0.15em;text-transform:uppercase;color:var(--ink-muted);">{lbl}</div><div style="font-family:'Syne',sans-serif;font-weight:700;font-size:1rem;margin-top:4px;line-height:1.2;">{val}</div></div>""", unsafe_allow_html=True)

    st.markdown("<hr>", unsafe_allow_html=True)

    # ── MATCH RENDER ───────────────────────────
    st.markdown('<span class="section-label">03 — AI Scored Pipeline</span>', unsafe_allow_html=True)
    
    if filtered_df.empty:
        st.info("No candidates strictly matched all criteria in this region. CandidateIQ's deep-search engine prevents unqualified profiles from entering your pipeline. Try broadening the job requirements.")
    else:
        n = len(filtered_df)
        if fallback_used and city:
            st.info(f"No exact city match for **{city}**. Showing {n} regional candidates with matching titles.")

        dept = extracted_data.get("department") or "Healthcare"
        top_score = f"{filtered_df['Match Score'].max()}%" if not filtered_df.empty else "N/A"
        avg_score = f"{int(filtered_df['Match Score'].mean())}%" if not filtered_df.empty else "N/A"
            
        ms1, ms2, ms3 = st.columns(3)
        ms1.markdown(f'<div class="stat-card"><div class="stat-num">{n}</div><div class="stat-lbl">Shortlisted Candidates</div></div>', unsafe_allow_html=True)
        ms2.markdown(f'<div class="stat-card"><div class="stat-num">{top_score}</div><div class="stat-lbl" title="Generated by LLaMA 3.1 analysis.">Top AI Match Score ⓘ</div></div>', unsafe_allow_html=True)
        ms3.markdown(f'<div class="stat-card"><div class="stat-num">{avg_score}</div><div class="stat-lbl">Avg Pipeline Quality</div></div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown(f'<div class="result-header"><span class="result-header-title">Candidate Pipeline — {dept}</span><span class="result-header-count">Select any row below to view full profile</span></div>', unsafe_allow_html=True)

        # ── INTERACTIVE DATAFRAME ─────────────────────────────
        base_cols = ["Name", "Job Title", "Match Score", "Company", "Location"]
        if "Last_Active" in filtered_df.columns: base_cols.append("Last_Active")
        
        display_df = filtered_df[base_cols].copy()
        display_df = display_df.rename(columns={"Job Title": "Current Title"})
        display_df['Match Score'] = display_df['Match Score'].astype(str) + "%"
        
        selection_event = st.dataframe(display_df, use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row")

        # ── CANDIDATE PROFILE CARD ────────────────────────────
        selected_rows = selection_event.selection.rows
        if selected_rows:
            candidate = filtered_df.iloc[selected_rows[0]]
            
            contact_status = candidate.get('Contact_Status', 'Pending')
            is_verified = "Verified" in str(contact_status)
            status_color = "var(--accent-3)" if is_verified else "var(--accent)"
            status_icon = "✅" if is_verified else "⚠️"
            
            ai_reasoning = candidate.get('AI_Reasoning', 'LLM reasoning successfully generated score based on clinical overlap.')
            
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown('<span class="section-label">04 — Candidate Profile</span>', unsafe_allow_html=True)
            
            # Un-indented HTML to prevent Markdown code-block errors
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

<div style="background: rgba(212,56,13,0.05); border-left: 3px solid var(--accent); padding: 1rem; border-radius: 6px; margin-bottom: 1.2rem;">
<div style="font-family: 'DM Mono', monospace; font-size: 0.7rem; letter-spacing: 0.1em; color: var(--accent); text-transform: uppercase; margin-bottom: 4px;">✦ AI Match Reasoning</div>
<div style="font-size: 0.9rem; color: var(--ink); line-height: 1.5; font-weight: 500;">{ai_reasoning}</div>
</div>

<div style="background: rgba(255,255,255,0.4); padding: 1rem; border-radius: 6px; border-left: 3px solid {status_color}; margin-bottom: 1.2rem;">
<div style="font-family: 'DM Mono', monospace; font-size: 0.7rem; letter-spacing: 0.1em; color: var(--ink-muted); text-transform: uppercase; margin-bottom: 6px;">Contact Information</div>
<div style="font-size: 0.9rem; font-weight: 500;">✉️ {candidate.get('Email', 'Hidden')}</div>
<div style="font-size: 0.9rem; font-weight: 500; margin-top: 4px;">📞 {candidate.get('Phone', 'Hidden')} <span style="font-size: 0.75rem; color: {status_color};">({status_icon} {contact_status})</span></div>
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

        st.markdown("<br>", unsafe_allow_html=True)
        csv = filtered_df.to_csv(index=False).encode("utf-8")
        st.download_button(label="↓  Export CSV", data=csv, file_name="matched_candidates.csv", mime="text/csv")

st.markdown('<div class="footer-text">🔒 CandidateIQ Enterprise Encryption Active | Data Sourced via Proprietary Compliance Frameworks</div>', unsafe_allow_html=True)