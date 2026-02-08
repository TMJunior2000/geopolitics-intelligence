import pandas as pd

class TrafficLightSystem:
    def __init__(self, broker):
        self.broker = broker

    def analyze_portfolio(self, latest_insights_df):
        """
        Confronta posizioni aperte con insights recenti.
        Restituisce una lista di 'Azioni Consigliate'.
        """
        positions = self.broker.get_positions()
        actions = []

        if latest_insights_df.empty:
            return []

        for pos in positions:
            ticker = pos['symbol']
            
            # Cerca insights recenti per questo ticker
            relevant_news = latest_insights_df[latest_insights_df['asset_ticker'] == ticker]
            
            if relevant_news.empty:
                continue
                
            # Prendi la più recente
            latest_card = relevant_news.iloc[0]
            card_sentiment = str(latest_card.get('recommendation', 'WATCH')).upper()
            
            # Logica Semaforo
            my_dir = pos['type'] # LONG o SHORT
            
            status = "GREEN"
            message = "Trend Confermato. Mantieni."
            
            # Caso 1: Conflitto Diretto (Rosso)
            if (my_dir == "LONG" and "SHORT" in card_sentiment) or \
               (my_dir == "SHORT" and "LONG" in card_sentiment):
                status = "RED"
                message = f"🚨 INVERSIONE: Insight recente suggerisce {card_sentiment}. Valuta uscita."
            
            # Caso 2: Incertezza (Giallo)
            elif "WATCH" in card_sentiment:
                status = "YELLOW"
                message = "⚠️ ATTESA: Il mercato è laterale. Stringi Stop Loss."
            
            actions.append({
                "ticker": ticker,
                "my_pos": my_dir,
                "insight": card_sentiment,
                "status": status,
                "msg": message,
                "card_summary": latest_card.get('summary_card', '...')
            })
            
        return actions