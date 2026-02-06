import streamlit as st
from pathlib import Path

# Calcola i percorsi assoluti basandosi sulla posizione di QUESTO file
# Struttura assunta: frontend/ui/styles.py -> risale a root -> scende a frontend/assets
CURRENT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = CURRENT_DIR.parent.parent  # Adjust dependent on where styles.py lives
ASSETS_DIR = PROJECT_ROOT / "frontend"

def load_css(css_filename="style.css"):
    """
    Legge un file CSS dalla cartella assets e lo inietta in Streamlit.
    Usa Pathlib per garantire che funzioni indipendentemente dalla Working Directory.
    """
    css_path = ASSETS_DIR / css_filename

    if not css_path.exists():
        # Fallback sicuro: cerca relativo allo script se la struttura è diversa
        css_path = Path("frontend/assets") / css_filename
        if not css_path.exists():
            st.error(f"⚠️ Errore critico: File CSS non trovato in {css_path}")
            return

    try:
        with open(css_path, "r", encoding="utf-8") as f:
            css_content = f.read()
        
        st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Errore caricamento stili: {e}")