import os
import json
import time
import requests
import traceback  # Fondamentale per vedere i dettagli dell'errore
from datetime import datetime

# Import librerie
try:
    from youtube_transcript_api import YouTubeTranscriptApi
except ImportError:
    print("❌ CRITICO: Libreria youtube_transcript_api non installata.")
    exit(1)

from googleapiclient.discovery import build
from google import genai
from google.genai import types
from supabase import create_client, Client

# --- SETUP VARIABILI ---
print("🔧 [INIT] Caricamento variabili d'ambiente...")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not SUPABASE_URL or not SUPABASE_KEY or not GOOGLE_API_KEY:
    print("❌ ERRORE: Variabili d'ambiente mancanti.")
    exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
gemini_client = genai.Client(api_key=GOOGLE_API_KEY)
youtube_service = build('youtube', 'v3', developerKey=GOOGLE_API_KEY)

YOUTUBE_CHANNELS = ["@InvestireBiz"]

# ==========================================
# 🔍 DIAGNOSTICA LIBRERIA (Il punto critico)
# ==========================================
print("\n--- 🔍 DIAGNOSTICA LIBRERIA ---")
print(f"Libreria importata: {YouTubeTranscriptApi}")
print(f"Metodi disponibili: {dir(YouTubeTranscriptApi)}")
if hasattr(YouTubeTranscriptApi, 'list_transcripts'):
    print("✅ Metodo STATICO 'list_transcripts' TROVATO (Versione Standard).")
elif hasattr(YouTubeTranscriptApi, 'list'):
    print("⚠️ Metodo 'list' trovato. Sembra una versione vecchia o custom.")
else:
    print("❌ Nessun metodo noto trovato. La libreria è corrotta o diversa.")
print("-------------------------------\n")

# ==========================================
# FUNZIONI
# ==========================================

def get_transcript(video_id: str) -> str:
    print(f"   🕵️  [DEBUG] Avvio get_transcript per ID: {video_id}")
    
    try:
        # TENTATIVO 1: Metodo Standard Statico (Libreria Ufficiale)
        if hasattr(YouTubeTranscriptApi, 'list_transcripts'):
            print("   👉 [DEBUG] Chiamo YouTubeTranscriptApi.list_transcripts(video_id)...")
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        
        # TENTATIVO 2: Istanza (Se hai una classe custom)
        else:
            print("   👉 [DEBUG] Provo a istanziare la classe (Fallback)...")
            ytt = YouTubeTranscriptApi() 
            if hasattr(ytt, 'list_transcripts'):
                transcript_list = ytt.list_transcripts(video_id)
            elif hasattr(ytt, 'list'):
                transcript_list = ytt.list(video_id)
            else:
                print("   ❌ [DEBUG] Impossibile trovare un metodo valido.")
                return ""

        print("   ✅ [DEBUG] Lista trascritti ottenuta. Cerco lingua...")
        
        # Logica selezione lingua
        transcript = None
        try:
            print("   👉 [DEBUG] Cerco 'it' o 'en' manuale...")
            transcript = transcript_list.find_transcript(['it', 'en'])
        except Exception as e:
            print(f"   ⚠️ [DEBUG] Manuale non trovato ({e}). Provo traduzione automatica...")
            try:
                # Prendi il primo disponibile (es. generato auto)
                first_transcript = next(iter(transcript_list))
                print(f"   👉 [DEBUG] Trovato trascritto in lingua: {first_transcript.language_code}")
                if first_transcript.language_code == 'it':
                    transcript = first_transcript
                else:
                    print("   👉 [DEBUG] Traduco in Italiano...")
                    transcript = first_transcript.translate('it')
            except Exception as e2:
                print(f"   ❌ [DEBUG] Fallita anche la traduzione: {e2}")
                return ""

        if transcript:
            print("   👉 [DEBUG] Fetching dati testuali...")
            data = transcript.fetch()
            
            # Parsing robusto
            text_parts = []
            for item in data:
                # Gestisce sia dict {'text': '...'} che oggetti
                if isinstance(item, dict):
                    text_parts.append(item.get('text', ''))
                elif hasattr(item, 'text'):
                    text_parts.append(item.text)
                else:
                    text_parts.append(str(item))
            
            full_text = " ".join(text_parts)
            print(f"   ✅ [DEBUG] Testo estratto: {len(full_text)} caratteri.")
            return full_text

    except Exception as e:
        print(f"   ❌ [DEBUG] ERRORE CRITICO in get_transcript:")
        print(traceback.format_exc()) # Stampa l'errore completo con numeri di riga
        return ""
    
    return ""

def analyze_gemini(text: str) -> dict:
    if not text: return {"summary": "N/A"}
    print(f"   🧠 [DEBUG] Invio {len(text)} caratteri a Gemini...")
    try:
        res = gemini_client.models.generate_content(
            model="gemini-2.0-flash",
            contents=f"Analizza: {text[:30000]}",
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        print("   ✅ [DEBUG] Gemini ha risposto.")
        return json.loads(res.text.replace("```json","").replace("```","").strip())
    except Exception as e:
        print(f"   ❌ [DEBUG] Errore Gemini: {e}")
        return {}

def get_channel_videos(handle):
    print(f"📡 [DEBUG] Scansiono canale: {handle}")
    try:
        res = youtube_service.channels().list(part="contentDetails,snippet", forHandle=handle).execute()
        if not res.get('items'): 
            print("   ⚠️ [DEBUG] Nessun canale trovato con questo handle.")
            return []
        
        upl = res['items'][0]['contentDetails']['relatedPlaylists']['uploads']
        ch_title = res['items'][0]['snippet']['title']
        ch_id = res['items'][0]['id']
        
        print(f"   👉 [DEBUG] ID Uploads: {upl}. Recupero ultimi 5 video...")
        pl = youtube_service.playlistItems().list(part="snippet", playlistId=upl, maxResults=5).execute()
        
        videos = []
        for i in pl.get('items', []):
            vid = i['snippet']['resourceId']['videoId']
            print(f"   👉 [DEBUG] Trovato video: {vid} - {i['snippet']['title'][:30]}...")
            videos.append({
                "id": vid,
                "title": i['snippet']['title'],
                "desc": i['snippet']['description'],
                "date": i['snippet']['publishedAt'],
                "url": f"https://www.youtube.com/watch?v={vid}",
                "ch_title": ch_title, "ch_id": ch_id
            })
        return videos
    except Exception as e:
        print(f"   ❌ [DEBUG] Errore API YouTube Data: {e}")
        return []

def get_source_id(name, ch_id):
    try:
        res = supabase.table("sources").select("id").eq("name", name).execute()
        if res.data: return str(res.data[0]['id'])
        new = supabase.table("sources").insert({"name": name, "type": "yt", "base_url": ch_id}).execute()
        return str(new.data[0]['id']) if new.data else None
    except Exception as e:
        print(f"   ❌ [DEBUG] Errore Source ID: {e}")
        return None

def url_exists(url):
    try:
        res = supabase.table("intelligence_feed").select("id").eq("url", url).execute()
        exists = len(res.data) > 0
        if exists: print(f"   ⏭️ [DEBUG] URL già nel DB: {url}")
        return exists
    except: return False

# ==========================================
# MAIN LOOP
# ==========================================
if __name__ == "__main__":
    print(f"\n--- 🚀 START WORKER DEBUG MODE ({datetime.now()}) ---")
    
    for handle in YOUTUBE_CHANNELS:
        videos = get_channel_videos(handle)
        
        if not videos:
            print("⚠️ Nessun video trovato o errore API.")
        
        for v in videos:
            if url_exists(v['url']): continue
            
            print(f"\n🔄 Processing: {v['title'][:40]}...")
            
            # 1. TESTO
            text = get_transcript(v['id'])
            method = "Transcript API"
            
            if not text:
                print("   ⚠️ Sottotitoli assenti. Uso descrizione.")
                text = f"{v['title']}\n{v['desc']}"
                method = "Descrizione"
            
            # 2. ANALISI
            analysis = analyze_gemini(text)
            
            # 3. SALVATAGGIO
            sid = get_source_id(v['ch_title'], v['ch_id'])
            if sid:
                try:
                    print("   💾 [DEBUG] Salvataggio su Supabase...")
                    supabase.table("intelligence_feed").insert({
                        "source_id": sid, "title": v['title'], "url": v['url'],
                        "published_at": v['date'], "content": text, "analysis": analysis,
                        "raw_metadata": {"vid": v['id'], "method": method}
                    }).execute()
                    print("   ✅ Salvato.")
                except Exception as e:
                    print(f"   ❌ Errore Insert DB: {e}")
            
            time.sleep(1)
            
    print("\n--- ✅ WORKER FINISHED ---")