from typing import List, Dict, Any, cast
import json
from .connection import get_db_client

class MarketRepository:
    def __init__(self):
        self.client = get_db_client()

    def video_exists(self, url: str) -> bool:
        res = self.client.table("intelligence_feed").select("id").eq("url", url).execute()
        return len(res.data) > 0

    def get_source_id(self, name: str, base_url: str = "") -> int:
        res = self.client.table("sources").select("id").eq("name", name).execute()
        if res.data and len(res.data) > 0:
            return int(cast(Dict[str, Any], res.data[0]).get('id', 0))
        
        payload = {"name": name}
        if base_url: payload["base_url"] = base_url
        new = self.client.table("sources").insert(payload).execute()
        
        if new.data:
            return int(cast(Dict[str, Any], new.data[0]).get('id', 0))
        raise Exception(f"Failed to source ID for: {name}")

    def save_analysis_transaction(self, video_data: Dict[str, Any], analysis: Dict[str, Any]):
            """
            Salva il video e tutti gli insights estratti in un'unica transazione logica.
            Include normalizzazione dei ticker e pulizia dei dati per i vincoli del DB.
            """
            # 1. Mappa di normalizzazione per garantire coerenza con la tabella 'assets'
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

            # Valori ammessi nel DB (Check Constraints)
            ALLOWED_REC = ['LONG', 'SHORT', 'WATCH', 'HOLD']

            try:
                # --- STEP 1: GESTIONE SORGENTE ---
                channel_name = video_data.get('ch_title', 'Unknown Channel')
                search_url = f"https://www.youtube.com/results?search_query={channel_name.replace(' ', '+')}"
                source_id = self.get_source_id(channel_name, base_url=search_url)

                # --- STEP 2: SALVATAGGIO FEED (VIDEO) ---
                feed_payload = {
                    "source_id": source_id,
                    "title": video_data['title'],
                    "url": video_data['url'],
                    "published_at": video_data['date'],
                    "content": video_data.get('content', '')[:100000],
                    "summary": analysis.get("video_summary", "N/A"),
                    "macro_sentiment": analysis.get("macro_sentiment", "NEUTRAL"),
                    "raw_metadata": {"vid": video_data['id']}
                }
                
                res_feed = self.client.table("intelligence_feed").insert(feed_payload).execute()
                if not res_feed.data:
                    raise Exception("Errore durante l'inserimento del feed.")
                
                video_db_id = int(cast(Dict[str, Any], res_feed.data[0]).get('id', 0))
                print(f"      💾 DB: Feed salvato (ID: {video_db_id})")

                # --- STEP 3: SALVATAGGIO INSIGHTS (ASSET) ---
                assets_list = analysis.get("assets", [])
                if not assets_list:
                    print("      ⚠️ Nessun asset trovato dall'AI in questo video.")
                    return

                rows_to_insert = []
                for item in assets_list:
                    # A. Normalizzazione Ticker
                    raw_ticker = str(item.get("asset_ticker", "UNKNOWN")).upper().strip()
                    clean_ticker = TICKER_FIX.get(raw_ticker, raw_ticker)

                    # B. Normalizzazione Recommendation (Fix per HOLD/BUY o simili)
                    raw_rec = str(item.get("recommendation", "WATCH")).upper().strip()
                    if "LONG" in raw_rec or "BUY" in raw_rec: clean_rec = "LONG"
                    elif "SHORT" in raw_rec or "SELL" in raw_rec: clean_rec = "SHORT"
                    elif "HOLD" in raw_rec: clean_rec = "HOLD"
                    else: clean_rec = "WATCH"
                    
                    # C. Normalizzazione Sentiment
                    raw_sent = str(item.get("sentiment", "Neutral/Range")).strip()
                    # Assicuriamoci che non sia troppo lungo e segua il formato
                    if "Bull" in raw_sent: clean_sent = "Bullish"
                    elif "Bear" in raw_sent: clean_sent = "Bearish"
                    else: clean_sent = "Neutral/Range"

                    # D. Preparazione riga
                    rows_to_insert.append({
                        "video_id": video_db_id,
                        "asset_ticker": clean_ticker[:10], # Taglio precauzionale
                        "asset_name": item.get("asset_name", ""),
                        "channel_style": item.get("channel_style", "Fondamentale"),
                        "sentiment": clean_sent,
                        "recommendation": clean_rec,
                        "time_horizon": item.get("time_horizon", "Medium Term"),
                        "entry_zone": item.get("entry_zone"),
                        "target_price": item.get("target_price"),
                        "stop_invalidation": item.get("stop_invalidation"),
                        "key_drivers": item.get("key_drivers", []), # JSONB
                        "summary_card": item.get("summary_card", "")[:500]
                    })

                if rows_to_insert:
                    self.client.table("market_insights").insert(rows_to_insert).execute()
                    print(f"      💾 DB: Salvati {len(rows_to_insert)} insights operativi per {len(assets_list)} asset.")
                    
            except Exception as e:
                print(f"      ❌ DB Error Transaction: {e}")

    def get_all_insights_flat(self) -> List[Dict[str, Any]]:
        try:
            response = self.client.table("market_insights")\
                .select("*, intelligence_feed(*, sources(name))")\
                .order("created_at", desc=True)\
                .execute()
            
            flat_data = []
            for item in (response.data or []):
                item = cast(Dict[str, Any], item)
                feed = item.pop('intelligence_feed', {}) or {}
                source = feed.get('sources', {}) or {}
                
                # Mapping dei dati piatti
                item['source_name'] = source.get('name', 'Unknown')
                item['video_title'] = feed.get('title')
                item['published_at'] = feed.get('published_at')
                item['video_url'] = feed.get('url')
                item['video_summary'] = feed.get('summary')
                item['video_macro'] = feed.get('macro_sentiment')
                
                flat_data.append(item)
            return flat_data
        except Exception as e:
            print(f"❌ DB Fetch Error: {e}")
            return []