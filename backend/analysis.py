import pandas as pd
import numpy as np

def detect_fvgs(df: pd.DataFrame):
    """
    Rileva i Fair Value Gaps (FVG) e calcola la reale percentuale di mitigazione.
    """
    if df.empty or len(df) < 3:
        return []

    # ASSICURIAMO L'ORDINE CRONOLOGICO (Fondamentale per la mitigazione)
    df = df.sort_values('time').reset_index(drop=True)
    
    fvgs = []
    # Analisi a finestra mobile di 3 candele
    for i in range(len(df) - 2):
        c0, c1, c2 = df.iloc[i], df.iloc[i+1], df.iloc[i+2]
        
        fvg = None
        # --- IDENTIFICAZIONE GAP ---
        # BULLISH: Massimo candela 1 < Minimo candela 3
        if float(c0['high']) < float(c2['low']):
            fvg = {
                'type': 'BULLISH',
                'top': float(c2['low']),
                'bottom': float(c0['high']),
                'start_time': c1['time'].timestamp() if hasattr(c1['time'], 'timestamp') else c1['time']
            }
        # BEARISH: Minimo candela 1 > Massimo candela 3
        elif float(c0['low']) > float(c2['high']):
            fvg = {
                'type': 'BEARISH',
                'top': float(c0['low']),
                'bottom': float(c2['high']),
                'start_time': c1['time'].timestamp() if hasattr(c1['time'], 'timestamp') else c1['time']
            }

        if fvg:
            # --- CALCOLO MITIGAZIONE (REALE) ---
            # Guardiamo tutte le candele nate DOPO il gap (da i+3 in poi)
            future_candles = df.iloc[i+3:]
            
            fvg['mitigated_pct'] = 0.0 
            fvg['is_mitigated'] = False
            
            if not future_candles.empty:
                full_range = fvg['top'] - fvg['bottom']
                
                if full_range > 0: # Evitiamo divisioni per zero
                    if fvg['type'] == 'BULLISH':
                        # Cerchiamo il punto più basso toccato dal prezzo dopo il gap
                        min_reached = float(future_candles['low'].min())
                        
                        if min_reached <= fvg['bottom']: 
                            fvg['mitigated_pct'] = 100.0
                        elif min_reached < fvg['top']:
                            # Il prezzo è entrato nel rettangolo
                            filled_amount = fvg['top'] - min_reached
                            fvg['mitigated_pct'] = (filled_amount / full_range) * 100
                            
                    else: # BEARISH
                        # Cerchiamo il punto più alto toccato dal prezzo dopo il gap
                        max_reached = float(future_candles['high'].max())
                        
                        if max_reached >= fvg['top']:
                            fvg['mitigated_pct'] = 100.0
                        elif max_reached > fvg['bottom']:
                            # Il prezzo è entrato nel rettangolo
                            filled_amount = max_reached - fvg['bottom']
                            fvg['mitigated_pct'] = (filled_amount / full_range) * 100

            # Arrotondiamo per pulizia
            fvg['mitigated_pct'] = round(fvg['mitigated_pct'], 2)

            # Filtro: Se il gap è già chiuso al 99%, non lo mandiamo al grafico
            if fvg['mitigated_pct'] > 99:
                 continue 

            # Estensione orizzontale nel futuro (per il disegno)
            last_time = df.iloc[-1]['time']
            if hasattr(last_time, 'timestamp'):
                fvg['end_time'] = (last_time + pd.Timedelta(hours=4)).timestamp()
            else:
                fvg['end_time'] = last_time + 14400 
            
            fvgs.append(fvg)

    return fvgs[-20:] # Ritorna solo i più recenti