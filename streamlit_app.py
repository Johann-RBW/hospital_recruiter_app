import streamlit as st
import pandas as pd
import json
from groq import Groq

# 1. Page Configuration & Header
st.set_page_config(page_title="Candidate Finder", page_icon="🏥", layout="wide")

st.title("🏥 Healthcare Candidate Finder")
st.write("Paste a job description below to automatically extract key requirements and find matching candidates.")

# 2. Initialize Groq Client via Streamlit Secrets
try:
    # Streamlit Cloud looks here for environment variables
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except KeyError:
    st.error("GROQ_API_KEY is missing. Please add it to your Streamlit Cloud Secrets.")
    st.stop()

# 3. Input Area
job_description = st.text_area("Paste Job Description", height=200, placeholder="Enter the full job description here...")

# 4. Action Button & API Call
if st.button("Search", type="primary"):
    if not job_description.strip():
        st.warning("Please paste a job description before searching.")
    else:
        with st.spinner("Extracting job details with Groq..."):
            
            # Prompt engineered to force a specific JSON structure
            prompt = f"""
            Analyze the following job description and extract the key details. 
            You must return ONLY a valid JSON object with the exact following keys:
            - "job_title" (string)
            - "required_skills" (list of strings)
            - "location" (string)
            - "years_of_experience" (string or number)
            
            Job Description:
            {job_description}
            """
            
            try:
                # Call Groq API
                response = client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt}],
                    model="llama3-8b-8192",
                    response_format={"type": "json_object"},
                    temperature=0
                )
                
                # Parse the JSON string returned by Groq into a Python dictionary
                extracted_data = json.loads(response.choices[0].message.content)
                
                st.success("Extraction successful!")
                
                # Display the extracted JSON so we can verify it works
                st.subheader("Extracted Job Requirements")
                st.json(extracted_data)
                
                # --- Keep the Stage 1 Dummy Data Table below for UI continuity ---
                st.subheader("Candidate Results (Dummy Data)")
                
                dummy_data = {
                    "Name": ["Sarah Jenkins", "Michael Chang", "Elena Rodriguez", "David Smith", "Jessica Barnes"],
                    "Current Job Title": ["Registered Nurse", "Clinical Pathologist", "Medical Technologist", "ICU Nurse", "Healthcare Administrator"],
                    "Company": ["Mercy General Hospital", "Lakeside Health", "City Medical Center", "Veterans Affairs", "County General"],
                    "Location": ["Charlotte, NC", "Charlotte, NC", "Raleigh, NC", "Columbia, SC", "Charlotte, NC"],
                    "Email": ["s.jenkins@email.com", "mchang_med@email.com", "elena.r@email.com", "dsmith_icu@email.com", "jbarnes.admin@email.com"]
                }
                
                df = pd.DataFrame(dummy_data)
                st.dataframe(df, use_container_width=True, hide_index=True)
                
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(label="Download Results as CSV", data=csv, file_name='candidate_results.csv', mime='text/csv')

            except Exception as e:
                st.error(f"An error occurred during extraction: {e}")