import html

def _generate_single_card(row):
    style = row.get('channel_style', 'Fondamentale')
    rec = str(row.get('recommendation', 'WATCH')).upper()
    ticker = html.escape(str(row.get('asset_ticker', 'ASSET')))
    name = html.escape(str(row.get('asset_name', '')))
    summary = html.escape(str(row.get('summary_card', 'Nessun dettaglio disponibile.')))
    
    # CSS Classes
    rec_cls = f"rec-{rec.lower()}"
    
    # Drivers list conversion
    drivers = row.get('key_drivers', [])
    drivers_html = "".join([f"<li>{html.escape(d)}</li>" for d in drivers])

    # Technical Levels Box (show only if data exists)
    levels_html = ""
    if any([row.get('entry_zone'), row.get('target_price'), row.get('stop_invalidation')]):
        levels_html = f"""
        <div class="levels-box">
            <div class="level-item">ENTRY <span class="level-val">{row.get('entry_zone') or 'N/A'}</span></div>
            <div class="level-item">TARGET <span class="level-val">{row.get('target_price') or 'N/A'}</span></div>
            <div class="level-item">STOP <span class="level-val">{row.get('stop_invalidation') or 'N/A'}</span></div>
            <div class="level-item">HORIZON <span class="level-val">{row.get('time_horizon') or 'N/A'}</span></div>
        </div>
        """

    return f"""
    <div class="modern-card">
        <div class="card-header">
            <span class="tag tag-style">{style}</span>
            <span class="tag {rec_cls}">{rec}</span>
        </div>
        <div class="card-ticker">{ticker}</div>
        <div class="card-name">{name}</div>
        
        <div class="summary-text">{summary}</div>
        
        <ul class="drivers-list">
            {drivers_html}
        </ul>

        {levels_html}

        <a href="{row.get('video_url', '#')}" target="_blank" class="cta-button">ANALYSIS SOURCE</a>
    </div>
    """

def generate_grid_html(df, assets_to_show):
    html_out = []
    # Ordiniamo per data decrescente
    df = df.sort_values(by='published_at', ascending=False)
    
    for asset in assets_to_show:
        asset_df = df[df['asset_ticker'] == asset]
        if asset_df.empty: continue
        
        html_out.append(f'<div class="asset-header">💎 {asset}</div>')
        html_out.append('<div class="cards-grid">')
        for _, row in asset_df.iterrows():
            html_out.append(_generate_single_card(row))
        html_out.append('</div>')
    return "".join(html_out)