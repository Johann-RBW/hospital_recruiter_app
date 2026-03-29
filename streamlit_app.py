import streamlit as st
import pandas as pd
import json
import os
from auth import (
    is_logged_in, login_user, logout_user,
    authenticate_user, create_user,
    validate_invite_token, consume_invite_token,
    username_exists, email_already_registered,
    init_db,
)

# Initialize DB — safe every run, uses CREATE IF NOT EXISTS
init_db()

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
# SESSION STATE INIT
# ─────────────────────────────────────────────────────────────
defaults = {
    "authenticated": False,
    "user": None,
    "search_active": False,
    "extracted_data": {},
    "filtered_df": pd.DataFrame(),
    "fallback_used": False,
    "city": None,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ─────────────────────────────────────────────────────────────
# AUTH SCREENS  — pure Streamlit only, zero custom CSS/HTML
# ─────────────────────────────────────────────────────────────

def render_login():
    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        st.markdown("## ⬡ CandidateIQ")
        st.caption("HEALTHCARE TALENT INTELLIGENCE")
        st.divider()
        st.markdown("### Sign In")

        username = st.text_input("Username", key="login_username", placeholder="your username")
        password = st.text_input("Password", key="login_password", type="password", placeholder="••••••••")

        if st.button("Sign In →", type="primary", use_container_width=True):
            if not username.strip() or not password.strip():
                st.error("Please enter both username and password.")
            else:
                user = authenticate_user(username, password)
                if user:
                    login_user(st.session_state, user)
                    st.rerun()
                else:
                    st.error("Invalid username or password.")

        st.divider()
        st.caption("Access by invitation only · Contact your administrator")


def render_signup(token: str):
    invite = validate_invite_token(token)

    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        st.markdown("## ⬡ CandidateIQ")
        st.caption("HEALTHCARE TALENT INTELLIGENCE")
        st.divider()

        if not invite:
            st.error("This invite link is invalid or has expired.")
            st.caption("Please contact your administrator for a new invite link.")
            return

        invited_email = invite["email"]
        st.markdown("### Create Account")
        st.caption(f"Invited as **{invited_email}**")

        if email_already_registered(invited_email):
            st.warning("An account for this email already exists.")
            if st.button("Go to Sign In", type="primary"):
                st.query_params.clear()
                st.rerun()
            return

        username  = st.text_input("Choose a username",  key="signup_username",  placeholder="e.g. jsmith")
        password  = st.text_input("Choose a password",  key="signup_password",  type="password", placeholder="Min 8 characters")
        password2 = st.text_input("Confirm password",   key="signup_password2", type="password", placeholder="Re-enter password")

        if st.button("Create Account →", type="primary", use_container_width=True):
            uname  = username.strip().lower()
            errors = []

            if len(uname) < 3:
                errors.append("Username must be at least 3 characters.")
            if not uname.replace("_", "").replace("-", "").isalnum():
                errors.append("Username can only contain letters, numbers, hyphens, and underscores.")
            if username_exists(uname):
                errors.append("That username is already taken.")
            if len(password) < 8:
                errors.append("Password must be at least 8 characters.")
            if password != password2:
                errors.append("Passwords do not match.")

            if errors:
                for e in errors:
                    st.error(e)
            else:
                success = create_user(invited_email, uname, password)
                if success:
                    consume_invite_token(token)
                    st.success(f"Account created! Welcome, {uname}. Signing you in…")
                    user = authenticate_user(uname, password)
                    if user:
                        login_user(st.session_state, user)
                        st.query_params.clear()
                        st.rerun()
                else:
                    st.error("Account creation failed. Username or email may already exist.")

        st.divider()
        st.caption("Access by invitation only · Contact your administrator")


# ─────────────────────────────────────────────────────────────
# MAIN APP  — all custom CSS lives here, only loads post-auth
# ─────────────────────────────────────────────────────────────

def render_app():
    # CSS only injected for authenticated sessions
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Mono:wght@400;500&family=DM+Sans:wght@300;400;500&display=swap');

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

.masthead { display: flex; align-items: flex-end; gap: 1.2rem; padding: 2rem 0 0.25rem; border-bottom: var(--border-w) solid var(--border); margin-bottom: 2.2rem; }
.masthead-mark { width: 44px; height: 44px; background: var(--accent); border: var(--border-w) solid var(--border); border-radius: var(--radius); display: flex; align-items: center; justify-content: center; font-size: 1.3rem; box-shadow: var(--brutalist-shadow); flex-shrink: 0; color: white;}
.masthead-title { font-family: 'Syne', sans-serif; font-weight: 800; font-size: 1.75rem; letter-spacing: -0.03em; line-height: 1; color: var(--ink); }
.masthead-sub { font-family: 'DM Mono', monospace; font-size: 0.7rem; color: var(--ink-muted); letter-spacing: 0.12em; text-transform: uppercase; margin-bottom: 3px; }
.section-label { font-family: 'DM Mono', monospace; font-size: 0.65rem; letter-spacing: 0.18em; text-transform: uppercase; color: var(--ink-muted); margin-bottom: 0.5rem; display: block; }
.neu-card { background: var(--surface); border-radius: 12px; box-shadow: var(--neu-shadow); border: var(--border-w) solid var(--border); padding: 1.6rem 1.8rem; margin-bottom: 1.4rem; position: relative; }
.stTextArea textarea { background: var(--surface) !important; box-shadow: var(--neu-inset) !important; border: var(--border-w) solid var(--border) !important; border-radius: var(--radius) !important; font-family: 'DM Sans', sans-serif !important; font-size: 0.9rem !important; color: var(--ink) !important; padding: 0.9rem 1rem !important; }
.stButton > button[kind="primary"] { background: var(--accent) !important; color: #fff !important; font-family: 'Syne', sans-serif !important; font-weight: 700 !important; font-size: 0.95rem !important; border: var(--border-w) solid var(--border) !important; border-radius: var(--radius) !important; padding: 0.55rem 2rem !important; box-shadow: var(--brutalist-shadow) !important; transition: transform 0.1s, box-shadow 0.1s !important; }
.stButton > button[kind="primary"]:hover { transform: translate(-2px, -2px) !important; box-shadow: 6px 6px 0 var(--border) !important; }
.stButton > button[kind="secondary"] { background: var(--surface) !important; color: var(--ink) !important; font-family: 'DM Mono', monospace !important; font-size: 0.8rem !important; border: var(--border-w) solid var(--border) !important; border-radius: var(--radius) !important; box-shadow: 3px 3px 0 var(--border) !important; }
.stDownloadButton > button { background: var(--surface) !important; color: var(--ink) !important; font-family: 'DM Mono', monospace !important; font-size: 0.75rem !important; border: var(--border-w) solid var(--border) !important; border-radius: var(--radius) !important; box-shadow: 3px 3px 0 var(--border) !important; }
.stDataFrame { border: var(--border-w) solid var(--border) !important; border-radius: var(--radius) !important; box-shadow: var(--neu-shadow) !important; overflow: hidden !important; }
.stDataFrame thead tr th { background: var(--ink) !important; color: var(--bg) !important; font-family: 'DM Mono', monospace !important; font-size: 0.68rem !important; padding: 0.7rem 1rem !important; }
.stat-card { background: var(--surface); border: var(--border-w) solid var(--border); border-radius: var(--radius); box-shadow: var(--neu-shadow); padding: 1rem 1.2rem; }
.stat-card .stat-num { font-family: 'Syne', sans-serif; font-weight: 800; font-size: 2rem; line-height: 1; color: var(--accent); }
.stat-card .stat-lbl { font-family: 'DM Mono', monospace; font-size: 0.62rem; letter-spacing: 0.15em; text-transform: uppercase; color: var(--ink-muted); margin-top: 4px; }
.result-header { display: flex; justify-content: space-between; padding: 0.75rem 1rem; background: var(--ink); color: var(--bg); border-radius: var(--radius) var(--radius) 0 0; border: var(--border-w) solid var(--border); margin-bottom: -2px; }
.result-header-title { font-family: 'Syne', sans-serif; font-weight: 700; font-size: 0.9rem; }
hr { border: none !important; border-top: var(--border-w) solid var(--border) !important; margin: 1.5rem 0 !important; }
.footer-text { text-align: center; font-family: 'DM Mono', monospace; font-size: 0.65rem; color: var(--ink-muted); margin-top: 3rem; }
.user-chip { display: inline-flex; align-items: center; gap: 0.5rem; font-family: 'DM Mono', monospace; font-size: 0.7rem; background: var(--surface); border: var(--border-w) solid var(--border); border-radius: 3px; padding: 4px 10px; box-shadow: 2px 2px 0 var(--border); color: var(--ink-muted); }
</style>
""", unsafe_allow_html=True)

    # ── LAZY IMPORTS (only when authenticated user reaches the app)
    from groq import Groq
    from pdl_search import get_candidates_from_pdl

    try:
        groq_client = Groq(api_key=st.secrets["GROQ_API_KEY"])
    except KeyError:
        st.error("⚠ GROQ_API_KEY is missing. Add it to .streamlit/secrets.toml.")
        st.stop()

    try:
        pdl_api_key = st.secrets["PDL_API_KEY"]
    except KeyError:
        st.error("⚠ PDL_API_KEY is missing. Add it to .streamlit/secrets.toml.")
        st.stop()

    # ── MASTHEAD ───────────────────────────────────────────
    uname = st.session_state.user["username"]
    st.markdown(f"""
<div class="masthead">
  <div class="masthead-mark">⬡</div>
  <div style="flex:1;">
    <div class="masthead-sub">Healthcare Talent Intelligence</div>
    <div class="masthead-title">CandidateIQ</div>
  </div>
  <div class="user-chip">⬡ {uname}</div>
</div>
""", unsafe_allow_html=True)

    _, col_logout = st.columns([6, 1])
    with col_logout:
        if st.button("Sign Out", type="secondary"):
            logout_user(st.session_state)
            st.rerun()

    # ── LAYOUT ────────────────────────────────────────────
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

    # ── SEARCH LOGIC ──────────────────────────────────────
    if search_clicked:
        if not job_description.strip():
            st.warning("Please paste a job description before running a search.")
            st.session_state.search_active = False
        else:
            st.session_state.search_active = True

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

            with st.spinner("Searching live candidate database via PDL…"):
                try:
                    df = get_candidates_from_pdl(st.session_state.extracted_data, pdl_api_key)

                    if df.empty:
                        st.warning("PDL returned no candidates. Try broadening the job description.")
                        st.session_state.filtered_df = pd.DataFrame()
                        st.session_state.search_active = False
                        st.stop()

                    ext_loc = st.session_state.extracted_data.get("location")
                    st.session_state.fallback_used = False
                    st.session_state.city = None
                    if ext_loc and str(ext_loc).lower() != "null":
                        st.session_state.city = ext_loc.split(",")[0].strip()
                        local_df = df[df["Location"].str.contains(st.session_state.city, case=False, na=False, regex=False)]
                        if local_df.empty:
                            st.session_state.fallback_used = True

                    req_skills      = st.session_state.extracted_data.get("required_skills", []) or []
                    req_certs       = st.session_state.extracted_data.get("required_certifications", []) or []
                    ext_title       = str(st.session_state.extracted_data.get("job_title", "")).lower()
                    target_keywords = [str(k).lower().strip() for k in (req_skills + req_certs)]
                    if ext_title and ext_title != "null":
                        target_keywords.extend([w for w in ext_title.split() if len(w) > 2])
                    target_keywords = list(set(target_keywords))

                    def sift_score(row):
                        if not target_keywords:
                            return 1
                        cand_text = " ".join([
                            str(row.get('Job Title', '')),
                            str(row.get('Skills', '')),
                            str(row.get('Certifications', ''))
                        ]).lower()
                        return sum(1 for kw in target_keywords if kw in cand_text)

                    df['Sift_Hits'] = df.apply(sift_score, axis=1)
                    shortlist_df    = df[df['Sift_Hits'] > 0].sort_values(by='Sift_Hits', ascending=False).head(10)

                    if shortlist_df.empty:
                        shortlist_df = df.head(10)

                    with st.spinner("LLM reading profiles and generating clinical scores…"):
                        candidates_payload = shortlist_df[[
                            'Name', 'Job Title', 'Skills', 'Certifications',
                            'Background_Summary', 'Years of Experience'
                        ]].to_dict(orient='records')

                        judge_prompt = f"""
                        You are an expert AI Recruiting Judge.
                        Job Requirements: {json.dumps(st.session_state.extracted_data)}

                        Here are {len(candidates_payload)} candidates. Score them 0–98 on fit.
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
                        ai_df     = pd.DataFrame(ai_scores)
                        merged_df = shortlist_df.merge(ai_df, on="Name", how="left")

                        if 'Match_Score' in merged_df.columns:
                            merged_df['Match Score'] = merged_df['Match_Score'].fillna(50).astype(int)
                        else:
                            merged_df['Match Score'] = 50

                        st.session_state.filtered_df = merged_df.sort_values(by='Match Score', ascending=False)

                except Exception as e:
                    st.error(f"Candidate search error: {e}")
                    st.stop()

    # ── RENDER RESULTS ────────────────────────────────────
    if st.session_state.search_active:
        extracted_data = st.session_state.extracted_data
        filtered_df    = st.session_state.filtered_df
        fallback_used  = st.session_state.fallback_used
        city           = st.session_state.city

        st.markdown('<span class="section-label">02 — Extracted Requirements</span>', unsafe_allow_html=True)

        c1, c2, c3, c4 = st.columns(4)
        cards = [
            (c1, "Role",       extracted_data.get("job_title", "—"),                "accent"),
            (c2, "Location",   extracted_data.get("location", "—"),                 "default"),
            (c3, "Experience", str(extracted_data.get("years_of_experience", "—")), "default"),
            (c4, "Shift",      extracted_data.get("shift_type") or "Unspecified",   "default"),
        ]
        for col, lbl, val, kind in cards:
            with col:
                border_color = "var(--accent)" if kind == "accent" else "var(--border)"
                col.markdown(f"""<div class="neu-card" style="border-left: 4px solid {border_color}; padding: 0.9rem 1.1rem;"><div style="font-family:'DM Mono',monospace;font-size:0.6rem;letter-spacing:0.15em;text-transform:uppercase;color:var(--ink-muted);">{lbl}</div><div style="font-family:'Syne',sans-serif;font-weight:700;font-size:1rem;margin-top:4px;line-height:1.2;">{val}</div></div>""", unsafe_allow_html=True)

        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown('<span class="section-label">03 — AI Scored Pipeline</span>', unsafe_allow_html=True)

        if filtered_df.empty:
            st.info("No candidates matched all criteria. Try broadening the job requirements.")
        else:
            n         = len(filtered_df)
            dept      = extracted_data.get("department") or "Healthcare"
            top_score = f"{filtered_df['Match Score'].max()}%" if not filtered_df.empty else "N/A"
            avg_score = f"{int(filtered_df['Match Score'].mean())}%" if not filtered_df.empty else "N/A"

            if fallback_used and city:
                st.info(f"No exact city match for **{city}**. Showing {n} regional candidates.")

            ms1, ms2, ms3 = st.columns(3)
            ms1.markdown(f'<div class="stat-card"><div class="stat-num">{n}</div><div class="stat-lbl">Shortlisted Candidates</div></div>', unsafe_allow_html=True)
            ms2.markdown(f'<div class="stat-card"><div class="stat-num">{top_score}</div><div class="stat-lbl">Top AI Match Score</div></div>', unsafe_allow_html=True)
            ms3.markdown(f'<div class="stat-card"><div class="stat-num">{avg_score}</div><div class="stat-lbl">Avg Pipeline Quality</div></div>', unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown(f'<div class="result-header"><span class="result-header-title">Candidate Pipeline — {dept}</span><span>Select any row to view full profile</span></div>', unsafe_allow_html=True)

            base_cols = ["Name", "Job Title", "Match Score", "Company", "Location"]
            if "Last_Active" in filtered_df.columns:
                base_cols.append("Last_Active")

            display_df = filtered_df[base_cols].copy()
            display_df = display_df.rename(columns={"Job Title": "Current Title"})
            display_df['Match Score'] = display_df['Match Score'].astype(str) + "%"

            selection_event = st.dataframe(display_df, use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row")

            selected_rows = selection_event.selection.rows
            if selected_rows:
                candidate      = filtered_df.iloc[selected_rows[0]]
                contact_status = candidate.get('Contact_Status', 'Pending')
                is_verified    = "Verified" in str(contact_status)
                status_color   = "var(--accent-3)" if is_verified else "var(--accent)"
                status_icon    = "✅" if is_verified else "⚠️"
                ai_reasoning   = candidate.get('AI_Reasoning', 'Score generated based on clinical overlap.')

                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown('<span class="section-label">04 — Candidate Profile</span>', unsafe_allow_html=True)

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


# ─────────────────────────────────────────────────────────────
# ADMIN PANEL  — hidden route /?admin=1, password-protected
# Generates invite links directly against the live DB
# ─────────────────────────────────────────────────────────────

def render_admin():
    from auth import create_invite_token, get_db

    _, col, _ = st.columns([1, 1.5, 1])
    with col:
        st.markdown("## ⬡ CandidateIQ Admin")
        st.caption("INTERNAL — DO NOT SHARE THIS URL")
        st.divider()

        # Gate with admin password from secrets
        try:
            admin_password = st.secrets["ADMIN_PASSWORD"]
        except KeyError:
            st.error("ADMIN_PASSWORD not set in secrets.toml")
            return

        if not st.session_state.get("admin_authed"):
            pwd = st.text_input("Admin password", type="password", key="admin_pwd_input")
            if st.button("Unlock", type="primary"):
                if pwd == admin_password:
                    st.session_state["admin_authed"] = True
                    st.rerun()
                else:
                    st.error("Wrong password.")
            return

        # ── INVITE ────────────────────────────────────────
        st.markdown("### Generate Invite Link")
        email = st.text_input("User email", placeholder="client@company.com", key="admin_email")
        app_url = st.secrets.get("APP_URL", "https://your-app.streamlit.app").rstrip("/")

        if st.button("Generate Link", type="primary"):
            email = email.strip().lower()
            if not email or "@" not in email:
                st.error("Enter a valid email address.")
            else:
                token = create_invite_token(email)
                link  = f"{app_url}/?invite={token}"
                st.success(f"Invite created for **{email}**")
                st.code(link, language=None)
                st.caption("Link expires in 48 hours. Copy and send it to the user.")

        st.divider()

        # ── USER LIST ─────────────────────────────────────
        st.markdown("### Registered Users")
        with get_db() as conn:
            users = conn.execute(
                "SELECT username, email, created_at, is_active FROM users ORDER BY id DESC"
            ).fetchall()

        if not users:
            st.caption("No users registered yet.")
        else:
            for u in users:
                status = "✅ Active" if u["is_active"] else "🔴 Deactivated"
                st.markdown(f"**{u['username']}** · {u['email']} · {status} · joined {u['created_at'][:10]}")

        st.divider()

        # ── DEACTIVATE ────────────────────────────────────
        st.markdown("### Deactivate / Reactivate User")
        target = st.text_input("Username", key="admin_deact_username")
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("Deactivate", type="secondary"):
                with get_db() as conn:
                    c = conn.execute("UPDATE users SET is_active = 0 WHERE username = ?", (target.strip().lower(),))
                st.success(f"Deactivated '{target}'") if c.rowcount else st.error("User not found.")
                st.rerun()
        with col_b:
            if st.button("Reactivate", type="primary"):
                with get_db() as conn:
                    c = conn.execute("UPDATE users SET is_active = 1 WHERE username = ?", (target.strip().lower(),))
                st.success(f"Reactivated '{target}'") if c.rowcount else st.error("User not found.")
                st.rerun()


# ─────────────────────────────────────────────────────────────
# ROUTER  — no CSS, no imports, just route and render
# ─────────────────────────────────────────────────────────────
invite_token = st.query_params.get("invite", None)
is_admin     = st.query_params.get("admin", None) == "1"

if is_admin:
    render_admin()
elif invite_token:
    render_signup(invite_token)
elif is_logged_in(st.session_state):
    render_app()
else:
    render_login()