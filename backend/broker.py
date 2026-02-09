from typing import Any
import pandas as pd
import streamlit as st
import time
import MetaTrader5 as mt5
 

class TradingAccount:
    def __init__(self, balance=200.0):
        """
        Inizializza il collegamento al Broker.
        """
        self.is_connected = False
        self.status = "🟡 SIMULATION (Cloud)"
        self.simulated_balance = balance 
        
        # Connessione MT5 (Solo Windows/Locale)
        if mt5.initialize():
            self.is_connected = True
            
            # Info conto base
            account_info = mt5.account_info()
            if account_info:
                broker_name = account_info.company
                login = account_info.login
                self.status = f"🟢 LIVE ({broker_name} - {login})"
            else:
                self.status = "🟢 LIVE (MT5 Connected)"
        else:
            print(f"MT5 presente ma errore connessione: {mt5.last_error()}")
            self.status = "🔴 ERRORE MT5"

    def get_account_info(self):
        """
        Documentazione: mt5.account_info()
        Restituisce named tuple con balance, equity, margin_free.
        """
        if self.is_connected:
            info = mt5.account_info()
            if info:
                return {
                    "balance": info.balance,
                    "equity": info.equity,
                    "floating_pl": info.profit,
                    "used_margin": info.margin,
                    "free_margin": info.margin_free,
                    "positions_count": mt5.positions_total(),
                    "leverage_account": info.leverage, 
                    "status": self.status
                }
        
        # MODO SIMULAZIONE
        return {
            "balance": self.simulated_balance,
            "equity": self.simulated_balance, 
            "floating_pl": 0.0,
            "used_margin": 0.0,
            "free_margin": self.simulated_balance,
            "positions_count": 0,
            "leverage_account": 30, # Default prudente
            "status": self.status
        }

    def get_positions(self):
        """
        Documentazione: mt5.positions_get()
        """
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
        """
        Documentazione: mt5.symbols_get(visible=True)
        Recupera solo i simboli presenti nel 'Market Watch'.
        """
        if self.is_connected:
            symbols = mt5.symbols_get(visible=True)
            if symbols:
                return [s.name for s in symbols]
        
        # Fallback simulazione
        return ["NQ100", "BTCUSD", "EURUSD", "XAUUSD", "NVDA.xnas"]

    def get_asset_specs(self, ticker):
            """
            RECUPERA SPECIFICHE ASSET CON DEBUG PRINTS.
            """
            # 1. MODO REALE (MT5)
            if self.is_connected:
                if not mt5.symbol_select(ticker, True):
                    print(f"🔴 DEBUG: Impossibile selezionare {ticker}")
                    return None

                # Doc: mt5.symbol_info("SYMBOL") restituisce named tuple
                info = mt5.symbol_info(ticker)
                
                if info:
                    print(f"\n--- 🕵️‍♂️ DEBUG ASSET: {ticker} ---")
                    print(f"   > Path: {info.path}")
                    print(f"   > Margin Initial (Raw): {info.margin_initial}")
                    print(f"   > Margin Maintenance (Raw): {info.margin_maintenance}")
                    print(f"   > Contract Size: {info.trade_contract_size}")
                    
                    # --- CALCOLO LEVA REALE (Doc: margin_initial) ---
                    margin_rate = info.margin_initial
                    
                    # Fallback doc: margin_maintenance
                    if margin_rate == 0:
                        print("   ⚠️ Margin Initial è 0. Provo con Margin Maintenance...")
                        margin_rate = info.margin_maintenance

                    real_leverage = 1.0

                    if margin_rate > 0:
                        # FORMULA: 1 / 0.10 = 10.0 (Leva 1:10)
                        real_leverage = 1.0 / margin_rate
                        print(f"   ✅ CALCOLO: 1 / {margin_rate} = Leva {real_leverage}")
                    else:
                        print("   ⚠️ Margin Rate è ancora 0. Uso Leva Account + Safety Cap.")
                        # --- CASO STANDARD / FOREX ---
                        acc = mt5.account_info()
                        acc_lev = acc.leverage if acc else 30.0
                        print(f"   > Leva Account Base: {acc_lev}")
                        
                        # SAFETY CAP
                        path = info.path.upper() 
                        if "STOCK" in path or "SHARE" in path or "EQUITY" in path or "NASDAQ" in path:
                            real_leverage = min(acc_lev, 20.0) 
                            print(f"   🛡️ SAFETY CAP ATTIVATO (Stock/Index): Leva forzata a {real_leverage}")
                        else:
                            real_leverage = acc_lev
                            print(f"   ℹ️ Uso Leva Account Standard: {real_leverage}")

                    return {
                        "leverage": real_leverage,
                        "contract_size": info.trade_contract_size,
                        "tick_value": info.trade_tick_value,
                        "min_lot": info.volume_min,
                        "max_lot": info.volume_max,
                        "step_lot": info.volume_step,
                        "digits": info.digits
                    }
                else:
                    print(f"🔴 DEBUG: mt5.symbol_info({ticker}) ha restituito None")

            # 2. MODO SIMULAZIONE (Database statico)
            print(f"🟡 DEBUG: Modo Simulazione per {ticker}")
            
            # FIX PYLANCE: Definiamo esplicitamente i valori come float o misti
            specs_db = {
                "NQ100": {"leverage": 20.0, "contract_size": 20.0},
                "BTCUSD": {"leverage": 2.0, "contract_size": 1.0},
                "EURUSD": {"leverage": 30.0, "contract_size": 100000.0},
                "XAUUSD": {"leverage": 20.0, "contract_size": 100.0},
                "NVDA":   {"leverage": 10.0, "contract_size": 1.0},
            }
            
            clean_ticker = ticker.split('.')[0]
            # Cerchiamo parziale (es. NVDA.xnas -> NVDA)
            found_key = next((k for k in specs_db if k in clean_ticker), None)
            
            # Default generico se non trovato
            default_spec = {"leverage": 20.0, "contract_size": 1.0}
            
            # Ora .get() è felice perché i tipi coincidono (str -> dict[str, float])
            if found_key:
                base_spec = specs_db[found_key]
            else:
                base_spec = default_spec

            # Default fields per simulazione
            base_spec["min_lot"] = 0.01
            base_spec["step_lot"] = 0.01
            base_spec["digits"] = 2
            
            return base_spec

    def get_latest_tick(self, ticker):
        """
        Documentazione: mt5.symbol_info_tick(symbol)
        Restituisce: time, bid, ask, last, volume...
        """
        if self.is_connected:
            if not mt5.symbol_select(ticker, True):
                return None
            
            # Doc: symbol_info_tick restituisce una tupla Tick()
            tick = mt5.symbol_info_tick(ticker)
            if tick:
                return {
                    "price": tick.ask, # Usiamo ASK per simulare un Buy
                    "bid": tick.bid,
                    # Doc: time (Timestamp Unix del server broker)
                    "timestamp": tick.time 
                }
        
        # Fallback simulazione
        mock_prices = {
            "BTCUSD": 96500.0, "EURUSD": 1.0540, "NQ100": 21500.0, "XAUUSD": 2950.0
        }
        return {
            "price": mock_prices.get(ticker, 100.0),
            "timestamp": int(time.time())
        }