import html

def _generate_single_card(row):
    """Genera una singola card con dimensioni fisse per tutte le sezioni"""
    
    # Escape dati per sicurezza
    style = html.escape(str(row.get('channel_style', 'Fondamentale')))
    rec = str(row.get('recommendation', 'WATCH')).upper()
    ticker = html.escape(str(row.get('asset_ticker', 'ASSET')))
    name = html.escape(str(row.get('asset_name', '')))[:50]  # Limita lunghezza
    summary = html.escape(str(row.get('summary_card', 'Nessun dettaglio disponibile.')))
    
    # CSS Classes per recommendation
    rec_cls = f"rec-{rec.lower()}"
    
    # Drivers list (max 4 items per limitare altezza)
    drivers = row.get('key_drivers', [])[:4]  # Limita a 4
    drivers_html = "".join([f"<li>{html.escape(str(d)[:80])}</li>" for d in drivers])
    
    # Se non ci sono drivers, metti placeholder
    if not drivers_html:
        drivers_html = "<li>No specific drivers available</li>"
    
    # Technical Levels Box (mostra solo se dati esistono)
    levels_html = ""
    if any([row.get('entry_zone'), row.get('target_price'), row.get('stop_invalidation')]):
        entry = html.escape(str(row.get('entry_zone') or 'N/A'))
        target = html.escape(str(row.get('target_price') or 'N/A'))
        stop = html.escape(str(row.get('stop_invalidation') or 'N/A'))
        horizon = html.escape(str(row.get('time_horizon') or 'N/A'))
        
        levels_html = f"""
        <div class="levels-box">
            <div class="level-item">
                ENTRY
                <span class="level-val">{entry}</span>
            </div>
            <div class="level-item">
                TARGET
                <span class="level-val">{target}</span>
            </div>
            <div class="level-item">
                STOP
                <span class="level-val">{stop}</span>
            </div>
            <div class="level-item">
                HORIZON
                <span class="level-val">{horizon}</span>
            </div>
        </div>
        """
    
    # URL video (escape)
    video_url = html.escape(str(row.get('video_url', '#')))
    
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

        <a href="{video_url}" target="_blank" class="cta-button">
            👁️ ANALYSIS SOURCE
        </a>
    </div>
    """


def generate_grid_html(df, assets_to_show):
    """Genera l'HTML completo con tutte le card organizzate per asset"""
    
    html_out = []
    
    # Ordiniamo per data decrescente
    df = df.sort_values(by='published_at', ascending=False)
    
    for asset in assets_to_show:
        asset_df = df[df['asset_ticker'] == asset]
        if asset_df.empty: 
            continue
        
        # Header asset con emoji
        asset_emoji = {
            'BTC': '₿', 'ETH': '⟠', 'SPX': '📈',
            'GOLD': '🥇', 'OIL': '🛢️', 'EUR': '💶',
            'USD': '💵', 'GBP': '💷'
        }.get(asset, '💎')
        
        html_out.append(f'<div class="asset-header">{asset_emoji} {html.escape(asset)}</div>')
        html_out.append('<div class="cards-grid">')
        
        # Genera card per ogni insight
        for _, row in asset_df.iterrows():
            html_out.append(_generate_single_card(row))
        
        html_out.append('</div>')
    
    return "".join(html_out)