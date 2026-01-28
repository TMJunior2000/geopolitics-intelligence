import os
import json
import time
from typing import cast, List, Dict, Any

# Libreria Apify
from apify_client import ApifyClient

from googleapiclient.discovery import build
from google import genai
from google.genai import types
from supabase import create_client, Client

# --- SETUP ---
print("\n🔧 [INIT] Avvio script (APIFY MODE)...")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
APIFY_TOKEN = os.getenv("APIFY_TOKEN")

if not SUPABASE_URL or not SUPABASE_KEY or not GOOGLE_API_KEY or not APIFY_TOKEN:
    print("❌ ERRORE: Variabili mancanti (serve APIFY_TOKEN).")
    exit(1)

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    gemini_client = genai.Client(api_key=GOOGLE_API_KEY)
    youtube_service = build('youtube', 'v3', developerKey=GOOGLE_API_KEY)
    # Init Apify
    apify_client = ApifyClient(APIFY_TOKEN)
    print("✅ Client inizializzati.")
except Exception as e:
    print(f"❌ ERRORE INIT: {e}")
    exit(1)

YOUTUBE_CHANNELS = ["@InvestireBiz"]

# --- FUNZIONE TRASCRITTO (APIFY) ---
def get_transcript_apify(video_url: str) -> str:
    print(f"   🤖 [APIFY] Chiedo trascrizione per {video_url}...")
    
    # Questo attore è specifico per i transcript e costa pochissimo
    actor_id = "undoshort/youtube-transcript-scraper"
    
    run_input = {
        "videoUrls": [video_url],
        "preferredLanguage": "it",
        "fallbackLanguage": "en",
        "includeTimestamps": False
    }

    try:
        # 1. Avvia l'attore sui server Apify
        run = apify_client.actor(actor_id).call(run_input=run_input)
        
        # 2. Recupera i risultati dal dataset
        dataset_items = apify_client.dataset(run["defaultDatasetId"]).list_items().items
        
        if dataset_items:
            # Prende il primo risultato
            item = dataset_items[0]
            text = item.get("text") or item.get("transcript") or ""
            
            # Se è una lista di segmenti, uniscili
            if isinstance(text, list):
                text = " ".join([seg.get('text', '') for seg in text if 'text' in seg])
            
            if len(text) > 50:
                print(f"      ✅ Testo ricevuto: {len(text)} caratteri.")
                return text
            else:
                print("      ⚠️ Apify ok, ma testo vuoto.")
        else:
            print("      ⚠️ Nessun dato restituito da Apify.")
            
    except Exception as e:
        print(f"      ❌ Errore Apify: {e}")
        
    return ""

# --- ANALISI GEMINI ---
def analyze_gemini(text: str) -> dict:
    if not text or len(text) < 50: return {"summary": "N/A"}
    print(f"   🧠 [AI] Invio {len(text)} chars...")
    for attempt in range(3):
        try:
            res = gemini_client.models.generate_content(
                model="gemini-2.0-flash",
                contents=f'Analizza JSON: {{ "summary": "Riassunto", "risk_level": "LOW", "countries_involved": [], "key_takeaway": "Main" }}\nTEXT:{text[:28000]}',
                config=types.GenerateContentConfig(response_mime_type="application/json")
            )
            return json.loads(res.text.replace("```json","").replace("```","").strip())
        except Exception as e:
            if "429" in str(e): 
                print("      ⚠️ Quota AI 429. Wait 35s...")
                time.sleep(35)
            else: return {}
    return {}

# --- DB UTILS ---
def get_source_id(name, ch_id):
    try:
        res = supabase.table("sources").select("id").eq("name", name).execute()
        data = cast(List[Dict[str, Any]], res.data)
        if data: return str(data[0]['id'])
        
        new = supabase.table("sources").insert({
            "name": name, "type": "youtube", "base_url": ch_id
        }).execute()
        new_data = cast(List[Dict[str, Any]], new.data)
        if new_data: return str(new_data[0]['id'])
    except: pass
    return None

def get_channel_videos(handle):
    videos = []
    try:
        res = youtube_service.channels().list(part="contentDetails,snippet", forHandle=handle).execute()
        if not res.get('items'): return []
        upl = res['items'][0]['contentDetails']['relatedPlaylists']['uploads']
        ch_title = res['items'][0]['snippet']['title']
        ch_id = res['items'][0]['id']
        pl = youtube_service.playlistItems().list(part="snippet", playlistId=upl, maxResults=5).execute()
        for i in pl.get('items', []):
            videos.append({
                "id": i['snippet']['resourceId']['videoId'],
                "title": i['snippet']['title'],
                "desc": i['snippet']['description'],
                "date": i['snippet']['publishedAt'],
                "url": f"https://www.youtube.com/watch?v={i['snippet']['resourceId']['videoId']}",
                "ch_title": ch_title, "ch_id": ch_id
            })
    except: pass
    return videos

# --- MAIN ---
if __name__ == "__main__":
    print("\n--- 🚀 START WORKER (APIFY) ---")
    
    for handle in YOUTUBE_CHANNELS:
        videos = get_channel_videos(handle)
        
        for v in videos:
            print(f"\n🔄 {v['title'][:40]}...")
            
            try:
                if supabase.table("intelligence_feed").select("id").eq("url", v['url']).execute().data:
                    print("   ⏭️  Già presente."); continue
            except: pass

            # 1. APIFY
            text = get_transcript_apify(v['url'])
            method = "Apify"
            
            if not text:
                print("   ⚠️ Fallback Descrizione.")
                text = f"{v['title']}\n{v['desc']}"
                method = "Descrizione"
            else:
                print("   🔥 SUBS RECUPERATI!")

            # 2. AI
            analysis = analyze_gemini(text)
            
            # 3. DB
            sid = get_source_id(v['ch_title'], v['ch_id'])
            if sid:
                try:
                    supabase.table("intelligence_feed").insert({
                        "source_id": sid, "title": v['title'], "url": v['url'],
                        "published_at": v['date'], "content": text, "analysis": analysis,
                        "raw_metadata": {"vid": v['id'], "method": method}
                    }).execute()
                    print(f"   💾 SALVATO")
                except Exception as e:
                    if "duplicate" not in str(e): print(f"   ❌ DB: {e}")
            
            print("   💤 2s...")
            time.sleep(2)
            
    print("\n--- ✅ FINITO ---")