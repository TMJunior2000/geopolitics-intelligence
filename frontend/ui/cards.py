import streamlit as st
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape

# --- CONFIGURAZIONE PERCORSI E JINJA ---
CURRENT_DIR = Path(__file__).parent.resolve()
# Risaliamo per trovare la cartella templates corretta
PROJECT_ROOT = CURRENT_DIR.parent.parent 
TEMPLATES_DIR = PROJECT_ROOT / "frontend" / "assets" / "templates"

# Setup Ambiente Jinja Sicuro (Protezione XSS)
# Se la cartella non esiste, evitiamo crash immediati, gestiremo l'errore al render
try:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(['html', 'xml']) # <-- FONDAMENTALE PER SICUREZZA
    )
except Exception:
    env = None

def _get_badge_class(rec):
    """Logica pura Python: decide la classe CSS in base al valore."""
    if not rec:
        return "badge-style"
        
    rec_upper = str(rec).strip().upper()
    cls_map = {
        "LONG": "badge-long",
        "SHORT": "badge-short",
        "WATCH": "badge-watch"
    }
    return cls_map.get(rec_upper, "badge-style")

def _safe_render_template(template_name, **kwargs):
    """Wrapper sicuro per renderizzare template o fallire con grazia."""
    if env is None:
        return ""
    
    try:
        template = env.get_template(template_name)
        return template.render(**kwargs)
    except Exception as e:
        # In sviluppo mostra l'errore, in prod potresti volerlo nascondere
        return f""
    
def _render_single_card(row):
    # --- SETUP DATI ---
    sentiment = str(row.get('sentiment', 'NEUTRAL')).upper()
    recommendation = str(row.get('recommendation', 'WATCH')).upper()
    style_type = row.get('channel_style', 'N.D.').upper()
    
    # Mapping per le classi CSS dei tuoi badge
    rec_class = _get_badge_class(recommendation) # Usa la tua funzione esistente
    
    # Colore bordo dinamico (basato sulla fonte)
    channel_name = row.get('source_name', '')
    accent_color = "#34495e"
    if "investire biz" in channel_name.lower(): accent_color = "#2ecc71"
    elif "marketmind" in channel_name.lower(): accent_color = "#95a5a6"

    # Formattazione Data
    import pandas as pd
    try:
        display_date = pd.to_datetime(row.get('published_at')).strftime("%d %b %Y")
    except:
        display_date = "N.D."

    # --- RENDERING ---
    with st.container(border=True):
        # Header: Ticker + Data con stile Space Grotesk (dal tuo CSS)
        st.markdown(f"""
            <div style="border-left: 4px solid {accent_color}; padding-left: 12px; margin-bottom: 15px;">
                <div style="display: flex; justify-content: space-between; align-items: baseline;">
                    <h2 style="margin: 0; font-family: 'Space Grotesk', sans-serif;">{row.get('asset_ticker')}</h2>
                    <span style="font-size: 0.8rem; color: #888;">{display_date}</span>
                </div>
                <div class="badge badge-style" style="margin-top: 5px;"># {style_type}</div>
            </div>
        """, unsafe_allow_html=True)

        # La Summary Card (Sintesi Analisi)
        st.info(row.get('summary_card', 'No summary available.'))

        # Box Tecnico con i Badge (Sentiment e Rec)
        # Usiamo le tue classi .badge e .badge-long/short/watch
        st.markdown(f"""
            <div style="display: flex; gap: 8px; margin-bottom: 15px;">
                <div class="badge badge-style" style="background: transparent; border: 1px solid #444;">{sentiment}</div>
                <div class="badge {rec_class}">{recommendation}</div>
            </div>
        """, unsafe_allow_html=True)

        # Bottone "Dettagli" (Prende lo stile .stButton > button dal tuo CSS)
        if st.button("✨ KEY DRIVERS", key=f"btn_{row['id']}", use_container_width=True):
            _show_drivers_modal(row)

@st.dialog("🎯 Key Drivers")
def _show_drivers_modal(row):
    st.subheader(f"Insight: {row.get('asset_ticker')}")
    
    # Qui usiamo la tua classe .tech-box per i drivers
    drivers = row.get('key_drivers')
    if drivers and isinstance(drivers, list):
        for d in drivers:
            st.markdown(f"""
                <div class="tech-box" style="margin-bottom: 8px; padding: 10px;">
                    <div class="tech-row">
                        <span class="tech-val">⚡ {d}</span>
                    </div>
                </div>
            """, unsafe_allow_html=True)
    else:
        st.write("Nessun driver disponibile.")

def render_grid(df, assets_to_show):
    """Funzione principale chiamata dalla dashboard"""
    if df.empty:
        return

    # Ordinamento sicuro
    if 'published_at' in df.columns:
        df = df.sort_values(by='published_at', ascending=False)
    
    for asset in assets_to_show:
        asset_df = df[df['asset_ticker'] == asset]
        if asset_df.empty: continue
        
        st.markdown(f"### 💎 {asset}")
        st.markdown("---")
        
        cols = st.columns(3)
        for idx, (_, row) in enumerate(asset_df.iterrows()):
            with cols[idx % 3]:
                _render_single_card(row)
        
        st.markdown("<br>", unsafe_allow_html=True)