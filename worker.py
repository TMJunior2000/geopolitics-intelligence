import os
import json
import time
import requests
import traceback
from datetime import datetime

# Import
from youtube_transcript_api import YouTubeTranscriptApi
try:
    from youtube_transcript_api.proxies import GenericProxyConfig
except ImportError:
    from youtube_transcript_api import GenericProxyConfig

from googleapiclient.discovery import build
from google import genai
from google.genai import types
from supabase import create_client, Client

# --- CONFIG ---
print("🔧 INIT: Verifico variabili...")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not SUPABASE_URL or not SUPABASE_KEY or not GOOGLE_API_KEY:
    raise ValueError("❌ Variabili mancanti.")

# Inizializzazione Client
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    gemini_client = genai.Client(api_key=GOOGLE_API_KEY)
    youtube_service = build('youtube', 'v3', developerKey=GOOGLE_API_KEY)
    print("✅ Client inizializzati.")
except Exception as e:
    print(f"❌ Errore Inizializzazione Client: {e}")
    exit(1)

YOUTUBE_CHANNELS = ["@InvestireBiz"]

# --- FUNZIONI ---

def get_transcript(video_id: str) -> str:
    print(f"   🕵️  Scarico sottotitoli per {video_id}...")
    try:
        proxy_url = "socks5h://127.0.0.1:40000"
        proxy_conf = GenericProxyConfig(http_url=proxy_url, https_url=proxy_url)
        ytt_api = YouTubeTranscriptApi(proxy_config=proxy_conf)
        
        transcript_list = ytt_api.list(video_id)
        transcript = None
        try:
            transcript = transcript_list.find_transcript(['it', 'en'])
        except:
            try:
                first = next(iter(transcript_list))
                transcript = first.translate('it')
            except: pass

        if transcript:
            data = transcript.fetch()
            parts = []
            for i in data:
                if isinstance(i, dict): parts.append(i.get('text', ''))
                elif hasattr(i, 'text'): parts.append(i.text)
            
            full_text = " ".join(parts)
            if full_text:
                print("   ✅ Successo Transcript!")
                return full_text
    except Exception as e:
        print(f"   ⚠️ Errore Transcript: {e}")
    return ""

def analyze_gemini(text: str) -> dict:
    if not text: return {"summary": "N/A"}
    print("   🧠 Analisi Gemini in corso...")
    try:
        res = gemini_client.models.generate_content(
            model="gemini-2.0-flash",
            contents=f'Analizza JSON: {{ "summary": "...", "risk": "LOW" }}\nTEXT:{text[:15000]}',
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        return json.loads(res.text.replace("```json","").replace("```","").strip())
    except Exception as e: 
        print(f"   ❌ Errore Gemini: {e}")
        return {}

def get_source_id(name, ch_id):
    print(f"   🔎 Cerco/Creo Source: {name}")
    try:
        # Verifica esistenza
        res = supabase.table("sources").select("id").eq("name", name).execute()
        if res.data: 
            print(f"   ✅ Source trovata: {res.data[0]['id']}")
            return str(res.data[0]['id'])
        
        # Creazione
        print(f"   ➕ Creo nuova source...")
        new = supabase.table("sources").insert({
            "name": name, 
            "type": "yt", 
            "base_url": ch_id
        }).execute()
        
        if new.data:
            print(f"   ✅ Source creata: {new.data[0]['id']}")
            return str(new.data[0]['id'])
        else:
            print(f"   ❌ Errore Creazione Source: Nessun dato ritornato. (Check RLS?)")
            return None
            
    except Exception as e:
        print(f"   ❌ ERRORE CRITICO get_source_id: {e}")
        # Stampa dettagliata per capire se è colpa delle Permission
        print(traceback.format_exc())
        return None

def get_channel_videos(handle):
    # (Logica identica a prima, abbreviata per spazio)
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
    print("--- 🚀 START WORKER DEBUG ---")
    for handle in YOUTUBE_CHANNELS:
        for v in get_channel_videos(handle):
            # Rimuovo controllo esistenza per forzare il test di inserimento
            # if url_exists(v['url']): continue
            
            print(f"🔄 Processing: {v['title'][:30]}...")
            
            text = get_transcript(v['id'])
            if not text: text = "Descrizione fallback..."
            
            analysis = analyze_gemini(text)
            
            # QUI È IL PUNTO CRITICO
            sid = get_source_id(v['ch_title'], v['ch_id'])
            
            if sid:
                try:
                    print("   💾 Tentativo inserimento intelligence_feed...")
                    data = {
                        "source_id": sid, 
                        "title": v['title'], 
                        "url": v['url'],
                        "published_at": v['date'], 
                        "content": text[:5000], # Taglio per sicurezza
                        "analysis": analysis,
                        "raw_metadata": {"vid": v['id']}
                    }
                    res = supabase.table("intelligence_feed").insert(data).execute()
                    print(f"   ✅ Salvataggio riuscito! Dati: {len(res.data)}")
                except Exception as e:
                    print(f"   ❌ ERRORE INSERIMENTO FINALE: {e}")
                    print(traceback.format_exc())
            else:
                print("   ❌ SALVATAGGIO SALTATO: Source ID nullo.")
            
            time.sleep(1)
    print("--- END ---")