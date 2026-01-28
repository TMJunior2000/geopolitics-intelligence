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
print("\n🔧 [INIT] Avvio script (APIFY TRANSCRIPT MODE)...")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
APIFY_TOKEN = os.getenv("APIFY_TOKEN")

try:
    supabase: Client = create_client(cast(str, SUPABASE_URL), cast(str, SUPABASE_KEY))
    gemini_client = genai.Client(api_key=GOOGLE_API_KEY)
    youtube_service = build('youtube', 'v3', developerKey=GOOGLE_API_KEY)
    apify_client = ApifyClient(APIFY_TOKEN)
    print("✅ Client inizializzati.")
except Exception as e:
    print(f"❌ ERRORE INIT: {e}")
    exit(1)

YOUTUBE_CHANNELS = ["@InvestireBiz"]

# --- ESTRAZIONE TRASCRIZIONE ---
def get_transcript_apify(video_url: str) -> str:
    """Estrae il testo usando pintostudio/youtube-transcript-scraper"""
    print(f"   ☁️ [APIFY] Estrazione testo: {video_url}...")
    
    # L'actor che hai confermato funzionare
    actor_id = "pintostudio/youtube-transcript-scraper"
    
    run_input = {
        "videoUrl": video_url,
    }

    try:
        # Avvia l'actor
        run = apify_client.actor(actor_id).call(run_input=run_input)
        if not run: 
            return ""
        
        full_text = ""
        # Recupera i risultati dal dataset
        items = list(apify_client.dataset(run["defaultDatasetId"]).iterate_items())
        
        for item in items:
            if isinstance(item, dict):
                # Cerchiamo il testo in tutte le chiavi possibili usate dagli scraper
                # 1. 'text' è la più comune per i singoli segmenti
                # 2. 'caption' o 'transcript' per il testo completo
                # 3. 'body' o 'content' come fallback
                text_part = (
                    item.get("text") or 
                    item.get("caption") or 
                    item.get("transcript") or 
                    item.get("fullTranscript")
                )
                
                if text_part:
                    full_text += str(text_part) + " "
        
        clean_text = full_text.strip()
        
        if clean_text:
            # Rimuoviamo eventuali timestamp se presenti (es. [00:00]) 
            # ma solitamente questi actor danno già testo pulito
            print(f"      ✅ Testo estratto con successo ({len(clean_text)} caratteri)")
            return clean_text
        else:
            # Se arriviamo qui, l'actor ha girato ma non abbiamo trovato le chiavi giuste
            print(f"      ⚠️ Dataset trovato ma chiavi sconosciute. Chiavi presenti: {items[0].keys() if items else 'Nessuna'}")
            return ""

    except Exception as e:
        print(f"      ❌ Errore durante la chiamata Apify: {e}")
        return ""

# --- ANALISI GEMINI ---
def analyze_gemini(text: str) -> dict:
    if not text or len(text) < 50: return {"summary": "N/A"}
    print(f"   🧠 [AI] Analisi con Gemini...")
    try:
        res = gemini_client.models.generate_content(
            model="gemini-2.0-flash",
            contents=f'Analizza il testo e restituisci JSON: {{ "summary": "...", "risk_level": "LOW", "countries_involved": [], "key_takeaway": "..." }}\nTESTO:{text[:28000]}',
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        return cast(dict, json.loads(res.text.strip() if res.text else "{}"))
    except:
        return {}

# --- GESTIONE DB ---
def get_source_id(name: str, ch_id: str) -> Optional[str]:
    try:
        res = supabase.table("sources").select("id").eq("name", name).execute()
        data = cast(List[Dict[str, Any]], res.data)
        if data: return str(data[0].get('id'))
        
        new = supabase.table("sources").insert({"name": name, "type": "youtube", "base_url": ch_id}).execute()
        new_data = cast(List[Dict[str, Any]], new.data)
        if new_data: return str(new_data[0].get('id'))
    except: return None
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
        
        pl = youtube_service.playlistItems().list(part="snippet", playlistId=upl_id, maxResults=3).execute()
        for i in pl.get('items', []):
            snippet = i.get('snippet', {})
            v_id = snippet.get('resourceId', {}).get('videoId')
            videos.append({
                "id": v_id,
                "title": snippet.get('title'),
                "desc": snippet.get('description'),
                "date": snippet.get('publishedAt'),
                "url": f"https://www.youtube.com/watch?v={v_id}",
                "ch_title": ch_title, "ch_id": ch_id
            })
    except: pass
    return videos

# --- MAIN ---
if __name__ == "__main__":
    print("\n--- 🚀 START WORKER ---")
    
    for handle in YOUTUBE_CHANNELS:
        videos = get_channel_videos(handle)
        
        for v in videos:
            print(f"\n🔄 Video: {v['title'][:50]}...")
            
            # Controllo duplicati
            try:
                check = supabase.table("intelligence_feed").select("id").eq("url", v['url']).execute()
                if check.data:
                    print("   ⏭️  Già presente."); continue
            except: pass

            # 1. Scraping Trascrizione con Apify
            text = get_transcript_apify(v['url'])
            method = "Apify-Transcript"
            
            if not text:
                print("   ⚠️ Sottotitoli non trovati. Uso la descrizione.")
                text = f"{v['title']}\n{v['desc']}"
                method = "YouTube-Description"

            # 2. Analisi AI
            analysis = analyze_gemini(text)
            
            # 3. Salvataggio
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
                    print(f"   ❌ Errore DB: {e}")
            
            time.sleep(2)

    print("\n--- ✅ FINITO ---")