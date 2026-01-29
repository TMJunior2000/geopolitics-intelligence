import os
import time
from datetime import datetime
from googleapiclient.discovery import build
from config import Config
from services.apify_service import ApifyService
from services.ai_service import AIService
from services.db_service import DBService

# Setup Servizi
apify_svc = ApifyService()
ai_svc = AIService()
db_svc = DBService()
yt_service = build('youtube', 'v3', developerKey=Config.GOOGLE_API_KEY)

# --- FUNZIONE LIVE (Veloce, pochi video) ---
def get_live_videos(handle: str, max_results: int = 3):
    videos = []
    try:
        res = yt_service.channels().list(part="contentDetails,snippet", forHandle=handle).execute()
        if not res.get('items'): return []
        upl_id = res['items'][0]['contentDetails']['relatedPlaylists']['uploads']
        ch_title = res['items'][0]['snippet']['title']
        
        pl = yt_service.playlistItems().list(part="snippet", playlistId=upl_id, maxResults=max_results).execute()
        for i in pl.get('items', []):
            videos.append({
                "id": i['snippet']['resourceId']['videoId'],
                "title": i['snippet']['title'],
                "date": i['snippet']['publishedAt'],
                "url": f"https://www.youtube.com/watch?v={i['snippet']['resourceId']['videoId']}",
                "ch_title": ch_title
            })
    except Exception as e:
        print(f"❌ Errore YouTube Live: {e}")
    return videos

# --- FUNZIONE BACKFILL (Profonda, filtro date) ---
def get_backfill_videos(handle: str):
    videos = []
    # Date hardcoded per il tuo bisogno specifico (o configurabili)
    START_DATE = datetime(2026, 1, 27)
    END_DATE = datetime(2026, 1, 28, 23, 59, 59)
    
    print(f"   📅 Backfill range: {START_DATE.date()} -> {END_DATE.date()}")

    try:
        res = yt_service.channels().list(part="contentDetails,snippet", forHandle=handle).execute()
        if not res.get('items'): return []
        upl_id = res['items'][0]['contentDetails']['relatedPlaylists']['uploads']
        ch_title = res['items'][0]['snippet']['title']
        
        next_page_token = None
        searching = True
        
        while searching:
            pl = yt_service.playlistItems().list(
                part="snippet", playlistId=upl_id, maxResults=50, pageToken=next_page_token
            ).execute()
            
            for i in pl.get('items', []):
                pub_str = i['snippet']['publishedAt']
                # Parsifica la data (ISO 8601)
                pub_dt = datetime.strptime(pub_str, "%Y-%m-%dT%H:%M:%SZ")
                
                if START_DATE <= pub_dt <= END_DATE:
                    videos.append({
                        "id": i['snippet']['resourceId']['videoId'],
                        "title": i['snippet']['title'],
                        "date": pub_str,
                        "url": f"https://www.youtube.com/watch?v={i['snippet']['resourceId']['videoId']}",
                        "ch_title": ch_title
                    })
                elif pub_dt < START_DATE:
                    print(f"      🛑 Trovato video del {pub_dt.date()} (precedente al target). Stop.")
                    searching = False
                    break
            
            next_page_token = pl.get('nextPageToken')
            if not next_page_token: break
            
    except Exception as e:
        print(f"❌ Errore YouTube Backfill: {e}")
    return videos

# --- PIPELINE PRINCIPALE ---
def run_pipeline(mode: str):
    print(f"\n🚀 AVVIO WORKER | Mode: {mode}")
    
    for handle in Config.YOUTUBE_HANDLES:
        print(f"\n🔍 Canale: {handle}")
        
        if mode == "BACKFILL":
            videos = get_backfill_videos(handle)
        else:
            videos = get_live_videos(handle, max_results=3)
            
        print(f"   📹 Trovati {len(videos)} video da processare.")
        
        for v in videos:
            print(f"\n🔄 [{mode}] Video: {v['title'][:40]} ({v['date']})")
            
            if db_svc.video_exists(v['url']):
                print("   ⏭️  Già nel DB. Salto.")
                continue
                
            text = apify_svc.get_transcript(v['url'])
            if not text:
                print("   ⚠️ No transcript. Skip.")
                continue
            
            v['content'] = text
            analysis = ai_svc.analyze_video(text)
            
            if analysis:
                db_svc.save_analysis(v, analysis)
            
            time.sleep(2) # Pausa gentile

if __name__ == "__main__":
    # Legge la variabile d'ambiente impostata da GitHub Actions
    # Se non c'è, default è LIVE
    mode = os.getenv("WORKER_MODE", "LIVE").upper()
    run_pipeline(mode)