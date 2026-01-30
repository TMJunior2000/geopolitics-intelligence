import streamlit as st

def _get_badge_html(rec):
    rec = rec.upper()
    cls_map = {
        "LONG": "badge-long",
        "SHORT": "badge-short",
        "WATCH": "badge-watch"
    }
    css_class = cls_map.get(rec, "badge-style")
    return f'<span class="badge {css_class}">{rec}</span>'

def _render_single_card(row):
    """Renderizza una singola card usando componenti nativi Streamlit"""
    
    # Estrazione dati
    style = row.get('channel_style', 'Fondamentale')
    rec = str(row.get('recommendation', 'WATCH')).upper()
    ticker = row.get('asset_ticker', 'ASSET')
    name = row.get('asset_name', '')
    summary = row.get('summary_card', 'Nessun dettaglio disponibile.')
    drivers = row.get('key_drivers', [])
    video_url = row.get('video_url', '')

    # Container Card con bordo (nativo Streamlit)
    with st.container(border=True):
        
        # 1. Header: Badges
        badge_html = f"""
        <div style="margin-bottom: 10px;">
            <span class="badge badge-style">{style}</span>
            {_get_badge_html(rec)}
        </div>
        """
        st.markdown(badge_html, unsafe_allow_html=True)

        # 2. Ticker e Nome
        st.markdown(f"### {ticker}")
        if name:
            st.caption(name)
        
        # 3. Summary
        # Usiamo un divisore visivo leggero
        st.markdown("---")
        st.markdown(f"**Analisi:** {summary}")

        # 4. Drivers
        if drivers:
            st.markdown("**Key Drivers:**")
            for driver in drivers:
                st.markdown(f"- {driver}")

        # 5. Technical Levels (Renderizzato solo se esistono dati)
        entry = row.get('entry_zone')
        target = row.get('target_price')
        stop = row.get('stop_invalidation')
        horizon = row.get('time_horizon')

        if any([entry, target, stop]):
            st.markdown(f"""
            <div class="tech-box">
                <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                    <div><div class="tech-label">ENTRY</div><div class="tech-val">{entry or '-'}</div></div>
                    <div><div class="tech-label">TARGET</div><div class="tech-val">{target or '-'}</div></div>
                </div>
                <div style="display: flex; justify-content: space-between;">
                    <div><div class="tech-label">STOP</div><div class="tech-val">{stop or '-'}</div></div>
                    <div><div class="tech-label">HORIZON</div><div class="tech-val">{horizon or '-'}</div></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        # 6. Button
        if video_url and video_url != '#':
            st.markdown("") # Spacer
            st.link_button("📺 VEDI ANALISI COMPLETA", video_url, use_container_width=True)


def render_grid(df, assets_to_show):
    """
    Gestisce la griglia responsiva nativa.
    """
    # Ordiniamo per data decrescente
    if not df.empty and 'published_at' in df.columns:
        df = df.sort_values(by='published_at', ascending=False)
    
    for asset in assets_to_show:
        asset_df = df[df['asset_ticker'] == asset]
        if asset_df.empty:
            continue
        
        # Titolo Sezione Asset
        st.markdown(f"### 💎 {asset}")
        st.markdown("---")
        
        # Griglia 3 colonne
        cols = st.columns(3)
        
        for idx, (_, row) in enumerate(asset_df.iterrows()):
            # Modulo 3 per distribuire le card nelle colonne ciclicamente
            with cols[idx % 3]:
                _render_single_card(row)
        
        st.markdown("<br>", unsafe_allow_html=True)