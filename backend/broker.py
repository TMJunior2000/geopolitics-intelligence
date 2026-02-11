import pandas as pd
import streamlit as st
import time
import MetaTrader5 as mt5
import numpy as np
import MetaTrader5 as mt5
from datetime import datetime

class TradingAccount:
    def __init__(self, balance=200.0):
        self.is_connected = False
        self.status = "🟡 SIMULATION (Cloud)"
        self.simulated_balance = balance 
        self.account_currency = "USD" 
        
        # Tenta la connessione al terminale
        if mt5.initialize():
            self.is_connected = True
            account_info = mt5.account_info()
            if account_info:
                self.status = f"🟢 LIVE ({account_info.company} - {account_info.login})"
                self.account_currency = account_info.currency
            else:
                self.status = "🟢 LIVE (MT5 Connected)"
        else:
            print(f"MT5 Error: {mt5.last_error()}")
            self.status = "🔴 ERRORE MT5"

    def get_account_info(self):
            """Restituisce saldo, equità, margine, leva e NUMERO CONTO."""
            if self.is_connected:
                info = mt5.account_info()
                if info:
                    return {
                        "login": info.login,          # <--- AGGIUNGI QUESTA RIGA
                        "balance": info.balance,
                        "equity": info.equity,
                        "floating_pl": info.profit,
                        "used_margin": info.margin,
                        "free_margin": info.margin_free,
                        "positions_count": mt5.positions_total(),
                        "leverage_account": info.leverage, 
                        "status": self.status
                    }
            
            # Fallback Simulazione
            return {
                "login": 12345678,                # <--- Numero finto per simulazione
                "balance": self.simulated_balance,
                "equity": self.simulated_balance, 
                "floating_pl": 0.0,
                "used_margin": 0.0,
                "free_margin": self.simulated_balance,
                "positions_count": 0,
                "leverage_account": 50,
                "status": self.status
            }

    def get_positions(self):
        """Recupera le posizioni aperte."""
        if self.is_connected:
            positions = mt5.positions_get()
            if positions:
                formatted = []
                for p in positions:
                    formatted.append({
                        "ticket": p.ticket,
                        "symbol": p.symbol,
                        "type": "LONG" if p.type == mt5.POSITION_TYPE_BUY else "SHORT",
                        "lots": p.volume,
                        "entry_price": p.price_open,
                        "current_price": p.price_current,
                        "stop_loss": p.sl,
                        "profit": p.profit
                    })
                return formatted
        return []

    def get_all_available_tickers(self):
        """Recupera i simboli dal Market Watch."""
        if self.is_connected:
            symbols = mt5.symbols_get(visible=True)
            if symbols:
                return [s.name for s in symbols]
        return ["NQ100", "BTCUSD", "EURUSD", "XAUUSD", "NVDA.xnas"]

    def get_asset_specs(self, ticker):
            """
            CALCOLA LEVA REALE E MARGINE MINIMO RISPETTANDO IL BLOCCO ACCOUNT.
            """
            if self.is_connected:
                if not mt5.symbol_select(ticker, True): return None

                info = mt5.symbol_info(ticker)
                acc = mt5.account_info()
                
                # 1. LEGGE IL BLOCCO ACCOUNT (Tetto Massimo Inviolabile)
                acc_lev_cap = float(acc.leverage) if acc else 50.0
                acc_curr = acc.currency if acc else "USD"
                
                if info:
                    print(f"\n--- 🛡️ VERIFICA BLOCCO LEVA: {ticker} ---")
                    
                    margin_rate = info.margin_initial
                    if margin_rate == 0: margin_rate = info.margin_maintenance
                    
                    # Inizializziamo la leva calcolata dell'asset
                    asset_leverage = acc_lev_cap 
                    
                    # --- FASE A: CALCOLO LEVA SPECIFICA ASSET ---
                    if margin_rate > 0:
                        # Se il tasso è >= 1 (es. ORO), è un divisore. Se < 1 (es. NVDA), è percentuale.
                        if margin_rate >= 1.0: asset_leverage = acc_lev_cap / margin_rate
                        else: asset_leverage = 1.0 / margin_rate
                    else:
                        # Calcolo dinamico tramite order_calc_margin (solo se le valute coincidono)
                        if info.currency_profit == acc_curr:
                            tick = mt5.symbol_info_tick(ticker)
                            price = tick.ask if tick else 0.0
                            if price > 0:
                                try:
                                    m_req = mt5.order_calc_margin(mt5.ORDER_TYPE_BUY, ticker, 1.0, price)
                                    if m_req and m_req > 0:
                                        notional = price * 1.0 * info.trade_contract_size
                                        asset_leverage = notional / m_req
                                except: pass
                        else:
                            # Fallback per asset esteri (Hong Kong etc.)
                            path = info.path.upper()
                            if any(x in path for x in ["STOCK", "SHARE"]): asset_leverage = 20.0
                            else: asset_leverage = acc_lev_cap

                    # --- FASE B: APPLICAZIONE DEL BLOCCO (MINIMUM RULE) ---
                    asset_leverage = round(asset_leverage)
                    final_leverage = min(asset_leverage, acc_lev_cap)
                    
                    # --- FASE C: CALCOLO MARGINE MINIMO REALE PER L'HUD ---
                    tick = mt5.symbol_info_tick(ticker)
                    price = tick.ask if tick else 0.0
                    min_lot = info.volume_min
                    
                    # Calcolo manuale forzato sul blocco account per allinearsi alla realtà MT5
                    # Margine = (Prezzo * Lotto * Contract) / LevaFinale
                    if price > 0 and final_leverage > 0:
                        notional_min = price * min_lot * info.trade_contract_size
                        margin_min_val = notional_min / final_leverage
                    else:
                        margin_min_val = 0.0

                    print(f"   > Leva Finale: 1:{final_leverage} | Margine Min HUD: ${margin_min_val:.2f}")

                    return {
                        "leverage": float(final_leverage),
                        "contract_size": info.trade_contract_size,
                        "tick_value": info.trade_tick_value,
                        "min_lot": min_lot,
                        "max_lot": info.volume_max,      # Aggiunto
                        "step_lot": info.volume_step,    # Aggiunto per lo step dell'input
                        "margin_min": float(margin_min_val),
                        "digits": info.digits
                    }
            return None

    def get_latest_tick(self, ticker):
        if self.is_connected:
            if not mt5.symbol_select(ticker, True): return None
            tick = mt5.symbol_info_tick(ticker)
            if tick:
                return {"price": tick.ask, "timestamp": tick.time}
        return {"price": 100.0, "timestamp": int(time.time())}
    
    def get_candles(self, ticker, timeframe="H4", n_candles=500):
            """
            Scarica candele per il grafico.
            timeframe: "H4" o "M15"
            """
            # Mappa stringa -> costante MT5
            tf_map = {
                "H4": mt5.TIMEFRAME_H4,
                "M15": mt5.TIMEFRAME_M15
            }
            mt5_tf = tf_map.get(timeframe, mt5.TIMEFRAME_H4) # Default H4

            if self.is_connected:
                if not mt5.symbol_select(ticker, True):
                    return pd.DataFrame()
                
                # Scarica tassi
                rates = mt5.copy_rates_from_pos(ticker, mt5_tf, 0, n_candles)
                
                if rates is not None and len(rates) > 0:
                    df = pd.DataFrame(rates)
                    df['time'] = pd.to_datetime(df['time'], unit='s')
                    df = df.sort_values('time').reset_index(drop=True)
                    return df[['time', 'open', 'high', 'low', 'close']]
                else:
                    return pd.DataFrame()

            # --- SIMULAZIONE OFFLINE ---
            # Adatta la frequenza dei dati finti
            freq_map = {"H4": "4h", "M15": "15min"}
            freq = freq_map.get(timeframe, "4h")
            
            dates = pd.date_range(end=datetime.now(), periods=n_candles, freq=freq)
            df = pd.DataFrame(index=dates)
            df['time'] = df.index
            # ... logica random walk identica a prima ...
            df['close'] = 100 + np.random.randn(n_candles).cumsum()
            df['open'] = df['close'].shift(1).fillna(100)
            df['high'] = df[['open', 'close']].max(axis=1) + abs(np.random.randn(n_candles))
            df['low'] = df[['open', 'close']].min(axis=1) - abs(np.random.randn(n_candles))
            return df[['time', 'open', 'high', 'low', 'close']]