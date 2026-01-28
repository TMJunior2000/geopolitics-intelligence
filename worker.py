import os
import json
import time
from typing import cast, List, Dict, Any, Optional

from apify_client import ApifyClient
from googleapiclient.discovery import build
from google import genai
from google.genai import types
from supabase import create_client, Client

# --- CONFIGURAZIONE ---
print("\n🔧 [INIT] Avvio script (APIFY MODE)...")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
APIFY_TOKEN = os.getenv("APIFY_TOKEN")

if not all([SUPABASE_URL, SUPABASE_KEY, GOOGLE_API_KEY, APIFY_TOKEN]):
    print("❌ ERRORE: Variabili d'ambiente mancanti.")
    exit(1)

try:
    # Cast esplicito per evitare errori di tipo None su supabase
    supabase: Client = create_client(cast(str, SUPABASE_URL), cast(str, SUPABASE_KEY))
    gemini_client = genai.Client(api_key=GOOGLE_API_KEY)
    youtube_service = build('youtube', 'v3', developerKey=GOOGLE_API_KEY)
    apify_client = ApifyClient(APIFY_TOKEN)
    print("✅ Client inizializzati.")
except Exception as e:
    print(f"❌ ERRORE INIT: {e}")
    exit(1)

YOUTUBE_CHANNELS = ["@InvestireBiz"]

# --- ESTRAZIONE TRASCRIZIONE CON APIFY ---
def get_transcript_apify(video_url: str) -> str:
    print(f"   ☁️ [APIFY] Richiesta trascrizione per: {video_url}...")
    
    run_input = {
        "videoUrls": [video_url],
        "subtitlesLanguage": "it",
        "addVideoMetadata": False
    }

    try:
        run = apify_client.actor("stream_99/youtube-transcript-scraper").call(run_input=run_input)
        if not run: return ""
        
        transcript_text = ""
        # iterate_items restituisce un generatore di oggetti, dobbiamo assicurarci che siano dict
        for item in apify_client.dataset(run["defaultDatasetId"]).iterate_items():
            if isinstance(item, dict):
                # Usiamo .get() invece delle parentesi quadre per sicurezza
                transcript_text = item.get("transcript") or item.get("text") or ""
                if transcript_text: break
        
        if transcript_text:
            print(f"      ✅ Trascrizione ottenuta ({len(transcript_text)} chars)")
            return str(transcript_text)
        return ""

    except Exception as e:
        print(f"      ❌ Errore Apify: {e}")
        return ""

# --- ANALISI GEMINI ---
def analyze_gemini(text: str) -> dict:
    if not text or len(text) < 50: return {"summary": "N/A"}
    print(f"   🧠 [AI] Analisi con Gemini...")
    for attempt in range(3):
        try:
            res = gemini_client.models.generate_content(
                model="gemini-flash-latest",
                contents=f'Analizza JSON: {{ "summary": "Riassunto", "risk_level": "LOW", "countries_involved": [], "key_takeaway": "Main" }}\nTEXT:{text[:28000]}',
                config=types.GenerateContentConfig(response_mime_type="application/json")
            )
            # res.text può essere None, quindi usiamo un fallback
            text_response = res.text or "{}"
            return cast(dict, json.loads(text_response.strip()))
        except Exception as e:
            if "429" in str(e): 
                time.sleep(35)
            else: return {}
    return {}

# --- GESTIONE DB ---
def get_source_id(name: str, ch_id: str) -> Optional[str]:
    try:
        # Specifichiamo a Pylance che res.data è una lista di dizionari
        res = supabase.table("sources").select("id").eq("name", name).execute()
        data = cast(List[Dict[str, Any]], res.data)
        
        if data and len(data) > 0: 
            return str(data[0].get('id'))
        
        new = supabase.table("sources").insert({"name": name, "type": "youtube", "base_url": ch_id}).execute()
        new_data = cast(List[Dict[str, Any]], new.data)
        
        if new_data and len(new_data) > 0: 
            return str(new_data[0].get('id'))
    except Exception as e:
        print(f"   ❌ Errore Source ID: {e}")
    return None

def get_channel_videos(handle: str) -> List[Dict[str, Any]]:
    videos = []
    try:
        res = youtube_service.channels().list(part="contentDetails,snippet", forHandle=handle).execute()
        items = res.get('items', [])
        if not items: return []
        
        ch_title = items[0]['snippet']['title']
        ch_id = items[0]['id']
        upl_id = items[0]['contentDetails']['relatedPlaylists']['uploads']
        
        pl = youtube_service.playlistItems().list(part="snippet", playlistId=upl_id, maxResults=5).execute()
        for i in pl.get('items', []):
            snippet = i.get('snippet', {})
            vid_id = snippet.get('resourceId', {}).get('videoId')
            videos.append({
                "id": vid_id,
                "title": snippet.get('title'),
                "desc": snippet.get('description'),
                "date": snippet.get('publishedAt'),
                "url": f"https://www.youtube.com/watch?v={vid_id}",
                "ch_title": ch_title, "ch_id": ch_id
            })
    except Exception as e:
        print(f"❌ Errore YouTube API: {e}")
    return videos

# --- MAIN ---
if __name__ == "__main__":
    print("\n--- 🚀 START WORKER ---")
    
    for handle in YOUTUBE_CHANNELS:
        videos = get_channel_videos(handle)
        
        for v in videos:
            print(f"\n🔄 Video: {v['title'][:40]}...")
            
            try:
                check = supabase.table("intelligence_feed").select("id").eq("url", v['url']).execute()
                if check.data and len(cast(list, check.data)) > 0:
                    print("   ⏭️  Già presente."); continue
            except: pass

            text = get_transcript_apify(v['url'])
            method = "Apify-Transcript"
            
            if not text:
                text = f"{v['title']}\n{v['desc']}"
                method = "YouTube-Description"

            analysis = analyze_gemini(text)
            sid = get_source_id(str(v['ch_title']), str(v['ch_id']))
            
            if sid:
                try:
                    supabase.table("intelligence_feed").insert({
                        "source_id": sid,
                        "title": v['title'],
                        "url": v['url'],
                        "published_at": v['date'],
                        "content": text,
                        "analysis": analysis,
                        "raw_metadata": {"vid": v['id'], "method": method}
                    }).execute()
                    print(f"   💾 SALVATO")
                except Exception as e:
                    print(f"   ❌ DB: {e}")
            
            time.sleep(2)

    print("\n--- ✅ FINITO ---")