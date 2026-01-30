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
    # 1. Gestione Colore in base al canale (Tabella sources)
    # Mapping basato sui nomi che hai nel DB
    channel_name = row.get('source_name', '')
    
    # Colore default (Blu scuro)
    accent_color = "#34495e" 
    if "investire biz - analisi" in channel_name.lower():
        accent_color = "#2ecc71"  # Verde
    elif "marketmind" in channel_name.lower():
        accent_color = "#95a5a6"  # Grigio

    # 2. Formattazione Data sicura
    raw_date = row.get('published_at')
    display_date = "Data N.D."

    if raw_date:
        try:
            # Se è già un oggetto Timestamp/datetime (Pandas/Supabase lo converte spesso)
            if hasattr(raw_date, 'strftime'):
                display_date = raw_date.strftime("%d/%m/%Y")
            else:
                # Se arriva come stringa "2026-01-29 09:41:09+00"
                # Trasformiamo la stringa in oggetto data per formattarla meglio
                import pandas as pd
                temp_date = pd.to_datetime(raw_date)
                display_date = temp_date.strftime("%d/%m/%Y")
        except Exception:
            # Fallback estremo: prendiamo i primi 10 caratteri se tutto fallisce
            display_date = str(raw_date)[:10]

    with st.container(border=True):
        # Header con Colore e Data
        st.markdown(f"""
            <div style="border-left: 5px solid {accent_color}; padding-left: 10px; margin-bottom: 10px;">
                <span style="color: #888; font-size: 0.8rem;">📅 {display_date}</span>
                <h3 style="margin: 0;">{row.get('asset_ticker')}</h3>
                <small style="color: {accent_color}; font-weight: bold;">{channel_name}</small>
            </div>
        """, unsafe_allow_html=True)

        # Drivers compatti (HTML per rimuovere i margini eccessivi di Streamlit)
        drivers = row.get('key_drivers') or []
        if drivers:
            st.markdown("<p style='margin-bottom: 5px;'><b>Key Drivers:</b></p>", unsafe_allow_html=True)
            drivers_list = "".join([f"<li style='margin-bottom: 0px;'>{d}</li>" for d in drivers])
            st.markdown(f"<ul style='margin-top: 0px; padding-left: 20px; font-size: 0.9rem;'>{drivers_list}</ul>", unsafe_allow_html=True)

        # Bottone Leggi Tutto (Sostituisce il link video diretto)
        if st.button("🔍 DETTAGLI COMPLETI", key=f"details_{row['id']}", use_container_width=True):
            _show_full_analysis_modal(row)

@st.dialog("Dettaglio Analisi")
def _show_full_analysis_modal(row):
    st.subheader(f"{row['asset_ticker']} - {row.get('asset_name', '')}")
    st.info(f"Fonte: {row.get('source_name')} | Pubblicato il: {row.get('published_at')}")
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Sentiment", row.get('sentiment'))
    with col2:
        st.metric("Recommendation", row.get('recommendation'))

    st.markdown("### 📝 Analisi Completa")
    # Qui usiamo 'video_summary' che è il testo lungo della tabella intelligence_feed
    st.write(row.get('video_summary') or row.get('summary_card'))
    
    if row.get('video_url'):
        st.link_button("📺 Guarda Video Originale", row['video_url'])

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