import pandas as pd
import streamlit as st
import random

# --- BLOCCO MAGICO IBRIDO ---
# Questo prova a caricare MT5. 
# Se siamo sul Cloud (Linux), fallisce silenziosamente e attiva la modalità Simulazione.
# Se siamo sul tuo PC (Windows), funziona e attiva la modalità Live.
try:
    import MetaTrader5 as mt5
    HAS_MT5 = True
except ImportError:
    HAS_MT5 = False

class TradingAccount:
    def __init__(self, balance=200.0):
        """
        Inizializza il broker.
        :param balance: Saldo iniziale per la modalità simulazione (default 200.0)
        """
        self.is_connected = False
        self.mode = "SIMULATION" # Default per il Cloud
        self.simulated_balance = balance # Salviamo il saldo passato da streamlit_app
        
        # Se la libreria esiste (Windows), proviamo a connetterci
        if HAS_MT5:
            if mt5.initialize():
                self.is_connected = True
                self.mode = "LIVE (Local MT5)"
            else:
                print(f"MT5 presente ma errore connessione: {mt5.last_error()}")
        
    def get_account_info(self):
        """
        Se siamo su PC connesso -> Dati Veri.
        Se siamo su Cloud -> Dati Finti (Simulazione usando self.simulated_balance).
        """
        if self.is_connected:
            # --- MODO REALE (Tuo PC Windows) ---
            info = mt5.account_info()
            if info:
                return {
                    "balance": info.balance,
                    "equity": info.equity,
                    "floating_pl": info.profit,
                    "used_margin": info.margin,
                    "free_margin": info.margin_free,
                    "positions_count": mt5.positions_total(),
                    "status": "🟢 CONNECTED (FPMarkets)"
                }
        
        # --- MODO SIMULAZIONE (Streamlit Cloud / Linux) ---
        # Usiamo il saldo che hai passato nell'init
        return {
            "balance": self.simulated_balance,
            "equity": self.simulated_balance,
            "floating_pl": 0.0,
            "used_margin": 0.0,
            "free_margin": self.simulated_balance,
            "positions_count": 0,
            "status": "🟡 SIMULATION MODE (Cloud)"
        }

    def get_positions(self):
        """
        Scarica posizioni reali o lista vuota in simulazione.
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
                        "entry_price": p.open, # Nota: p.open o p.price_open dipende dalla versione, solitamente price_open
                        "current_price": p.price_current,
                        "stop_loss": p.sl,
                        "swap": p.swap,
                        "profit": p.profit
                    })
                return formatted
        return [] # Nessuna posizione in simulazione

    def get_asset_specs(self, ticker):
        """
        Specifiche asset: Reali da MT5 o Standard in simulazione.
        """
        if self.is_connected:
            symbol_info = mt5.symbol_info(ticker)
            if symbol_info:
                try:
                    acc_lev = mt5.account_info().leverage
                except:
                    acc_lev = 50 # Default se fallisce
                
                return {
                    "leverage": acc_lev,
                    "contract_size": symbol_info.trade_contract_size,
                    "tick_value": symbol_info.trade_tick_value
                }

        # Specifiche Standard per la Demo Cloud (Risk Engine)
        specs = {
            "NQ100": {"leverage": 50, "contract_size": 20, "tick_value": 0.25},
            "DJ30":  {"leverage": 50, "contract_size": 5, "tick_value": 1.0},
            "SPX500": {"leverage": 50, "contract_size": 50, "tick_value": 0.25},
            "BTCUSD": {"leverage": 10, "contract_size": 1, "tick_value": 1.0},
            "EURUSD": {"leverage": 30, "contract_size": 100000, "tick_value": 1.0},
            "XAUUSD": {"leverage": 20, "contract_size": 100, "tick_value": 1.0},
        }
        # Pulizia ticker
        clean_ticker = ticker.split('.')[0].replace('#', '')
        # Fallback intelligente
        return specs.get(clean_ticker, {"leverage": 20, "contract_size": 1, "tick_value": 1.0})