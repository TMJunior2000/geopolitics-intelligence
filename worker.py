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

def get_recent_videos(handle: str, max_results: int = 3):
    """Ottiene video recenti usando API YouTube ufficiali."""
    videos = []
    try:
        res = yt_service.channels().list(part="contentDetails,snippet", forHandle=handle).execute()
        if not res.get('items'): return []
        
        upl_id = res['items'][0]['contentDetails']['relatedPlaylists']['uploads']
        ch_title = res['items'][0]['snippet']['title']
        
        pl = yt_service.playlistItems().list(part="snippet", playlistId=upl_id, maxResults=max_results).execute()
        for i in pl.get('items', []):
            snippet = i['snippet']
            v_id = snippet['resourceId']['videoId']
            videos.append({
                "id": v_id,
                "title": snippet['title'],
                "date": snippet['publishedAt'],
                "url": f"https://www.youtube.com/watch?v={v_id}",
                "ch_title": ch_title
            })
    except Exception as e:
        print(f"❌ Errore YouTube API: {e}")
    return videos

def run_pipeline(backfill_mode=False):
    print(f"\n🚀 AVVIO WORKER | Mode: {'BACKFILL' if backfill_mode else 'LIVE'}")
    limit = 50 if backfill_mode else 3
    
    for handle in Config.YOUTUBE_HANDLES:
        print(f"\n🔍 Canale: {handle}")
        videos = get_recent_videos(handle, max_results=limit)
        
        for v in videos:
            print(f"\n🔄 Video: {v['title'][:50]}...")
            
            # 1. Check Esistenza
            if db_svc.video_exists(v['url']):
                print("   ⏭️  Skipped (Già presente)")
                continue
                
            # 2. Scraping
            text = apify_svc.get_transcript(v['url'])
            if not text:
                print("   ⚠️ No transcript. Skip analysis.")
                continue
            
            # Arricchiamo l'oggetto video con il testo
            v['content'] = text
            
            # 3. AI Analysis
            analysis = ai_svc.analyze_video(text)
            if not analysis:
                print("   ⚠️ AI Analysis failed.")
                continue
                
            # 4. Save to DB
            db_svc.save_analysis(v, analysis)
            
            # Rate limiting gentile
            time.sleep(2)

if __name__ == "__main__":
    # Puoi passare argomenti da riga di comando per attivare il backfill
    run_pipeline(backfill_mode=False)