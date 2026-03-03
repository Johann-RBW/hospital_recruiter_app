import streamlit as st
import pandas as pd
import json
import requests
from groq import Groq

# 1. Page Configuration & Header
st.set_page_config(page_title="Candidate Finder", page_icon="🏥", layout="wide")

st.title("🏥 Healthcare Candidate Finder")
st.write("Paste a job description below to automatically extract key requirements and find matching candidates.")

# 2. Initialize API Keys via Streamlit Secrets
try:
    groq_client = Groq(api_key=st.secrets["GROQ_API_KEY"])
    apollo_api_key = st.secrets["APOLLO_API_KEY"]
except KeyError as e:
    st.error(f"Missing Secret: {e}. Please add it to your .streamlit/secrets.toml file.")
    st.stop()

# 3. Input Area
job_description = st.text_area("Paste Job Description", height=200, placeholder="Enter the full job description here...")

# 4. Action Button & API Call
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

        # --- APOLLO API INTEGRATION ---
        with st.spinner("Searching Apollo.io for matching candidates..."):
            try:
                url = "https://api.apollo.io/api/v1/mixed_people/search"
                headers = {
                    "Cache-Control": "no-cache",
                    "Content-Type": "application/json",
                    "x-api-key": apollo_api_key
                }
                
                # Build the search payload from the Groq data
                payload = {
                    "per_page": 10
                }
                
                # We map the extracted values to Apollo's expected query arrays
                if extracted_data.get("location"):
                    payload["person_locations"] = [extracted_data["location"]]
                
                if extracted_data.get("job_title"):
                    payload["person_titles"] = [extracted_data["job_title"]]
                
                # Send request to Apollo
                apollo_response = requests.post(url, headers=headers, json=payload)
                apollo_response.raise_for_status() 
                apollo_data = apollo_response.json()
                
                people = apollo_data.get("people", [])
                
                if not people:
                    st.warning("No candidates found matching those specific requirements in Apollo.")
                else:
                    st.success("Candidates found!")
                    st.subheader(f"Real Candidate Results ({len(people)})")
                    
                    # Parse Apollo response into our table structure
                    formatted_results = []
                    for person in people:
                        
                        # Handle potential missing data safely
                        first_name = person.get("first_name", "")
                        last_name = person.get("last_name", "")
                        org = person.get("organization") or {}
                        city = person.get("city") or ""
                        state = person.get("state") or ""
                        
                        location_str = f"{city}, {state}".strip(", ")
                        if not location_str:
                            location_str = "N/A"
                            
                        formatted_results.append({
                            "Name": f"{first_name} {last_name}".strip() or "N/A",
                            "Current Job Title": person.get("title", "N/A"),
                            "Company": org.get("name", "N/A"),
                            "Location": location_str,
                            "Email": person.get("email", "Not Provided")
                        })
                    
                    # Display real data and setup CSV export
                    df = pd.DataFrame(formatted_results)
                    st.dataframe(df, use_container_width=True, hide_index=True)
                    
                    csv = df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="Download Results as CSV",
                        data=csv,
                        file_name='apollo_candidates.csv',
                        mime='text/csv'
                    )

            except requests.exceptions.RequestException as e:
                st.error(f"An error occurred communicating with Apollo API: {e}")