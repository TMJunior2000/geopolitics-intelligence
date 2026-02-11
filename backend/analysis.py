import pandas as pd
import numpy as np

def detect_fvgs(df: pd.DataFrame) -> list:
    """
    Rileva FVG e determina il range temporale di esistenza.
    Restituisce dati pronti per il rendering a "rettangoli".
    """
    if df.empty or len(df) < 5:
        return []

    # Usiamo array numpy per velocità
    highs = df['high'].values
    lows = df['low'].values
    
    # --- FIX QUI SOTTO: Aggiunto .values per renderlo un array NumPy ---
    # Senza .values, Pandas cerca l'indice "-1" (che non esiste) invece dell'ultimo elemento.
    times = (df['time'].astype(np.int64) // 10**9).values 
    
    fvgs = []
    n = len(df)

    # 1. Rilevamento (Gap tra candela i-2 e i)
    for i in range(2, n - 1):
        # BULLISH FVG (Gap tra High[i-2] e Low[i])
        if lows[i] > highs[i-2]:
            top = lows[i]
            bottom = highs[i-2]
            gap_size = top - bottom
            
            # Calcolo Mitigazione nel futuro
            mitigated_idx = -1
            current_penetration = 0
            
            for j in range(i + 1, n):
                # Se il prezzo scende sotto il top, sta mitigando
                if lows[j] < top:
                    current_penetration = max(current_penetration, top - lows[j])
                    # Se tocca il fondo, è mitigato totalmente
                    if lows[j] <= bottom:
                        mitigated_idx = j
                        break
            
            mit_pct = round((current_penetration / gap_size) * 100, 1) if gap_size > 0 else 0
            
            fvgs.append({
                'start_time': times[i-1], # Tempo della candela centrale che crea il gap
                # Ora times[-1] funzionerà perché times è un array numpy
                'end_time': times[mitigated_idx] if mitigated_idx != -1 else times[-1],
                'top': top,
                'bottom': bottom,
                'type': 'bullish',
                'mitigated_pct': min(mit_pct, 100.0),
                'fully_mitigated': mitigated_idx != -1
            })

        # BEARISH FVG (Gap tra Low[i-2] e High[i])
        elif highs[i] < lows[i-2]:
            top = lows[i-2]
            bottom = highs[i]
            gap_size = top - bottom

            mitigated_idx = -1
            current_penetration = 0

            for j in range(i + 1, n):
                if highs[j] > bottom:
                    current_penetration = max(current_penetration, highs[j] - bottom)
                    if highs[j] >= top:
                        mitigated_idx = j
                        break
            
            mit_pct = round((current_penetration / gap_size) * 100, 1) if gap_size > 0 else 0

            fvgs.append({
                'start_time': times[i-1],
                'end_time': times[mitigated_idx] if mitigated_idx != -1 else times[-1],
                'top': top,
                'bottom': bottom,
                'type': 'bearish',
                'mitigated_pct': min(mit_pct, 100.0),
                'fully_mitigated': mitigated_idx != -1
            })

    return fvgs