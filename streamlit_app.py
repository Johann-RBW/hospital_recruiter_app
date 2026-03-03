import streamlit as st
import pandas as pd
import json
import os
from groq import Groq

# 1. Page Configuration & Header
st.set_page_config(page_title="Candidate Finder", page_icon="🏥", layout="wide")

st.title("🏥 Healthcare Candidate Finder")
st.write("Paste a job description below to automatically extract key requirements and find matching candidates.")

# 2. Initialize Groq Client via Streamlit Secrets
try:
    groq_client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except KeyError:
    st.error("GROQ_API_KEY is missing. Please add it to your .streamlit/secrets.toml file.")
    st.stop()

# 3. Input Area
job_description = st.text_area("Paste Job Description", height=200, placeholder="Enter the full job description here...")

# 4. Action Button & Core Logic
if st.button("Search", type="primary"):
    if not job_description.strip():
        st.warning("Please paste a job description before searching.")
    else:
        # --- GROQ EXTRACTION ---
        with st.spinner("Extracting job details with Groq..."):
            prompt = f"""
            You are an expert healthcare recruiter. Analyze the following job description and extract the key details. 
            
            CRITICAL INSTRUCTION: Do not just look for explicit keywords. You must deduce and extrapolate required skills, certifications, and experience levels from the context of the daily responsibilities, patient care duties, and tools mentioned in the text.
            
            You must return ONLY a valid JSON object with the exact following keys:
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
                    temperature=0
                )
                
                extracted_data = json.loads(response.choices[0].message.content)
                
                with st.expander("View Extracted Job Requirements (JSON)"):
                    st.json(extracted_data)
                
            except Exception as e:
                st.error(f"An error occurred during Groq extraction: {e}")
                st.stop()

        # --- LOCAL MOCK DATABASE SEARCH ---
        with st.spinner("Searching local candidate database..."):
            try:
                # 1. Load the CSV
                file_path = "candidates.csv"
                if not os.path.exists(file_path):
                    st.error(f"Could not find '{file_path}'. Make sure it is saved in the root directory.")
                    st.stop()
                    
                df = pd.read_csv(file_path)
                filtered_df = df.copy()
                
                # 2. Resilient Title Matching
                extracted_title = extracted_data.get("job_title")
                if extracted_title and str(extracted_title).lower() != "null":
                    # Grab just the first two words to catch "Patient Care" out of "Patient Care Associate (PCA)"
                    core_title = " ".join(str(extracted_title).replace("(", "").replace(")", "").split()[:2])
                    
                    # regex=False fixes the warning, core_title makes it a fuzzy match
                    filtered_df = filtered_df[filtered_df['Job Title'].str.contains(core_title, case=False, na=False, regex=False)]
                
                # 3. Resilient Location Matching (with fallback)
                extracted_location = extracted_data.get("location")
                location_matched_df = filtered_df.copy()
                
                if extracted_location and str(extracted_location).lower() != "null":
                    city = extracted_location.split(',')[0].strip()
                    location_matched_df = filtered_df[filtered_df['Location'].str.contains(city, case=False, na=False, regex=False)]
                
                # Fallback: If no one is in that exact city, show the wider region matches instead of an empty table
                if location_matched_df.empty and not filtered_df.empty:
                    st.info(f"No exact matches found in {city}. Showing {len(filtered_df)} regional candidates with matching titles.")
                else:
                    filtered_df = location_matched_df
                
                # 4. Display Results
                if filtered_df.empty:
                    st.warning("No candidates found matching those specific requirements in the database.")
                else:
                    # We already showed the st.info fallback message above if location didn't match
                    st.subheader(f"Candidate Results ({len(filtered_df)})")
                    
                    # 1. Select the columns using the ORIGINAL names first
                    display_cols = ["Name", "Job Title", "Company", "Location", "Email", "Phone"]
                    display_df = filtered_df[display_cols]
                    
                    # 2. Rename the column AFTER selecting it
                    display_df = display_df.rename(columns={"Job Title": "Current Job Title"})
                    
                    st.dataframe(display_df, use_container_width=True, hide_index=True)
                    
                    csv = display_df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="Download Results as CSV",
                        data=csv,
                        file_name='matched_candidates.csv',
                        mime='text/csv'
                    )

            except Exception as e:
                st.error(f"An error occurred while searching the database: {e}")