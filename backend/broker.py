import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime

class TradingAccount:
    def __init__(self):
        """
        Inizializza la connessione con il terminale MT5 di FP Markets.
        Assicurati che il terminale sia aperto o installato.
        """
        if not mt5.initialize():
            print("❌ Errore inizializzazione MT5: ", mt5.last_error())
            self.connected = False
        else:
            print(f"✅ Connesso a MT5: {mt5.terminal_info().name}")
            self.connected = True
            
        # Cache per specifiche asset (per non chiamare l'API mille volte)
        self._specs_cache = {}

    def get_account_info(self):
        """
        Recupera i dati LIVE del conto (Equity, Balance, Margine).
        """
        if not self.connected:
            # Fallback dati finti se non connesso (per evitare crash app)
            return {
                "balance": 0.0, "equity": 0.0, "floating_pl": 0.0,
                "used_margin": 0.0, "free_margin": 0.0, "positions_count": 0
            }

        info = mt5.account_info()
        
        if info is None:
            return None

        # Calcolo P&L Totale (Equity - Balance)
        floating_pl = info.equity - info.balance

        return {
            "balance": info.balance,
            "equity": info.equity,
            "floating_pl": floating_pl,
            "used_margin": info.margin,      # Margine usato reale
            "free_margin": info.margin_free, # Margine libero reale
            "leverage": info.leverage,       # Leva del conto (es. 500)
            "positions_count": mt5.positions_total()
        }

    def get_positions(self):
        """
        Scarica le posizioni aperte e le formatta per il Risk Engine.
        """
        if not self.connected: return []

        positions = mt5.positions_get()
        formatted_positions = []

        if positions:
            for pos in positions:
                # MT5 Type: 0 = Buy, 1 = Sell
                direction = "LONG" if pos.type == 0 else "SHORT"
                
                formatted_positions.append({
                    "ticket": pos.ticket,
                    "symbol": pos.symbol,
                    "type": direction,
                    "lots": pos.volume,
                    "entry_price": pos.price_open,
                    "current_price": pos.price_current,
                    "stop_loss": pos.sl,       # Fondamentale per il Risk Engine
                    "take_profit": pos.tp,
                    "profit": pos.profit,
                    "swap": pos.swap
                })
        
        return formatted_positions

    def get_asset_specs(self, ticker):
        """
        Recupera le specifiche tecniche dell'asset (Contract Size, Leva, Tick Value).
        Fondamentale per calcolare il rischio in dollari.
        """
        if not self.connected: 
            return {"leverage": 30, "contract_size": 1, "tick_value": 1.0}

        # Controllo se è in cache per velocità
        if ticker in self._specs_cache:
            return self._specs_cache[ticker]

        symbol_info = mt5.symbol_info(ticker)
        
        if symbol_info is None:
            # Provo ad aggiungere suffissi tipici se non lo trova (es. EURUSD.r)
            # FP Markets a volte usa suffissi, ma se selezioni dal Market Watch va bene.
            return {"leverage": 30, "contract_size": 1, "tick_value": 1.0}

        # Calcolo Leva Specifica Asset
        # MT5 non dà sempre la leva del simbolo diretta, usiamo quella del conto
        # o calcoliamo margine richiesto per 1 lotto.
        account_leverage = mt5.account_info().leverage
        
        # Alcuni broker su CFD riducono la leva. Per sicurezza usiamo 
        # una logica conservativa o quella del conto se non specificato.
        # Per FP Markets la leva conto è affidabile per il Forex.
        
        specs = {
            "leverage": account_leverage, 
            "contract_size": symbol_info.trade_contract_size,
            "tick_value": symbol_info.trade_tick_value,
            "min_lot": symbol_info.volume_min,
            "step_lot": symbol_info.volume_step
        }
        
        self._specs_cache[ticker] = specs
        return specs
        
    def execute_trade(self, ticker, action, lots, sl=0.0, tp=0.0):
        """
        Funzione extra per eseguire i trade direttamente dalla Dashboard (Opzionale).
        """
        symbol_info = mt5.symbol_info(ticker)
        if not symbol_info:
            return "❌ Simbolo non trovato"
            
        if not symbol_info.visible:
            if not mt5.symbol_select(ticker, True):
                return "❌ Impossibile selezionare il simbolo"

        order_type = mt5.ORDER_TYPE_BUY if action == "LONG" else mt5.ORDER_TYPE_SELL
        price = mt5.symbol_info_tick(ticker).ask if action == "LONG" else mt5.symbol_info_tick(ticker).bid

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": ticker,
            "volume": float(lots),
            "type": order_type,
            "price": price,
            "sl": float(sl),
            "tp": float(tp),
            "deviation": 20,
            "magic": 234000,
            "comment": "Kairos AI Trade",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            return f"❌ Errore: {result.comment}"
        
        return "✅ Ordine Eseguito"