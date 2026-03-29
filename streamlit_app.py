import streamlit as st
import sys

st.write(f"Python: {sys.version}")

try:
    from groq import Groq
    st.write("✅ groq OK")
except Exception as e:
    st.error(f"❌ groq: {e}")

try:
    from pdl_search import get_candidates_from_pdl
    st.write("✅ pdl_search OK")
except Exception as e:
    st.error(f"❌ pdl_search: {e}")

try:
    from auth import init_db
    init_db()
    st.write("✅ auth + db OK")
except Exception as e:
    st.error(f"❌ auth: {e}")

st.stop()