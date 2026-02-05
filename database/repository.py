from typing import List, Dict, Any, cast
import json
from .connection import get_db_client

class MarketRepository:
    def __init__(self):
        self.client = get_db_client()

    def video_exists(self, url: str) -> bool:
        """Controlla se un URL (Video o Post) esiste già nel feed."""
        res = self.client.table("intelligence_feed").select("id").eq("url", url).execute()
        return len(res.data) > 0

    def get_source_id(self, name: str, base_url: str = "") -> int:
        """Recupera o crea una Fonte (Canale YT o Social)."""
        res = self.client.table("sources").select("id").eq("name", name).execute()
        if res.data and len(res.data) > 0:
            return int(cast(Dict[str, Any], res.data[0]).get('id', 0))
        
        # Se non esiste, la crea (Default category sarà 'VIDEO_ANALYSIS' dal DB)
        payload = {"name": name}
        if base_url: payload["base_url"] = base_url
        new = self.client.table("sources").insert(payload).execute()
        
        if new.data:
            return int(cast(Dict[str, Any], new.data[0]).get('id', 0))
        raise Exception(f"Failed to get source ID for: {name}")

    def _ensure_asset_exists(self, ticker: str):
        """
        Metodo Helper (Auto-Healing):
        Verifica se un ticker esiste nella tabella 'assets'.
        Se non esiste, lo crea al volo come 'MACRO' o 'CRYPTO' generico per evitare errori di Foreign Key.
        """
        ticker = ticker.strip().upper()
        # Mappa rudimentale per indovinare il tipo se non lo conosciamo
        guessed_type = "CRYPTO" if "USD" in ticker and len(ticker) > 6 else "MACRO"
        
        try:
            # Tenta un upsert 'soft': se c'è già non fa nulla (grazie a ON CONFLICT nel DB), se manca lo crea.
            payload = {
                "ticker": ticker,
                "name": f"{ticker} (Auto-Detected)",
                "type": guessed_type 
            }
            # Nota: Supabase-py upsert richiede on_conflict se vogliamo ignorare duplicati senza errori
            self.client.table('assets').upsert(payload, on_conflict='ticker').execute()
        except Exception as e:
            # Log leggero, non blocchiamo il flusso per questo
            print(f"      ⚠️ Warning asset '{ticker}': {e}")

    def save_trump_signal(self, signal_data: Dict[str, Any]):
        """
        Salva un segnale da Truth Social (Trump Watch).
        Gestisce le nuove colonne 'impact_score' e 'feed_type'.
        """
        ai_data = signal_data.get('ai_analysis', {})
        summary = ai_data.get('summary_it', 'N/A')
        
        print(f"   💾 DB: Salvataggio Trump Signal -> {summary}")

        try:
            # 1. Recupera ID Fonte (Truth Social)
            source_id = self.get_source_id("Truth Social", "https://truthsocial.com")

            # 2. Salva il Feed (Post)
            # Trump non ha titoli, usiamo un estratto
            content_text = signal_data.get('content', '')
            fake_title = f"Truth: {content_text[:40]}..." if content_text else "Trump Truth Post"

            feed_payload = {
                "source_id": source_id,
                "url": signal_data['url'],
                "title": fake_title,
                "published_at": signal_data['created_at'],
                "content": content_text,
                "feed_type": "SOCIAL_POST",           # NUOVO CAMPO
                "summary": summary,
                "macro_sentiment": ai_data.get('trade_direction', 'NEUTRAL'),
                "raw_metadata": ai_data               # Backup JSON completo
            }

            # Upsert su URL
            res_feed = self.client.table("intelligence_feed").upsert(feed_payload, on_conflict='url').execute()
            
            if not res_feed.data:
                print("      ❌ Errore DB: Impossibile salvare il Feed Trump.")
                return

            feed_id = int(cast(Dict[str, Any], res_feed.data[0]).get('id', 0))

            # 3. Salva gli Insights (Impatto su Asset)
            assets_list = ai_data.get('assets_affected', [])
            
            # Fallback se l'AI non trova asset ma lo score è alto
            if not assets_list and ai_data.get('impact_score', 0) >= 4:
                assets_list = ['USD']

            saved_count = 0
            for ticker in assets_list:
                clean_ticker = str(ticker).strip().upper()
                
                # AUTO-HEALING: Crea l'asset se non esiste
                self._ensure_asset_exists(clean_ticker)

                insight_payload = {
                    "video_id": feed_id,
                    "asset_ticker": clean_ticker,
                    "asset_name": f"{clean_ticker} (Trump Target)",
                    "channel_style": "Macro/Geopolitics",
                    "sentiment": ai_data.get('trade_direction'),
                    "recommendation": "WATCH",
                    "time_horizon": "News_Event",
                    "impact_score": ai_data.get('impact_score', 3), # NUOVO CAMPO
                    "summary_card": f"🚨 TRUMP: {summary}",
                    "confidence_score": 5
                }

                self.client.table('market_insights').insert(insight_payload).execute()
                saved_count += 1

            print(f"      ✅ Successo! Feed ID: {feed_id} | Insights creati: {saved_count}")

        except Exception as e:
            print(f"      ⚠️ CRITICAL DB ERROR (Trump): {e}")

    def save_analysis_transaction(self, video_data: Dict[str, Any], analysis: Dict[str, Any]):
        """
        Salva video YouTube e insights.
        Aggiornato per usare _ensure_asset_exists e feed_type.
        """
        # Mappa di normalizzazione storica
        TICKER_FIX = {
            "NQ": "NQ100", "NAS100": "NQ100", "NASDAQ": "NQ100", "NAS": "NQ100",
            "ES": "SPX500", "US500": "SPX500", "S&P500": "SPX500", "SPX": "SPX500",
            "DOW": "DJ30", "US30": "DJ30", "YM": "DJ30",
            "EU": "EURUSD", "GU": "GBPUSD", "UJ": "USDJPY", "UC": "USDCHF",
            "GOLD": "XAUUSD", "ORO": "XAUUSD", "SILVER": "XAGUSD", "ARGENTO": "XAGUSD",
            "OIL": "WTI", "PETROLIO": "WTI", "BRENT": "BRENT",
            "BTC": "BTCUSD", "ETH": "ETHUSD", "SOL": "SOLUSD",
            "US10Y": "US10Y", "DXY": "DXY", "DOLLARO": "DXY"
        }

        try:
            # 1. Gestione Sorgente
            channel_name = video_data.get('ch_title', 'Unknown Channel')
            search_url = f"https://www.youtube.com/results?search_query={channel_name.replace(' ', '+')}"
            source_id = self.get_source_id(channel_name, base_url=search_url)

            # 2. Salvataggio Feed (Video)
            feed_payload = {
                "source_id": source_id,
                "title": video_data['title'],
                "url": video_data['url'],
                "published_at": video_data['date'],
                "content": video_data.get('content', '')[:100000],
                "feed_type": "VIDEO",  # Esplicito
                "summary": analysis.get("video_summary", "N/A"),
                "macro_sentiment": analysis.get("macro_sentiment", "NEUTRAL"),
                "raw_metadata": {"vid": video_data['id']}
            }
            
            res_feed = self.client.table("intelligence_feed").insert(feed_payload).execute()
            if not res_feed.data:
                raise Exception("Errore durante l'inserimento del feed.")
            
            video_db_id = int(cast(Dict[str, Any], res_feed.data[0]).get('id', 0))
            print(f"      💾 DB: Feed salvato (ID: {video_db_id})")

            # 3. Salvataggio Insights
            assets_list = analysis.get("assets", [])
            if not assets_list:
                print("      ⚠️ Nessun asset trovato dall'AI in questo video.")
                return

            rows_to_insert = []
            for item in assets_list:
                # A. Normalizzazione Ticker
                raw_ticker = str(item.get("asset_ticker", "UNKNOWN")).upper().strip()
                clean_ticker = TICKER_FIX.get(raw_ticker, raw_ticker)

                # AUTO-HEALING: Crea asset se manca (Fix Foreign Key Error)
                self._ensure_asset_exists(clean_ticker)

                # B. Normalizzazione Recommendation
                raw_rec = str(item.get("recommendation", "WATCH")).upper().strip()
                if "LONG" in raw_rec or "BUY" in raw_rec: clean_rec = "LONG"
                elif "SHORT" in raw_rec or "SELL" in raw_rec: clean_rec = "SHORT"
                elif "HOLD" in raw_rec: clean_rec = "HOLD"
                else: clean_rec = "WATCH"
                
                # C. Normalizzazione Sentiment
                raw_sent = str(item.get("sentiment", "Neutral/Range")).strip()
                if "Bull" in raw_sent: clean_sent = "Bullish"
                elif "Bear" in raw_sent: clean_sent = "Bearish"
                else: clean_sent = "Neutral/Range"

                # D. Preparazione riga
                rows_to_insert.append({
                    "video_id": video_db_id,
                    "asset_ticker": clean_ticker[:10],
                    "asset_name": item.get("asset_name", ""),
                    "channel_style": item.get("channel_style", "Fondamentale"),
                    "sentiment": clean_sent,
                    "recommendation": clean_rec,
                    "time_horizon": item.get("time_horizon", "Medium Term"),
                    "entry_zone": item.get("entry_zone"),
                    "target_price": item.get("target_price"),
                    "stop_invalidation": item.get("stop_invalidation"),
                    "key_drivers": item.get("key_drivers", []),
                    "summary_card": item.get("summary_card", "")[:500],
                    "impact_score": 0 # Default per i video normali
                })

            if rows_to_insert:
                self.client.table("market_insights").insert(rows_to_insert).execute()
                print(f"      💾 DB: Salvati {len(rows_to_insert)} insights operativi.")
                
        except Exception as e:
            print(f"      ❌ DB Error Transaction: {e}")

    def get_all_insights_flat(self) -> List[Dict[str, Any]]:
        """
        Recupera tutti gli insights per la Dashboard.
        """
        try:
            response = self.client.table("market_insights")\
                .select("*, intelligence_feed!inner(*, sources(name))")\
                .order("published_at", foreign_table="intelligence_feed", desc=True)\
                .execute()
            
            flat_data = []
            for item in (response.data or []):
                item = cast(Dict[str, Any], item)
                feed = item.pop('intelligence_feed', {}) or {}
                source = feed.get('sources', {}) or {}
                
                # Mapping dei dati piatti per Streamlit
                item['source_name'] = source.get('name', 'Unknown')
                item['video_title'] = feed.get('title')
                item['published_at'] = feed.get('published_at')
                item['video_url'] = feed.get('url')
                item['video_summary'] = feed.get('summary')
                item['video_macro'] = feed.get('macro_sentiment')
                
                # Nuovi Campi Esposti
                item['feed_type'] = feed.get('feed_type', 'VIDEO') 
                item['impact_score'] = item.get('impact_score', 0)
                
                flat_data.append(item)
            return flat_data
        except Exception as e:
            print(f"❌ DB Fetch Error: {e}")
            return []