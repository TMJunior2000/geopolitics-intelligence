import plotly.graph_objects as go
import pandas as pd
from datetime import timedelta

def render_interactive_chart(df, ticker, timeframe="H4", fvgs=[], levels=None):
    """
    Renderizza un grafico candlestick stile TradingView con:
    - FVG dual-layer
    - Livelli AI
    - Crosshair (Cursore) professionale con etichetta valore
    - Linea Prezzo Attuale (Last Price) dinamica
    """
    if df.empty: 
        return None, None
    
    # ---------------------------------------------------------
    # 1. PREPARAZIONE DATI
    # ---------------------------------------------------------
    df = df.copy()
    df['time'] = pd.to_datetime(df['time'])
    
    freq_map = {"H4": "4h", "M15": "15min"}
    round_rule = freq_map.get(timeframe, "4h")
    
    df['time'] = df['time'].dt.floor(round_rule)
    df = df.drop_duplicates(subset=['time'], keep='last')
    df = df.sort_values('time')

    # Dati ultima candela per la "Linea Prezzo Attuale"
    last_candle = df.iloc[-1]
    current_price = last_candle['close']
    is_last_bullish = last_candle['close'] >= last_candle['open']
    last_price_color = '#089981' if is_last_bullish else '#F23645'

    # ---------------------------------------------------------
    # 2. CONFIGURAZIONE RANGEBREAKS (Weekend/Feste)
    # ---------------------------------------------------------
    breaks_config = []
    is_crypto = any(x in ticker for x in ["BTC", "ETH", "SOL", "XRP"])
    if not is_crypto:
        breaks_config.append(dict(bounds=["sat", "mon"]))

    manual_holidays = ["2024-12-25", "2025-01-01", "2025-12-25", "2026-01-01"]
    if manual_holidays:
        breaks_config.append(dict(values=manual_holidays))

    # ---------------------------------------------------------
    # 3. COSTRUZIONE GRAFICO
    # ---------------------------------------------------------
    fig = go.Figure()

    # Candlestick Chart
    fig.add_trace(go.Candlestick(
        x=df['time'],
        open=df['open'], high=df['high'], low=df['low'], close=df['close'],
        increasing_line_color='#089981', increasing_fillcolor='rgba(8, 153, 129, 0.5)',
        decreasing_line_color='#F23645', decreasing_fillcolor='rgba(242, 54, 69, 0.5)',
        line_width=1,
        name=ticker,
        hoverinfo='x+y+name' # Mostra info pulite al passaggio
    ))

    # ---------------------------------------------------------
    # 4. DISEGNO FVG (Fair Value Gaps)
    # ---------------------------------------------------------
    for fvg in fvgs:
        is_bull = fvg['type'] == 'BULLISH'
        active_color = "8, 153, 129" if is_bull else "242, 54, 69"
        mitigated_color = "148, 163, 184"
        
        x0, x1 = fvg['start_time'], fvg['end_time']
        top, bottom = fvg['top'], fvg['bottom']
        mit_level = fvg.get('mitigation_level')
        pct = fvg.get('pct_filled', 0)

        # Logica rettangoli (Attivo vs Mitigato)
        if mit_level is not None and 0 < pct < 100:
            # Parte mitigata (grigio) + Parte attiva (colorata)
            if is_bull:
                fig.add_shape(type="rect", x0=x0, x1=x1, y0=mit_level, y1=top,
                            fillcolor=f"rgba({mitigated_color}, 0.15)", line_width=0, layer="below")
                fig.add_shape(type="rect", x0=x0, x1=x1, y0=bottom, y1=mit_level,
                            fillcolor=f"rgba({active_color}, 0.25)", 
                            line=dict(color=f"rgba({active_color}, 0.5)", width=1, dash="dot"), layer="below")
            else:
                fig.add_shape(type="rect", x0=x0, x1=x1, y0=bottom, y1=mit_level,
                            fillcolor=f"rgba({mitigated_color}, 0.15)", line_width=0, layer="below")
                fig.add_shape(type="rect", x0=x0, x1=x1, y0=mit_level, y1=top,
                            fillcolor=f"rgba({active_color}, 0.25)", 
                            line=dict(color=f"rgba({active_color}, 0.5)", width=1, dash="dot"), layer="below")
            
            # --- QUESTA È LA PARTE CHE MANCAVA PER VEDERE IL NUMERO ---
            fig.add_annotation(
                x=x1, 
                y=(top+bottom)/2, 
                text=f"{pct:.0f}%", 
                showarrow=False,
                font=dict(size=9, color="rgba(255,255,255,0.6)"), 
                xanchor="left"
            )

        elif pct <= 0:
            # Tutto attivo
            fig.add_shape(type="rect", x0=x0, x1=x1, y0=bottom, y1=top,
                        fillcolor=f"rgba({active_color}, 0.25)", 
                        line=dict(color=f"rgba({active_color}, 0.5)", width=1, dash="dot"), layer="below")

    # ---------------------------------------------------------
    # 5. LIVELLI AI (Entry/Stop)
    # ---------------------------------------------------------
    if levels:
        if levels.get('entry'):
            fig.add_hline(y=levels['entry'], line=dict(color="#2962FF", width=1, dash="dash"), 
                         annotation_text="AI ENTRY", annotation_position="top left", annotation_font_color="#2962FF")
        if levels.get('stop'):
            fig.add_hline(y=levels['stop'], line=dict(color="#F23645", width=1, dash="dot"), 
                         annotation_text="AI STOP", annotation_position="bottom left", annotation_font_color="#F23645")

    # ---------------------------------------------------------
    # 6. NUOVA FEATURE: LINEA PREZZO ATTUALE (LAST PRICE)
    # ---------------------------------------------------------
    # Aggiunge una linea orizzontale tratteggiata che segna il prezzo corrente
    fig.add_hline(
        y=current_price,
        line_dash="dot",
        line_color=last_price_color,
        line_width=1,
        opacity=0.8,
        annotation_text=f"CURRENT: {current_price:.2f}",
        annotation_position="right", # Lo mette sull'asse Y
        annotation_font=dict(color="white", size=10),
        annotation_bgcolor=last_price_color,
    )

    # ---------------------------------------------------------
    # 7. LAYOUT & CURSORI (CROSSHAIR)
    # ---------------------------------------------------------
    fig.update_layout(
        title=dict(
            text=f"<b>{ticker}</b> • <span style='color:#F59E0B'>{timeframe}</span>",
            font=dict(size=14, color="#94A3B8"), x=0.01, y=0.98
        ),
        template="plotly_dark", 
        plot_bgcolor='rgba(11, 15, 25, 0)', # Sfondo trasparente/scuro
        paper_bgcolor='rgba(0,0,0,0)', 
        margin=dict(l=10, r=60, t=40, b=20), # r=60 lascia spazio per etichette asse Y
        height=550, 
        dragmode='pan',
        hovermode='closest',
        spikedistance=-1,
        hoverdistance=0,

        
        hoverlabel=dict(
            bgcolor="#111827",
            font_size=11,
            font_family="monospace",
            bordercolor="#374151"
        ),

        # ASSE X (TEMPO)
        xaxis=dict(
            rangebreaks=breaks_config,
            rangeslider_visible=False,
            showgrid=True,
            gridcolor='rgba(255,255,255,0.05)',
            tickformat="%d/%m\n%H:%M",

            showspikes=True,
            spikemode='across',
            spikesnap='cursor',
            spikecolor="rgba(255,255,255,0.2)",
            spikethickness=1,
            spikedash="solid",
        ),

        # ASSE Y (PREZZO)
        yaxis=dict(
            side="right",
            showgrid=True,
            gridcolor='rgba(255,255,255,0.05)',
            tickformat=".2f",
            autorange=True,

            showspikes=True,
            spikemode='across',
            spikesnap='cursor',
            spikecolor="#666666",
            spikethickness=1,
            spikedash="longdash",

            showline=False,
            showticklabels=True,
        )
    )
    
    # Questo trucco forza Plotly a mostrare l'etichetta del prezzo sull'asse Y (Crosshair Label)
    fig.update_yaxes(showspikes=True, spikethickness=1, spikecolor="#666666", spikedash="longdash")

    config = {
        'scrollZoom': True, 
        'displayModeBar': False, 
        'staticPlot': False, 
        'responsive': True,
        'modeBarButtonsToRemove': ['lasso2d', 'select2d']
    }

    return fig, config