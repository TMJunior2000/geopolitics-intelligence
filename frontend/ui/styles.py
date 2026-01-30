import streamlit as st
import os

def load_css(file_path="frontend/assets/style.css"):
    """
    Legge un file CSS esterno e lo inietta in Streamlit.
    """
    if not os.path.exists(file_path):
        st.error(f"File CSS non trovato: {file_path}")
        return ""
    
    with open(file_path, "r") as f:
        css_content = f.read()
        
    st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)