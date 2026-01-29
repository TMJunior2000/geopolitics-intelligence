import html

def _generate_single_card(row):
    sent = str(row.get('sentiment', 'NEUTRAL')).upper()
    tag_cls = "tag-bullish" if sent == "BULLISH" else "tag-bearish" if sent == "BEARISH" else "tag-neutral"
    
    return f"""
    <div class="modern-card">
        <div><span class="{tag_cls}">{sent}</span></div>
        <div class="card-title">{html.escape(str(row.get('video_title','')))}</div>
        <div class="card-text">{html.escape(str(row.get('ai_reasoning','')))}</div>
        <a href="{row.get('video_url', '#')}" target="_blank" class="cta-button">VIEW ANALYSIS</a>
    </div>
    """

def generate_grid_html(df, assets_to_show):
    html_out = []
    for asset in assets_to_show:
        asset_df = df[df['asset_ticker'] == asset]
        if asset_df.empty: continue
        
        html_out.append(f'<div class="asset-header">💎 {asset}</div>')
        html_out.append('<div class="cards-grid">')
        for _, row in asset_df.iterrows():
            html_out.append(_generate_single_card(row))
        html_out.append('</div>')
    return "".join(html_out)