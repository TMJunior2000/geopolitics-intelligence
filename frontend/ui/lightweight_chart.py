import streamlit as st
import json
import pandas as pd
import numpy as np
import streamlit.components.v1 as components

def render_lightweight_chart(df: pd.DataFrame, ticker: str, fvgs: list | None = None):
    """
    Renderizza FVG come SFONDO SOLIDO.
    CORREZIONE: Estende FVG aperti fino all'ultima candela.
    CORREZIONE: Garantisce visibilità rettangoli 0%.
    """
    if df is None or df.empty:
        st.info(f"Nessun dato per {ticker}")
        return

    # --- 1. PREPARAZIONE DATI PREZZO ---
    df_plot = df.copy()
    df_plot["time"] = pd.to_datetime(df_plot["time"], errors="coerce")
    df_plot = df_plot.dropna(subset=["time"]).sort_values("time")
    df_plot = df_plot.drop_duplicates(subset=["time"], keep='last')

    all_times_array = df_plot['time'].astype(np.int64) // 10**9
    all_times_list = all_times_array.tolist()
    
    ohlc_data = df_plot[['open', 'high', 'low', 'close']].copy()
    ohlc_data['time'] = all_times_array
    ohlc_data_json = json.dumps(ohlc_data.to_dict(orient='records'))
    
    safe_id = f"chart_{ticker.replace('.', '_').replace('/', '_').replace(':', '_')}"

    # --- 2. GENERAZIONE DATI FVG ---
    box_data_bull = []
    box_data_bear = []
    box_data_mitigated = []
    markers = []

    if fvgs:
        time_to_idx = {t: i for i, t in enumerate(all_times_list)}
        last_chart_idx = len(all_times_list) - 1 # Indice ultima candela visibile

        for fvg in fvgs:
            try:
                start_t = int(fvg['start_time'])
                end_t = int(fvg['end_time'])
                
                # --- CALCOLO PERCENTUALE ---
                pct = fvg.get('mitigated_pct', 0.0)
                if pct is None: pct = 0.0
                is_fully_mitigated = pct >= 99

                # --- 1. LOGICA DI ESTENSIONE (FIX MANCATA ESTENSIONE) ---
                start_idx = next((i for t, i in time_to_idx.items() if t >= start_t), 0)
                
                if is_fully_mitigated:
                    # Se è chiuso, si ferma dove è stato chiuso
                    end_idx = next((i for t, i in time_to_idx.items() if t >= end_t), last_chart_idx)
                else:
                    # SE È APERTO (< 99%), FORZIAMO ALLA FINE DEL GRAFICO
                    end_idx = last_chart_idx 
                
                # Evitiamo errori se gli indici sono invertiti
                if start_idx > end_idx: start_idx = end_idx

                # --- 2. LOGICA PREZZO (FIX RETTANGOLO INVISIBILE) ---
                raw_top = float(fvg['top'])
                raw_bottom = float(fvg['bottom'])
                # Garantiamo che top sia il massimo e bottom il minimo (fix altezza negativa)
                top = max(raw_top, raw_bottom)
                bottom = min(raw_top, raw_bottom)
                
                # Tipo FVG
                is_bullish = (fvg['type'].upper() == 'BULLISH')

                # --- MARKER (SOLO TESTO %) ---              
                markers.append({
                    'time': all_times_list[start_idx],
                    'position': 'belowBar' if is_bullish else 'aboveBar',
                    'color': '#64748B' if is_fully_mitigated else ('#2ECC71' if is_bullish else '#EF4444'),
                    'shape': 'circle',
                    'text': f"{pct:.0f}%", # Es. "0%", "3%"
                    'size': 0 # Nasconde pallino
                })

                # --- CREAZIONE RETTANGOLO (SFONDO) ---
                for i in range(start_idx, end_idx + 1):
                    t = all_times_list[i]
                    box_candle = {'time': t, 'open': top, 'high': top, 'low': bottom, 'close': bottom}

                    if is_fully_mitigated:
                        box_data_mitigated.append(box_candle)
                    elif is_bullish:
                        box_data_bull.append(box_candle)
                    else:
                        box_data_bear.append(box_candle)

            except Exception as e:
                # print(f"Errore FVG: {e}") 
                continue

    def clean_and_dump(data):
        if not data: return "[]"
        unique_data = {x['time']: x for x in data}
        d_sorted = sorted(unique_data.values(), key=lambda item: item['time'])
        return json.dumps(d_sorted)

    json_bull = clean_and_dump(box_data_bull)
    json_bear = clean_and_dump(box_data_bear)
    json_mit = clean_and_dump(box_data_mitigated)
    markers_json = json.dumps(markers)

    # --- 3. JAVASCRIPT ---
    chart_html = f"""
    <style>
        body {{ margin: 0; padding: 0; overflow: hidden; background-color: #0B0F19; }}
        #{safe_id} {{ width: 100%; height: 500px; position: absolute; top: 0; left: 0; }}
        .legend {{
            position: absolute; left: 12px; top: 12px; z-index: 10;
            font-family: 'Inter', sans-serif; font-size: 13px;
            color: #94A3B8; pointer-events: none;
            background: rgba(15, 23, 42, 0.6);
            padding: 4px 8px; border-radius: 4px; 
        }}
    </style>
    <div id="{safe_id}"></div>
    <div class="legend">
        <span style="color: #F8FAFC; font-weight: 600;">{ticker}</span> • FVG Zones
    </div>
    <script src="https://unpkg.com/lightweight-charts@4.1.1/dist/lightweight-charts.standalone.production.js"></script>
    <script>
        const container = document.getElementById('{safe_id}');
        
        const chart = LightweightCharts.createChart(container, {{
            width: container.clientWidth, height: 500,
            layout: {{ background: {{ type: 'solid', color: '#0B0F19' }}, textColor: '#64748B', fontFamily: 'Inter' }},
            grid: {{ vertLines: {{ color: 'rgba(255, 255, 255, 0.02)' }}, horzLines: {{ color: 'rgba(255, 255, 255, 0.02)' }} }},
            timeScale: {{ borderColor: 'rgba(255, 255, 255, 0.1)', timeVisible: true }},
            rightPriceScale: {{ borderColor: 'rgba(255, 255, 255, 0.1)', scaleMargins: {{ top: 0.1, bottom: 0.1 }} }},
            crosshair: {{ mode: LightweightCharts.CrosshairMode.Normal }},
        }});

        const addLayer = (data, color) => {{
            if (data.length === 0) return;
            const s = chart.addCandlestickSeries({{
                upColor: color, 
                downColor: color, 
                borderVisible: false,   
                wickVisible: false,     
                priceLineVisible: false,
                lastValueVisible: false,
                crosshairMarkerVisible: false 
            }});
            s.setData(data);
        }};

        // Colori SFONDO (Più opachi per essere visibili anche se piccoli)
        addLayer({json_mit}, 'rgba(148, 163, 184, 0.15)'); // Grigio
        addLayer({json_bull}, 'rgba(34, 197, 94, 0.35)');  // Verde (aumentata opacità per visibilità)
        addLayer({json_bear}, 'rgba(239, 68, 68, 0.35)');  // Rosso (aumentata opacità per visibilità)

        // Serie Prezzo
        const mainSeries = chart.addCandlestickSeries({{ 
            upColor: '#22C55E', downColor: '#EF4444',
            borderUpColor: '#22C55E', borderDownColor: '#EF4444',
            wickUpColor: '#22C55E', wickDownColor: '#EF4444'
        }});
        mainSeries.setData({ohlc_data_json});
        mainSeries.setMarkers({markers_json});

        chart.timeScale().fitContent();
        new ResizeObserver(() => {{ chart.applyOptions({{ width: container.clientWidth }}); }}).observe(container);
    </script>
    """
    components.html(chart_html, height=500, scrolling=False)
    
