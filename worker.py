import os
import json
import time
import requests
import traceback
from datetime import datetime

# Importiamo la libreria ufficiale
from youtube_transcript_api import YouTubeTranscriptApi
from googleapiclient.discovery import build
from google import genai
from google.genai import types
from supabase import create_client, Client

# --- CONFIG ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not SUPABASE_URL or not SUPABASE_KEY or not GOOGLE_API_KEY:
    raise ValueError("❌ Variabili mancanti.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
gemini_client = genai.Client(api_key=GOOGLE_API_KEY)
youtube_service = build('youtube', 'v3', developerKey=GOOGLE_API_KEY)

YOUTUBE_CHANNELS = ["@InvestireBiz"]

# --- FUNZIONE RECUPERO TESTO ---
def get_transcript(video_id: str) -> str:
    print(f"   🕵️  Scarico sottotitoli per {video_id} (via Proxy SOCKS5)...")
    
    # Configuriamo il dizionario proxy per la libreria
    # SOCKS5h significa che anche la risoluzione DNS avviene tramite proxy (più sicuro e anonimo)
    PROXIES = {
        "https": "socks5h://127.0.0.1:40000",
        "http": "socks5h://127.0.0.1:40000"
    }

    try:
        # Metodo Standard: passiamo 'proxies' direttamente alla funzione statica
        # Non serve istanziare classi o oggetti complessi.
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id, proxies=PROXIES)
        
        transcript = None
        try:
            # Cerca IT o EN
            transcript = transcript_list.find_transcript(['it', 'en'])
        except:
            # Fallback: Traduci il primo disponibile
            try:
                first = next(iter(transcript_list))
                transcript = first.translate('it')
            except:
                pass

        if transcript:
            data = transcript.fetch()
            
            # Parsing pulito
            full_text = " ".join([i['text'] for i in data if 'text' in i])
            
            if full_text:
                print("   ✅ Successo!")
                return full_text

    except Exception as e:
        print(f"   ⚠️ Errore Transcript: {e}")
        # traceback.print_exc()
        
    return ""

# --- ANALISI ---
def analyze_gemini(text: str) -> dict:
    if not text or len(text) < 50: return {"summary": "N/A"}
    
    prompt = """
    Analizza questo testo. JSON Output:
    { "summary": "Riassunto", "countries_involved": [], "risk_level": "LOW", "key_takeaway": "..." }
    """
    try:
        res = gemini_client.models.generate_content(
            model="gemini-2.0-flash",
            contents=f"{prompt}\nTEXT:{text[:30000]}",
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        return json.loads(res.text.replace("```json","").replace("```","").strip())
    except: return {}

# --- UTILS ---
def get_source_id(name, ch_id):
    try:
        res = supabase.table("sources").select("id").eq("name", name).execute()
        if res.data: return str(res.data[0]['id'])
        new = supabase.table("sources").insert({"name": name, "type": "yt", "base_url": ch_id}).execute()
        return str(new.data[0]['id']) if new.data else None
    except: return None

def url_exists(url):
    try:
        return len(supabase.table("intelligence_feed").select("id").eq("url", url).execute().data) > 0
    except: return False

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
    print("--- 🚀 START WORKER (MANUAL PROXY MODE) ---")
    for handle in YOUTUBE_CHANNELS:
        for v in get_channel_videos(handle):
            if url_exists(v['url']): continue
            
            print(f"🔄 {v['title'][:40]}...")
            
            # 1. TESTO
            text = get_transcript(v['id'])
            method = "Transcript API"
            
            # 2. FALLBACK
            if not text:
                print("   ⚠️ Sottotitoli assenti. Uso descrizione.")
                text = f"{v['title']}\n{v['desc']}"
                method = "Descrizione"
            
            # 3. SALVA
            analysis = analyze_gemini(text)
            sid = get_source_id(v['ch_title'], v['ch_id'])
            
            if sid:
                try:
                    supabase.table("intelligence_feed").insert({
                        "source_id": sid, "title": v['title'], "url": v['url'],
                        "published_at": v['date'], "content": text, "analysis": analysis,
                        "raw_metadata": {"vid": v['id'], "method": method}
                    }).execute()
                    print("   💾 Salvato.")
                except: print("   ⏭️ Duplicato.")
            
            time.sleep(1)
    print("--- END ---")