import os
import json
import time
import uuid
import shutil
import datetime as dt
from datetime import datetime, timezone
from typing import List, Optional, Dict

# --- LIBRERIE ESTERNE ---
import yt_dlp
import assemblyai as aai
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google import genai
from google.genai import types
from supabase import create_client, Client

# =========================
# 1. CONFIGURAZIONE & SETUP
# =========================

# Caricamento Variabili Ambiente
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
ASSEMBLYAI_KEY = os.getenv("ASSEMBLYAI_KEY")

# Verifica critica iniziale
if not all([SUPABASE_URL, SUPABASE_KEY, GOOGLE_API_KEY, ASSEMBLYAI_KEY]):
    raise ValueError("❌ ERRORE: Mancano una o più variabili d'ambiente nel file .env (SUPABASE_URL, SUPABASE_KEY, GOOGLE_API_KEY, ASSEMBLYAI_KEY)")

# Configurazione Modalità
MODE = os.getenv("MODE", "LIVE").upper()
# Date per Backfill (modificare se necessario)
BACKFILL_START = dt.date(2026, 1, 1)
BACKFILL_END = dt.date(2026, 1, 31)

# Lista Canali
YOUTUBE_CHANNELS = [
    "@InvestireBiz",
    # Aggiungi qui altri canali es: "@NovaLectio"
]

# Inizializzazione Clienti
try:
    aai.settings.api_key = ASSEMBLYAI_KEY
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    gemini_client = genai.Client(api_key=GOOGLE_API_KEY)
    youtube_service = build('youtube', 'v3', developerKey=GOOGLE_API_KEY)
except Exception as e:
    raise RuntimeError(f"❌ Errore critico inizializzazione client: {e}")

# =========================
# 2. HELPER FUNCTIONS
# =========================

def log(msg: str):
    """Stampa messaggi con timestamp."""
    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] {msg}", flush=True)

def check_ffmpeg():
    """Verifica che FFmpeg sia installato nel sistema."""
    if not shutil.which("ffmpeg"):
        raise RuntimeError("❌ FFmpeg non trovato! Installalo e aggiungilo al PATH di sistema.")

def url_exists(url: str) -> bool:
    """Controlla se l'URL esiste già nel DB."""
    try:
        res = supabase.table("intelligence_feed").select("id").eq("url", url).execute()
        return len(res.data) > 0
    except Exception as e:
        log(f"⚠️ Errore check duplicati: {e}")
        return False

def get_or_create_source(name: str, url: str) -> str:
    """Ottiene o crea l'ID della fonte (canale) nel DB."""
    try:
        res = supabase.table("sources").select("id").eq("name", name).execute()
        if res.data:
            return res.data[0]['id']
        
        new = supabase.table("sources").insert({
            "name": name, 
            "type": "youtube", 
            "base_url": url
        }).execute()
        return new.data[0]['id'] if new.data else None
    except Exception as e:
        log(f"⚠️ Errore gestione source: {e}")
        return None

# =========================
# 3. CORE LOGIC (Download -> Transcribe -> Analyze)
# =========================

def download_audio_mp3(video_url: str) -> Optional[str]:
    """Scarica audio da YT e converte in MP3."""
    temp_dir = "temp_audio"
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)
    
    unique_name = f"audio_{uuid.uuid4()}"
    output_path_no_ext = os.path.join(temp_dir, unique_name)
    
    # Configurazione YT-DLP
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': output_path_no_ext, # yt-dlp aggiungerà .mp3
        'quiet': True,
        'noplaylist': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
        
        final_path = output_path_no_ext + ".mp3"
        if os.path.exists(final_path):
            return final_path
        return None
    except Exception as e:
        log(f"❌ Errore Download yt-dlp: {e}")
        return None

def transcribe_with_assemblyai(file_path: str) -> str:
    """Invia il file audio ad AssemblyAI."""
    transcriber = aai.Transcriber()
    config = aai.TranscriptionConfig(language_code="it") # Forza Italiano
    
    try:
        transcript = transcriber.transcribe(file_path, config=config)
        
        if transcript.status == aai.TranscriptStatus.error:
            log(f"❌ Errore AssemblyAI API: {transcript.error}")
            return ""
        
        return transcript.text
    except Exception as e:
        log(f"❌ Eccezione Trascrizione: {e}")
        return ""

def analyze_with_gemini(text: str) -> dict:
    """Analizza il testo con Gemini."""
    if not text or len(text) < 50:
        return {"summary": "N/A - Testo insufficiente", "risk_level": "LOW", "countries_involved": []}

    prompt = """
    Sei un analista di intelligence geopolitica e finanziaria.
    Analizza la seguente trascrizione video.
    
    Restituisci ESCLUSIVAMENTE un JSON valido con questa struttura:
    {
        "summary": "Riassunto analitico in italiano (max 5 frasi).",
        "countries_involved": ["Paese1", "Paese2"],
        "risk_level": "LOW" | "MEDIUM" | "HIGH",
        "keywords": ["tag1", "tag2", "tag3", "tag4"],
        "key_takeaway": "La singola conclusione più importante"
    }
    """
    
    try:
        # Tagliamo a 30k caratteri per sicurezza token
        response = gemini_client.models.generate_content(
            model="gemini-2.0-flash",
            contents=f"{prompt}\n\nTRASCRIZIONE:\n{text[:30000]}",
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        
        clean_json = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_json)
    except Exception as e:
        log(f"❌ Errore Gemini: {e}")
        return {"summary": f"Errore analisi AI: {str(e)}"}

# =========================
# 4. YOUTUBE API LOGIC
# =========================

def get_channel_videos(handle: str) -> List[Dict]:
    """Recupera gli ultimi video dal canale usando API ufficiale."""
    videos = []
    try:
        # 1. Ottieni ID Canale e Playlist Uploads
        res_ch = youtube_service.channels().list(
            part="id,contentDetails,snippet", 
            forHandle=handle
        ).execute()

        if not res_ch.get('items'):
            log(f"⚠️ Canale non trovato: {handle}")
            return []

        channel_item = res_ch['items'][0]
        channel_id = channel_item['id']
        channel_title = channel_item['snippet']['title']
        uploads_id = channel_item['contentDetails']['relatedPlaylists']['uploads']

        # 2. Ottieni Video dalla Playlist
        res_pl = youtube_service.playlistItems().list(
            part="snippet",
            playlistId=uploads_id,
            maxResults=10  # Prendi ultimi 10 video
        ).execute()

        for item in res_pl.get('items', []):
            snip = item['snippet']
            # Parsing data sicuro
            pub_date = datetime.fromisoformat(snip['publishedAt'].replace('Z', '+00:00'))
            
            videos.append({
                "id": snip['resourceId']['videoId'],
                "title": snip['title'],
                "description": snip['description'],
                "published_at": pub_date,
                "url": f"https://www.youtube.com/watch?v={snip['resourceId']['videoId']}",
                "channel_title": channel_title,
                "channel_id": channel_id
            })
            
    except HttpError as e:
        log(f"❌ Errore API YouTube: {e}")
    
    return videos

# =========================
# 5. MAIN LOOP
# =========================

def process_single_video(video: Dict):
    log(f"🔄 Avvio processo: {video['title'][:50]}...")

    # 1. Download
    log("   ⬇️  Scaricamento Audio (yt-dlp)...")
    mp3_path = download_audio_mp3(video['url'])
    
    if not mp3_path:
        log("   ❌ Skip: Impossibile scaricare audio.")
        return

    full_text = ""
    try:
        # 2. Trascrizione
        log("   🎙️  Trascrizione (AssemblyAI)...")
        full_text = transcribe_with_assemblyai(mp3_path)
        
        if not full_text:
            log("   ⚠️ Trascrizione fallita/vuota. Fallback su Descrizione.")
            full_text = f"TITOLO: {video['title']}\nDESCRIZIONE: {video['description']}"
        else:
            log("   ✅ Trascrizione riuscita.")

    finally:
        # 3. Cleanup (Sempre!)
        if os.path.exists(mp3_path):
            os.remove(mp3_path)
    
    # 4. Analisi
    log("   🧠 Analisi Intelligence (Gemini)...")
    analysis = analyze_with_gemini(full_text)

    # 5. Salvataggio
    try:
        source_id = get_or_create_source(video['channel_title'], f"https://youtube.com/channel/{video['channel_id']}")
        
        payload = {
            "source_id": source_id,
            "title": video['title'],
            "url": video['url'],
            "published_at": video['published_at'].isoformat(),
            "content": full_text,
            "analysis": analysis,
            "raw_metadata": {"video_id": video['id']}
        }
        
        supabase.table("intelligence_feed").insert(payload).execute()
        log("   💾 Salvato con successo nel DB.")
        
        # Pausa di sicurezza per API rate limits
        time.sleep(5)

    except Exception as e:
        log(f"❌ Errore salvataggio DB: {e}")

if __name__ == "__main__":
    print(f"\n--- 🚀 WORKER STARTED | MODE: {MODE} ---\n")
    
    # Check preliminare FFmpeg
    check_ffmpeg()

    for handle in YOUTUBE_CHANNELS:
        log(f"📡 Scansione: {handle}")
        videos = get_channel_videos(handle)
        
        for video in videos:
            # --- FILTRO DATE ---
            v_date = video['published_at'].date()
            if MODE == "BACKFILL":
                if not (BACKFILL_START <= v_date <= BACKFILL_END):
                    continue
            else: # LIVE
                today = datetime.now(timezone.utc).date()
                if (today - v_date).days > 2: # Solo ultimi 2 giorni
                    continue

            # --- FILTRO DUPLICATI ---
            # Decommentare per saltare video già processati
            if url_exists(video['url']):
               log(f"   ⏭️  Già nel DB: {video['title'][:30]}...")
               continue
            
            # --- ESECUZIONE ---
            process_single_video(video)

    log("--- ✅ WORKER COMPLETED ---")