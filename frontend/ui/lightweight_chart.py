import streamlit as st
import json
import pandas as pd
import numpy as np
import streamlit.components.v1 as components

def render_lightweight_chart(df: pd.DataFrame, ticker: str, fvgs: list | None = None):
    """
    Renderizza FVG come RETTANGOLI SOLIDI (stile LuxAlgo) su Tema Scuro.
    Usa il trucco della "ripetizione di candele" per simulare i box nella v4.1.1.
    """
    if df is None or df.empty:
        st.info(f"Nessun dato per {ticker}")
        return

    # --- 1. PREPARAZIONE DATI ---
    df_plot = df.copy()
    df_plot["time"] = pd.to_datetime(df_plot["time"], errors="coerce")
    df_plot = df_plot.dropna(subset=["time"])
    df_plot = df_plot.sort_values("time")
    df_plot = df_plot.drop_duplicates(subset=["time"], keep='last')

    # Master list di tutti i tempi Unix presenti nel grafico
    all_times_array = df_plot['time'].astype(np.int64) // 10**9
    all_times_list = all_times_array.tolist()
    
    # Dati Prezzo Principale
    ohlc_data = df_plot[['open', 'high', 'low', 'close']].copy()
    ohlc_data['time'] = all_times_array
    ohlc_data_json = json.dumps(ohlc_data.to_dict(orient='records'))
    
    # ID univoco
    safe_id = f"chart_{ticker.replace('.', '_').replace('/', '_').replace(':', '_')}"

    # --- 2. GENERAZIONE RETTANGOLI FVG (IL TRUCCO) ---
    box_data_bull = []
    box_data_bear = []
    box_data_mitigated = []
    markers = []

    if fvgs:
        # Mappa per trovare velocemente l'indice di un timestamp
        time_to_idx = {t: i for i, t in enumerate(all_times_list)}
        last_idx = len(all_times_list) - 1

        for fvg in fvgs:
            try:
                # Trova indice inizio e fine approssimativi
                start_t = int(fvg['start_time'])
                end_t = int(fvg['end_time'])
                
                # Logica Python per trovare l'indice (next con generator)
                start_idx = next((i for t, i in time_to_idx.items() if t >= start_t), 0)
                end_idx = next((i for t, i in time_to_idx.items() if t >= end_t), last_idx)
                
                is_bullish = (fvg['type'] == 'bullish')
                top = fvg['top']
                bottom = fvg['bottom']
                pct = fvg['mitigated_pct']
                is_fully_mitigated = fvg.get('fully_mitigated', False) or pct >= 99

                # --- FIX: LOGICA PYTHON CORRETTA ---
                label_icon = '🟢' if is_bullish else '🔴'
                if is_fully_mitigated: label_icon = '⚪'
                
                # Uso .append() invece di .push()
                markers.append({
                    'time': all_times_list[start_idx],
                    'position': 'belowBar' if is_bullish else 'aboveBar',
                    'color': '#94A3B8' if is_fully_mitigated else ('#2ECC71' if is_bullish else '#EF4444'),
                    'shape': 'arrowUp', 
                    'text': f"{label_icon} FVG {pct}%",
                    'size': 0 
                })

                # Genera le "fette" del rettangolo
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
                # print(f"Errore rendering FVG: {e}") # Debug opzionale
                continue

    # Funzione per pulire i dati per JS
    def clean_and_dump(data):
        if not data: return "[]"
        d_map = {x['time']: x for x in sorted(data, key=lambda item: item['time'])}
        return json.dumps(list(d_map.values()))

    json_bull = clean_and_dump(box_data_bull)
    json_bear = clean_and_dump(box_data_bear)
    json_mit = clean_and_dump(box_data_mitigated)
    markers_json = json.dumps(markers)

    # --- 3. HTML & JS ---
    chart_html = f"""
    <style>
        body {{ margin: 0; padding: 0; overflow: hidden; background-color: #0B0F19; }}
        #{safe_id} {{ width: 100%; height: 500px; position: absolute; top: 0; left: 0; }}
        .legend {{
            position: absolute; left: 12px; top: 12px; z-index: 10;
            font-family: 'Inter', sans-serif; font-size: 13px;
            color: #E2E8F0; pointer-events: none;
            background: rgba(15, 23, 42, 0.7);
            padding: 6px 10px; border-radius: 6px; border: 1px solid rgba(255,255,255,0.1);
        }}
    </style>

    <div id="{safe_id}"></div>
    <div class="legend">
        <span style="color: #2ECC71; font-weight: 700;">{ticker}</span> 
        <span style="color: #94A3B8;">• FVG Liquidity Zones</span>
    </div>

    <script>
        function initChart() {{
            const container = document.getElementById('{safe_id}');
            if (!container) return;
            const width = container.clientWidth || 500;
            const height = 500;

            const chart = LightweightCharts.createChart(container, {{
                width: width, height: height,
                layout: {{
                    backgroundColor: '#0B0F19',
                    textColor: '#94A3B8',
                    fontFamily: 'Inter, system-ui, sans-serif',
                }},
                grid: {{
                    vertLines: {{ color: 'rgba(255, 255, 255, 0.03)' }},
                    horzLines: {{ color: 'rgba(255, 255, 255, 0.03)' }},
                }},
                timeScale: {{
                    borderColor: 'rgba(255, 255, 255, 0.1)',
                    timeVisible: true, secondsVisible: false,
                }},
                rightPriceScale: {{
                    borderColor: 'rgba(255, 255, 255, 0.1)',
                    scaleMargins: {{ top: 0.15, bottom: 0.15 }},
                }},
                crosshair: {{ mode: LightweightCharts.CrosshairMode.Normal }},
            }});

            // LAYER FVG
            const mitSeries = chart.addCandlestickSeries({{
                upColor: 'rgba(148, 163, 184, 0.15)', downColor: 'rgba(148, 163, 184, 0.15)', 
                borderVisible: false, wickVisible: false, priceLineVisible: false, lastValueVisible: false
            }});
            mitSeries.setData({json_mit});

            const bullSeries = chart.addCandlestickSeries({{
                upColor: 'rgba(46, 204, 113, 0.3)', downColor: 'rgba(46, 204, 113, 0.3)',
                borderVisible: false, wickVisible: false, priceLineVisible: false, lastValueVisible: false
            }});
            bullSeries.setData({json_bull});

            const bearSeries = chart.addCandlestickSeries({{
                upColor: 'rgba(239, 68, 68, 0.3)', downColor: 'rgba(239, 68, 68, 0.3)',
                borderVisible: false, wickVisible: false, priceLineVisible: false, lastValueVisible: false
            }});
            bearSeries.setData({json_bear});

            // LAYER PREZZO
            const mainSeries = chart.addCandlestickSeries({{
                upColor: '#2ECC71', downColor: '#EF4444',
                borderUpColor: '#2ECC71', borderDownColor: '#EF4444',
                wickUpColor: '#2ECC71', wickDownColor: '#EF4444',
            }});
            mainSeries.setData({ohlc_data_json});
            mainSeries.setMarkers({markers_json});

            chart.timeScale().fitContent();
            
            new ResizeObserver(entries => {{
                if (entries.length === 0) return;
                const r = entries[0].contentRect;
                if (r.width > 0) chart.applyOptions({{ width: r.width, height: r.height }});
            }}).observe(container);
        }}
    </script>
    <script src="https://unpkg.com/lightweight-charts@4.1.1/dist/lightweight-charts.standalone.production.js" onload="initChart()"></script>
    """
    components.html(chart_html, height=500, scrolling=False)