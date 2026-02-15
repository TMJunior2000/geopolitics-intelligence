import streamlit as st
import pandas as pd
import numpy as np

def detect_fvgs(df: pd.DataFrame):
    """
    Rileva FVG, calcola mitigazione %, punti totali e punti rimanenti da colmare.
    Filtra quelli mitigati >= 98%.
    """
    if df.empty or len(df) < 3:
        return []

    # Ordine cronologico essenziale
    df = df.sort_values('time').reset_index(drop=True)
    
    fvgs = []
    
    # Pre-calcolo conversioni per velocità
    highs = df['high'].values
    lows = df['low'].values
    times = df['time'].values 
    
    for i in range(len(df) - 2):
        idx_0, idx_1, idx_2 = i, i+1, i+2
        
        fvg = None
        
        # --- RILEVAMENTO GAP ---
        if highs[idx_0] < lows[idx_2]: # BULLISH
            fvg = {
                'type': 'BULLISH',
                'top': float(lows[idx_2]),
                'bottom': float(highs[idx_0]),
                'start_time': times[idx_1] 
            }
        elif lows[idx_0] > highs[idx_2]: # BEARISH
            fvg = {
                'type': 'BEARISH',
                'top': float(lows[idx_0]),
                'bottom': float(highs[idx_2]),
                'start_time': times[idx_1]
            }

        if fvg:
            # Conversione timestamp
            t_val = fvg['start_time']
            if isinstance(t_val, pd.Timestamp):
                fvg['start_time'] = int(t_val.timestamp())
            elif hasattr(t_val, 'astype'):
                fvg['start_time'] = int(t_val.astype('int64') // 1_000_000_000)

            
            # --- CALCOLO MITIGAZIONE E PUNTI ---
            future_df = df.iloc[idx_2 + 1:] 
            fvg['mitigated_pct'] = 0.0
            
            # Calcolo ampiezza totale in punti
            total_points = round(abs(fvg['top'] - fvg['bottom']), 2)
            fvg['total_points'] = total_points
            
            # Inizializziamo i punti rimanenti con il totale
            fvg['points_to_fill'] = total_points
            
            if not future_df.empty:
                full_range = total_points if total_points > 0 else 1.0 

                if fvg['type'] == 'BULLISH':
                    min_reached = float(future_df['low'].min())
                    
                    if min_reached <= fvg['bottom']:
                        fvg['mitigated_pct'] = 100.0
                        fvg['points_to_fill'] = 0.0
                    elif min_reached < fvg['top']:
                        # Parzialmente mitigato
                        filled = fvg['top'] - min_reached
                        fvg['mitigated_pct'] = round((filled / full_range) * 100, 0)
                        fvg['points_to_fill'] = round(min_reached - fvg['bottom'], 2)
                        
                else: # BEARISH
                    max_reached = float(future_df['high'].max())
                    
                    if max_reached >= fvg['top']:
                        fvg['mitigated_pct'] = 100.0
                        fvg['points_to_fill'] = 0.0
                    elif max_reached > fvg['bottom']:
                        # Parzialmente mitigato
                        filled = max_reached - fvg['bottom']
                        fvg['mitigated_pct'] = round((filled / full_range) * 100, 0)
                        fvg['points_to_fill'] = round(fvg['top'] - max_reached, 2)

            # --- FILTRO 98% ---
            if fvg['mitigated_pct'] < 98:
                fvgs.append(fvg)

    return fvgs