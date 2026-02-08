import pandas as pd

class TradingAccount:
    def __init__(self, balance=200.0, leverage_default=50):
        # Dati statici (Simulazione API)
        self.balance = balance
        self.leverage_default = leverage_default
        self.currency = "USD"
        
        # Posizioni Aperte (Esempio: Sei già Short su NQ da giorni)
        # Struttura: Ticker, Type, Lots, Entry, SL, CurrentPrice
        self.open_positions = [
            # Esempio: Short NQ aperto prima del crollo
            # {
            #     "ticket": 12345,
            #     "symbol": "NQ100",
            #     "type": "SHORT",
            #     "lots": 0.02,
            #     "entry_price": 25120.0,
            #     "current_price": 24700.0,
            #     "stop_loss": 25200.0,  # SL già spostato a protezione
            #     "swap": -1.50
            # }
        ]

    def get_account_info(self):
        """
        Calcola Equity, Margine e P&L in tempo reale.
        """
        floating_pl = 0.0
        used_margin = 0.0
        
        for pos in self.open_positions:
            # Calcolo P&L (Semplificato per CFD)
            # Short: (Entry - Current) * Size * ContractValue
            # Long: (Current - Entry) * Size * ContractValue
            # Assumiamo Contract Size = 1 per Indici per semplicità matematica qui
            
            diff = 0
            if pos['type'] == 'SHORT':
                diff = pos['entry_price'] - pos['current_price']
            else:
                diff = pos['current_price'] - pos['entry_price']
                
            # Valore punto approssimativo (es. 0.02 lotti su NQ = $0.40 a punto su contract size standard, 
            # ma qui usiamo microlotti diretti per l'esempio)
            # Standard NQ contract = $20 per point. 0.02 lotti = $0.40 per point.
            point_value = 20 * pos['lots'] 
            
            profit = diff * point_value + pos.get('swap', 0)
            floating_pl += profit
            
            # Calcolo Margine (Prezzo / Leva * Lotti * ContractSize)
            margin = (pos['entry_price'] * 20 * pos['lots']) / self.leverage_default
            used_margin += margin

        equity = self.balance + floating_pl
        free_margin = equity - used_margin
        
        return {
            "balance": self.balance,
            "equity": equity,
            "floating_pl": floating_pl,
            "used_margin": used_margin,
            "free_margin": free_margin,
            "positions_count": len(self.open_positions)
        }

    def get_positions(self):
        return self.open_positions

    def get_asset_specs(self, ticker):
        """
        Restituisce le specifiche dell'asset (Leva, Contract Size).
        Mappa fondamentale per il Risk Engine.
        """
        specs = {
            "NQ100": {"leverage": 50, "contract_size": 20, "tick_value": 0.25}, # 20$ a punto per 1 lotto
            "SPX500": {"leverage": 50, "contract_size": 50, "tick_value": 0.25},
            "BTCUSD": {"leverage": 10, "contract_size": 1, "tick_value": 1.0}, # Crypto leva più bassa
            "EURUSD": {"leverage": 100, "contract_size": 100000, "tick_value": 1.0},
            "XAUUSD": {"leverage": 50, "contract_size": 100, "tick_value": 1.0},
        }
        # Default fallback
        return specs.get(ticker, {"leverage": 20, "contract_size": 10, "tick_value": 1.0})