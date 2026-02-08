class SurvivalRiskEngine:
    def __init__(self, broker_interface):
        self.broker = broker_interface

    def calculate_phantom_equity(self):
        """
        Calcola l'Equity nello scenario peggiore (Tutti i trade vanno a SL ora).
        """
        account = self.broker.get_account_info()
        positions = self.broker.get_positions()
        
        current_equity = account['equity']
        potential_future_loss = 0.0
        
        for pos in positions:
            sl = pos.get('stop_loss')
            if not sl:
                # SE MANCA LO STOP LOSS, IL RISCHIO È INFINITO.
                # Per sicurezza assumiamo un crash del 50% (Survival Mode)
                continue 
            
            # Calcolo perdita se tocca SL dal prezzo ATTUALE
            if pos['type'] == 'LONG':
                loss_dist = pos['current_price'] - sl
            else:
                loss_dist = sl - pos['current_price']
            
            # Se loss_dist è negativa, significa che lo SL è già "oltre" il prezzo (impossibile)
            # O che siamo in profitto e lo SL è in profitto (Trailing).
            # Se SL garantisce profitto, potential_loss è negativa (cioè è un guadagno garantito).
            # Se SL è in perdita, potential_loss è positiva (soldi che perderò).
            
            # Qui ci interessa: quanti soldi PERDO rispetto all'EQUITY DI ADESSO se tocco SL?
            # Esempio: Equity 300. Profitto aperto 100. SL a Breakeven.
            # Se scende a SL, perdo i 100 di profitto. Equity torna a 200.
            
            point_value = self.broker.get_asset_specs(pos['symbol'])['contract_size'] * pos['lots']
            
            # La perdita latente è la differenza tra Valore Attuale e Valore a SL
            money_at_risk = loss_dist * point_value
            potential_future_loss += money_at_risk

        # La Phantom Equity è l'Equity attuale meno tutto quello che posso perdere
        # se il mercato va contro fino agli SL.
        phantom_equity = current_equity - potential_future_loss
        return phantom_equity

    def check_trade_feasibility(self, ticker, direction, entry_price, stop_loss_price):
        """
        Simula se il conto sopravvive all'apertura del nuovo trade.
        """
        account = self.broker.get_account_info()
        specs = self.broker.get_asset_specs(ticker)
        
        # 1. Calcolo Spazio Vitale (Phantom Equity - Margine Usato)
        phantom_eq = self.calculate_phantom_equity()
        survival_space = phantom_eq - account['used_margin']
        
        if survival_space <= 0:
            return {
                "allowed": False, 
                "reason": "❌ NO OXYGEN: Il tuo conto è già a rischio Margin Call sugli SL esistenti."
            }

        # 2. Calcolo Costo per 1 Microlotto (0.01)
        min_lot = 0.01
        contract_value = specs['contract_size'] * min_lot
        
        # A. Margine richiesto per 0.01
        required_margin = (entry_price * contract_value) / specs['leverage']
        
        # B. Rischio Monetario per 0.01 (Distanza Entry - SL)
        dist = abs(entry_price - stop_loss_price)
        monetary_risk = dist * contract_value
        
        # Costo Totale "Impatto" = Margine che blocco + Soldi che potrei perdere
        total_impact_per_micro = required_margin + monetary_risk
        
        # 3. Calcolo Max Size
        if total_impact_per_micro <= 0: return {"allowed": False, "reason": "Errore Dati SL"}
        
        max_microlots = int(survival_space / total_impact_per_micro)
        max_lots = max_microlots * 0.01
        
        if max_lots < 0.01:
            return {
                "allowed": False,
                "reason": f"❌ POVERTY: Hai ${survival_space:.2f} di spazio vitale. Servono ${total_impact_per_micro:.2f} per il trade minimo."
            }
            
        return {
            "allowed": True,
            "max_lots": round(max_lots, 2),
            "margin_required": round(required_margin * (max_lots/0.01), 2),
            "risk_monetary": round(monetary_risk * (max_lots/0.01), 2),
            "survival_equity": round(survival_space, 2)
        }