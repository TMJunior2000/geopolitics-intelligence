import streamlit as st
import json
import pandas as pd
import numpy as np
import streamlit.components.v1 as components

# -----------------------------------------------------------------------------
# 1. FUNZIONE DI RILEVAMENTO (Corretta per formati tempo e mitigazione)
# -----------------------------------------------------------------------------
def detect_fvgs(df: pd.DataFrame):
    """
    Rileva FVG, calcola mitigazione e assicura formati compatibili.
    """
    if df.empty or len(df) < 3:
        return []

    # Ordine cronologico essenziale
    df = df.sort_values('time').reset_index(drop=True)
    
    fvgs = []
    
    # Pre-calcolo conversioni per velocità
    highs = df['high'].values
    lows = df['low'].values
    times = df['time'].values # Assumiamo datetime64 o simili
    
    for i in range(len(df) - 2):
        # Indici: 0=Candela 1, 1=Candela 2 (Gap), 2=Candela 3
        idx_0, idx_1, idx_2 = i, i+1, i+2
        
        fvg = None
        
        # --- RILEVAMENTO GAP ---
        # BULLISH: High[0] < Low[2]
        if highs[idx_0] < lows[idx_2]:
            fvg = {
                'type': 'BULLISH',
                'top': float(lows[idx_2]),
                'bottom': float(highs[idx_0]),
                'start_time': times[idx_1] # Usiamo l'oggetto raw, convertiamo dopo
            }
        # BEARISH: Low[0] > High[2]
        elif lows[idx_0] > highs[idx_2]:
            fvg = {
                'type': 'BEARISH',
                'top': float(lows[idx_0]),
                'bottom': float(highs[idx_2]),
                'start_time': times[idx_1]
            }

        if fvg:
            # Assicuriamo timestamp Unix (float secondi)
            t_val = fvg['start_time']
            if isinstance(t_val, pd.Timestamp):
                fvg['start_time'] = t_val.timestamp()
            elif hasattr(t_val, 'astype'): # numpy types
                 fvg['start_time'] = t_val.astype('int64') / 1e9
            
            # --- CALCOLO MITIGAZIONE ---
            future_df = df.iloc[idx_2 + 1:] # Candele successive alla conferma
            fvg['mitigated_pct'] = 0.0
            
            if not future_df.empty:
                full_range = fvg['top'] - fvg['bottom']
                # Evita divisione per zero
                if full_range <= 1e-9: full_range = 1.0 

                if fvg['type'] == 'BULLISH':
                    min_reached = float(future_df['low'].min())
                    if min_reached <= fvg['bottom']:
                        fvg['mitigated_pct'] = 100.0
                    elif min_reached < fvg['top']:
                        # Prezzo entrato nel box
                        filled = fvg['top'] - min_reached
                        fvg['mitigated_pct'] = (filled / full_range) * 100.0
                        
                else: # BEARISH
                    max_reached = float(future_df['high'].max())
                    if max_reached >= fvg['top']:
                        fvg['mitigated_pct'] = 100.0
                    elif max_reached > fvg['bottom']:
                        filled = max_reached - fvg['bottom']
                        fvg['mitigated_pct'] = (filled / full_range) * 100.0

            # Arrotondamento
            fvg['mitigated_pct'] = round(fvg['mitigated_pct'], 0)
            
            # --- LOGICA TEMPORALE CHIUSURA ---
            # Se chiuso (>99%), cerchiamo QUANDO è stato chiuso per fermare il rettangolo lì
            fvg['end_time'] = None 
            if fvg['mitigated_pct'] >= 99:
                 if fvg['type'] == 'BULLISH':
                     # Prima candela che ha toccato il bottom
                     hit_mask = future_df['low'] <= fvg['bottom']
                     if hit_mask.any():
                         hit_time = future_df.loc[hit_mask.idxmax(), 'time']
                         fvg['end_time'] = hit_time.timestamp() if isinstance(hit_time, pd.Timestamp) else hit_time
                 else:
                     hit_mask = future_df['high'] >= fvg['top']
                     if hit_mask.any():
                         hit_time = future_df.loc[hit_mask.idxmax(), 'time']
                         fvg['end_time'] = hit_time.timestamp() if isinstance(hit_time, pd.Timestamp) else hit_time
            
            # Se non abbiamo un end_time (perché aperto o errore), mettiamo placeholder
            if fvg['end_time'] is None:
                fvg['end_time'] = fvg['start_time'] # Verrà ignorato dal render se aperto

            # Filtro: Se chiuso completamente, lo scartiamo qui o lo teniamo in base alla logica utente
            # Qui li teniamo tutti, il filtro lo fai fuori se vuoi
            fvgs.append(fvg)

    return fvgs[-30:] # Ritorniamo gli ultimi 30