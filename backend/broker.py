import pandas as pd
import streamlit as st
import random

# --- BLOCCO MAGICO IBRIDO ---
# Tenta di importare la libreria MetaTrader5.
# Se siamo su Windows (Tuo PC), la trova e imposta HAS_MT5 = True.
# Se siamo su Streamlit Cloud (Linux), fallisce silenziosamente e imposta HAS_MT5 = False.
try:
    import MetaTrader5 as mt5
    HAS_MT5 = True
except ImportError:
    HAS_MT5 = False

class TradingAccount:
    # MODIFICA FONDAMENTALE QUI SOTTO: aggiungi ", balance=200.0"
    def __init__(self, balance=200.0):
        """
        Inizializza il collegamento al Broker.
        Accetta 'balance' come capitale iniziale per la modalità simulazione.
        """
        self.is_connected = False
        self.status = "🟡 SIMULATION (Cloud)"
        self.simulated_balance = balance # Salviamo il saldo per la demo
        
        # Se la libreria è presente (Siamo su Windows), proviamo a connetterci a MT5
        if HAS_MT5:
            if mt5.initialize():
                self.is_connected = True
                self.status = "🟢 LIVE (FPMarkets)"
            else:
                print(f"MT5 presente ma errore connessione: {mt5.last_error()}")
                self.status = "🔴 ERRORE MT5"
        
    def get_account_info(self):
        """
        Restituisce le informazioni vitali del conto:
        Balance, Equity, Margine Usato, Margine Libero.
        """
        # 1. MODO REALE (Tuo PC Windows con MT5 aperto)
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
                    "status": self.status
                }
        
        # 2. MODO SIMULAZIONE (Streamlit Cloud / Demo)
        # Usiamo self.simulated_balance che abbiamo salvato nell'init
        return {
            "balance": self.simulated_balance,
            "equity": self.simulated_balance, # Assumiamo no P&L all'inizio
            "floating_pl": 0.0,
            "used_margin": 0.0,
            "free_margin": self.simulated_balance,
            "positions_count": 0,
            "status": self.status
        }

    def get_positions(self):
        """
        Scarica le posizioni aperte per calcolare la 'Phantom Equity'.
        """
        # 1. MODO REALE
        if self.is_connected:
            positions = mt5.positions_get()
            if positions:
                formatted = []
                for p in positions:
                    # Mappiamo i dati di MT5 nel formato universale del Risk Engine
                    formatted.append({
                        "ticket": p.ticket,
                        "symbol": p.symbol,
                        "type": "LONG" if p.type == mt5.POSITION_TYPE_BUY else "SHORT",
                        "lots": p.volume,
                        "entry_price": p.price_open,
                        "current_price": p.price_current,
                        "stop_loss": p.sl,
                        "swap": p.swap,
                        "profit": p.profit
                    })
                return formatted
        
        # 2. MODO SIMULAZIONE
        return []

    def get_asset_specs(self, ticker):
        """
        Restituisce le specifiche dell'asset (Leva, Dimensione Contratto, Valore Tick).
        """
        # 1. MODO REALE (Chiediamo al Broker)
        if self.is_connected:
            symbol_info = mt5.symbol_info(ticker)
            if symbol_info:
                try:
                    acc_info = mt5.account_info()
                    acc_lev = acc_info.leverage if acc_info else 30
                except:
                    acc_lev = 30
                
                return {
                    "leverage": acc_lev,
                    "contract_size": symbol_info.trade_contract_size,
                    "tick_value": symbol_info.trade_tick_value
                }

        # 2. MODO SIMULAZIONE (Database statico di specifiche standard)
        specs = {
            "NQ100": {"leverage": 50, "contract_size": 20, "tick_value": 0.25},
            "USTECH100": {"leverage": 50, "contract_size": 20, "tick_value": 0.25},
            "DJ30":  {"leverage": 50, "contract_size": 5, "tick_value": 1.0},
            "SPX500": {"leverage": 50, "contract_size": 50, "tick_value": 0.25},
            "BTCUSD": {"leverage": 10, "contract_size": 1, "tick_value": 1.0},
            "EURUSD": {"leverage": 30, "contract_size": 100000, "tick_value": 1.0},
            "XAUUSD": {"leverage": 20, "contract_size": 100, "tick_value": 1.0},
            "META": {"leverage": 5, "contract_size": 1, "tick_value": 1.0},
            "MSFT": {"leverage": 5, "contract_size": 1, "tick_value": 1.0},
        }
        
        clean_ticker = ticker.split('.')[0].replace('#', '')
        return specs.get(clean_ticker, {"leverage": 20, "contract_size": 1, "tick_value": 1.0})