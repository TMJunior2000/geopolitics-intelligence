import pandas as pd
import streamlit as st
import time
import MetaTrader5 as mt5

class TradingAccount:
    def __init__(self, balance=200.0):
        self.is_connected = False
        self.status = "🟡 SIMULATION (Cloud)"
        self.simulated_balance = balance 

        if mt5.initialize():
            self.is_connected = True
            account_info = mt5.account_info()
            if account_info:
                self.status = f"🟢 LIVE ({account_info.company} - {account_info.login})"
            else:
                self.status = "🟢 LIVE (MT5 Connected)"
        else:
            print(f"MT5 Error: {mt5.last_error()}")
            self.status = "🔴 ERRORE MT5"

    def get_account_info(self):
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
        
        return {
            "balance": self.simulated_balance,
            "equity": self.simulated_balance, 
            "floating_pl": 0.0,
            "used_margin": 0.0,
            "free_margin": self.simulated_balance,
            "positions_count": 0,
            "leverage_account": 50, # Default a 50 come richiesto
            "status": self.status
        }

    def get_positions(self):
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
        if self.is_connected:
            symbols = mt5.symbols_get(visible=True)
            if symbols:
                return [s.name for s in symbols]
        return ["NQ100", "BTCUSD", "EURUSD", "XAUUSD", "NVDA.xnas"]

    def get_asset_specs(self, ticker):
        """
        RECUPERA LEVA REALE BASANDOSI SULLA MODALITÀ DI CALCOLO (CALC_MODE).
        Logica scoperta:
        1. Mode CFD -> Leva = 1 / MarginRate (Es. NVDA, BTC)
        2. Mode CFD_LEVERAGE -> Leva = AccountLev / MarginRate (Es. ORO)
        3. Mode FOREX -> Leva = AccountLev
        """
        if self.is_connected:
            if not mt5.symbol_select(ticker, True): return None

            info = mt5.symbol_info(ticker)
            
            # Recupera Leva Account (il tuo 50:1)
            acc = mt5.account_info()
            acc_lev = acc.leverage if acc else 50.0
            
            if info:
                calc_mode = info.trade_calc_mode
                margin_rate = info.margin_initial
                if margin_rate == 0: margin_rate = info.margin_maintenance
                
                real_leverage = acc_lev # Default iniziale
                
                # --- LOGICA DI CALCOLO BASATA SULLA TUA SCOPERTA ---
                
                # CASO 1: CFD Puro (NVDA, BTC)
                # Qui il margine è una % fissa (es. 0.1 = 10% = Leva 10)
                if calc_mode == mt5.SYMBOL_CALC_MODE_CFD:
                    if margin_rate > 0:
                        real_leverage = 1.0 / margin_rate
                    else:
                        # Fallback se CFD ma rate 0 (es. casi rari)
                        real_leverage = 20.0 

                # CASO 2: CFD Leverage (ORO/Forex Exotics)
                # Qui il margine è un divisore della leva account
                # Es. Rate 1.0 -> Leva 50 / 1.0 = 50
                # Es. Rate 2.0 -> Leva 50 / 2.0 = 25
                elif calc_mode == mt5.SYMBOL_CALC_MODE_CFDLEVERAGE:
                    if margin_rate > 0:
                        real_leverage = acc_lev / margin_rate
                    else:
                        real_leverage = acc_lev

                # CASO 3: Forex (Standard)
                elif calc_mode == mt5.SYMBOL_CALC_MODE_FOREX:
                    real_leverage = acc_lev
                
                # CASO 4: Futures / Exchange Stocks
                # Spesso margine fisso o 1:1
                elif calc_mode == mt5.SYMBOL_CALC_MODE_EXCH_STOCKS:
                    real_leverage = 1.0 / margin_rate if margin_rate > 0 else 1.0

                # --- SANITIZZAZIONE ---
                # 1. Arrotondamento (49.9 -> 50)
                real_leverage = round(real_leverage)
                
                # 2. Tetto Account
                # La leva finale non può mai superare quella dell'account
                final_leverage = min(real_leverage, acc_lev)
                
                if final_leverage < 1: final_leverage = 1.0

                # Debug nel terminale per conferma
                print(f"🕵️ {ticker} | Mode: {calc_mode} | Rate: {margin_rate} | Leva Calc: {real_leverage}")

                return {
                    "leverage": final_leverage,
                    "contract_size": info.trade_contract_size,
                    "tick_value": info.trade_tick_value,
                    "min_lot": info.volume_min,
                    "max_lot": info.volume_max,
                    "step_lot": info.volume_step,
                    "digits": info.digits
                }

        # 2. MODO SIMULAZIONE
        specs_db = {
            "NQ100": {"leverage": 20.0, "contract_size": 20.0},
            "BTCUSD": {"leverage": 2.0, "contract_size": 1.0},
            "EURUSD": {"leverage": 30.0, "contract_size": 100000.0},
            "NVDA":   {"leverage": 10.0, "contract_size": 1.0},
        }
        clean_ticker = ticker.split('.')[0]
        found_key = next((k for k in specs_db if k in clean_ticker), None)
        
        default_spec = {"leverage": 20.0, "contract_size": 1.0}
        
        # FIX PYLANCE: Sostituiamo .get() con if/else
        # Se found_key è None, .get(None) rompe le scatole a Pylance.
        if found_key:
            base_spec = specs_db[found_key]
        else:
            base_spec = default_spec
        
        base_spec["min_lot"] = 0.01
        base_spec["step_lot"] = 0.01
        base_spec["digits"] = 2
        
        return base_spec

    def get_latest_tick(self, ticker):
        if self.is_connected:
            if not mt5.symbol_select(ticker, True): return None
            tick = mt5.symbol_info_tick(ticker)
            if tick:
                return {"price": tick.ask, "timestamp": tick.time}
        return {"price": 100.0, "timestamp": int(time.time())}