import streamlit as st
import pandas as pd
import json
from datetime import datetime
from lightweight_charts.widgets import StreamlitChart

def render_lightweight_chart(df: pd.DataFrame, ticker: str, fvgs: list | None = None):
    """
    Renderizza il grafico usando la libreria Python ufficiale 'lightweight-charts'.
    
    ANALISI CONFLITTO RISOLTA:
    - Il wrapper converte le date in int64 // 10^9 (Secondi Unix puri).
    - Ora calcoliamo le chiavi del dizionario 'tooltip_map' ESATTAMENTE allo stesso modo.
    - Questo garantisce che param.time (JS) trovi sempre il dato corrispondente nel dizionario.
    """
    if df is None or df.empty:
        st.info(f"Nessun dato per {ticker}")
        return

    # --- 1. PREPARAZIONE DATI & ALLINEAMENTO CHIAVI ---
    df_plot = df.copy()
    if 'date' in df_plot.columns:
        df_plot = df_plot.rename(columns={'date': 'time'})
    
    df_plot['time'] = pd.to_datetime(df_plot['time'])
    df_plot = df_plot.sort_values('time').drop_duplicates(subset=['time'], keep='last')
    
    # [FIX CRITICO] Creiamo una colonna chiave identica a quella usata internamente dalla libreria
    # La libreria fa: df['time'].astype('int64') // 10**9
    # Facciamo lo stesso per assicurarci che le chiavi coincidano.
    df_plot['unix_key'] = df_plot['time'].astype('int64') // 10**9
    
    # Calcolo EMA 50
    df_plot['EMA 50'] = df_plot['close'].rolling(window=50).mean()
    
    # --- 2. CONFIGURAZIONE GRAFICO ---
    # Larghezza 1600 per Desktop Wide
    chart = StreamlitChart(width=1600, height=500, toolbox=True)
    
    chart.layout(background_color='#0B0F19', text_color='#94A3B8', font_size=12, font_family='Inter')
    chart.grid(vert_enabled=True, horz_enabled=True, color='rgba(255, 255, 255, 0.05)', style='solid')
    
    chart.candle_style(
        up_color='#22C55E', down_color='#EF4444',
        border_up_color='#22C55E', border_down_color='#EF4444',
        wick_up_color='#22C55E', wick_down_color='#EF4444'
    )
    
    chart.legend(visible=True, ohlc=True, percent=True, lines=True)
    
    # Topbar
    chart.topbar.textbox('symbol', ticker)
    current_time = datetime.now().strftime('%H:%M')
    chart.topbar.textbox('clock', current_time, align='right')

    # --- 3. CARICAMENTO DATI ---
    chart.set(df_plot)
    if 'volume' in df_plot.columns:
        chart.volume_config(scale_margin_top=0.8)

    # --- 4. EMA (NO PALLINO) ---
    line = chart.create_line(name='EMA 50', color='#3B82F6', width=2, price_line=False)
    chart.run_script(f'{line.id}.series.applyOptions({{crosshairMarkerVisible: false}})')
    line.set(df_plot[['time', 'EMA 50']].dropna())

    # --- 5. DISEGNO FVG E CREAZIONE DIZIONARIO DATI ---
    tooltip_map = {}
    
    if fvgs:
        # Usiamo i dati del DataFrame già calcolati con la chiave corretta
        # Creiamo un dizionario di accesso rapido: unix_key -> time (datetime)
        time_lookup = dict(zip(df_plot['unix_key'], df_plot['time']))
        # Lista di tutte le chiavi Unix disponibili nel grafico
        all_unix_keys = df_plot['unix_key'].tolist()
        last_time = df_plot['time'].iloc[-1]
        
        for fvg in fvgs:
            pct = fvg.get('mitigated_pct', 0)
            pts = fvg.get('points_to_fill', 0)
            
            try:
                # Gestione start_time: se arriva float, lo trattiamo come tale
                raw_start = fvg['start_time']
                if isinstance(raw_start, (int, float)):
                    # Assumiamo sia già in secondi se < 3000000000, altrimenti ms
                    start_unix = int(raw_start) if raw_start < 3000000000 else int(raw_start / 1000)
                    start_t = pd.to_datetime(start_unix, unit='s')
                else:
                    start_t = pd.to_datetime(raw_start)
                    start_unix = int(start_t.timestamp())
            except:
                continue

            # Colori
            if fvg['type'] == 'BULLISH':
                border_color = 'rgba(34, 197, 94, 0.4)'
                fill_color = 'rgba(34, 197, 94, 0.12)'
                label_html = "<span style='color:#2ECC71; font-weight:bold;'>🟢 BULLISH FVG</span>"
            else:
                border_color = 'rgba(239, 68, 68, 0.4)'
                fill_color = 'rgba(239, 68, 68, 0.12)'
                label_html = "<span style='color:#EF4444; font-weight:bold;'>🔴 BEARISH FVG</span>"

            # Disegna Box
            chart.box(
                start_time=start_t,
                start_value=fvg['top'],
                end_time=last_time,
                end_value=fvg['bottom'],
                color=border_color,
                fill_color=fill_color,
                width=1,
                style='solid'
            )
            
            # --- POPOLAZIONE DATI TOOLTIP ---
            info_text = f"""
            <div style="font-size:11px; margin-bottom:4px; color:#94A3B8; text-transform:uppercase; letter-spacing:1px;">Market Structure</div>
            <div style="font-size:14px; margin-bottom:6px;">{label_html}</div>
            <div style="display:flex; gap:20px; font-size:13px; color:#E2E8F0; border-top:1px solid rgba(255,255,255,0.1); padding-top:6px;">
                <span>Mitigated: <b style="color:#F8FAFC">{pct:.0f}%</b></span>
                <span>To Fill: <b style="color:#F8FAFC">{pts:.1f} pts</b></span>
            </div>
            """
            
            # Mappiamo SOLO le chiavi unix che sono >= allo start del FVG
            # Questo evita conversioni di datetime instabili
            for u_key in all_unix_keys:
                if u_key >= start_unix:
                    if u_key not in tooltip_map:
                        tooltip_map[u_key] = []
                    # Evita duplicati di testo identico
                    if info_text not in tooltip_map[u_key]:
                        tooltip_map[u_key].append(info_text)

    # Converti mappa per JS
    js_tooltip_data = {k: "".join(v) for k, v in tooltip_map.items()}
    js_payload = json.dumps(js_tooltip_data)

    # --- 6. INIEZIONE JAVASCRIPT (HUD FISSO SEMPLIFICATO) ---
    js_code = f"""
    // 1. Crea HUD se non esiste
    let hud = document.getElementById('chart-hud-panel');
    if (!hud) {{
        hud = document.createElement('div');
        hud.id = 'chart-hud-panel';
        hud.style.position = 'absolute';
        hud.style.top = '60px'; 
        hud.style.left = '50%';
        hud.style.transform = 'translateX(-50%)';
        hud.style.zIndex = '50';
        hud.style.display = 'none';
        hud.style.padding = '10px 18px';
        hud.style.backgroundColor = 'rgba(15, 23, 42, 0.90)';
        hud.style.backdropFilter = 'blur(4px)';
        hud.style.border = '1px solid rgba(51, 65, 85, 0.5)';
        hud.style.borderRadius = '8px';
        hud.style.boxShadow = '0 4px 12px rgba(0,0,0,0.3)';
        hud.style.fontFamily = 'Inter, sans-serif';
        hud.style.pointerEvents = 'none';
        hud.style.textAlign = 'center';
        hud.style.minWidth = '200px';
        document.getElementById('{chart.id}').appendChild(hud);
    }}

    // 2. Dati Python (Key = Unix Timestamp Intero)
    const hudData = {js_payload};

    // 3. Gestore Eventi
    const chartObj = window['{chart.id}'].chart;
    
    chartObj.subscribeCrosshairMove(param => {{
        if (!param.time || param.point.x < 0) {{
            hud.style.display = 'none';
            return;
        }}

        // --- NORMALIZZAZIONE TOTALE DELLA DATA ---
        // La libreria restituisce param.time come:
        // A) Numero (es. 1709234000) -> Intraday
        // B) Oggetto {{year: 2024, month: 2, day: 15}} -> Daily
        
        let timeKey = null;

        if (typeof param.time === 'object') {{
            // Conversione Oggetto -> Unix Timestamp (Secondi)
            // Attenzione: month è 1-based nell'oggetto della libreria lightweight-charts standard
            // Ma Date.UTC vuole month 0-based.
            const d = new Date(Date.UTC(param.time.year, param.time.month - 1, param.time.day));
            timeKey = d.getTime() / 1000;
        }} else {{
            // E' già un numero
            timeKey = param.time;
        }}

        const content = hudData[timeKey];

        if (content) {{
            hud.innerHTML = content;
            hud.style.display = 'block';
        }} else {{
            hud.style.display = 'none';
        }}
    }});
    """
    
    chart.run_script(js_code)

    # --- 7. RENDER ---
    chart.fit()
    chart.load()