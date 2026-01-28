import os
import json
import re
import html
import time
import datetime as dt
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

# --- LIBRERIE GOOGLE UFFICIALI ---
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google import genai
from google.genai import types

# --- LIBRERIA SOTTOTITOLI "UNOFFICIAL" ---
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound

# --- DATABASE ---
from supabase import create_client, Client

# =========================
# CONFIGURAZIONE
# =========================
MODE = os.getenv("MODE", "LIVE").upper()
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")

# Lista canali (Handle o ID)
YOUTUBE_CHANNELS = [
    "@InvestireBiz",
    # Aggiungi qui altri canali es: "@BreakingItaly", "@NovaLectio"
]

# Date per la modalità BACKFILL
BACKFILL_START = dt.date(2026, 1, 1)
BACKFILL_END = dt.date(2026, 1, 30)

# =========================
# INIZIALIZZAZIONE CLIENT
# =========================
if not GOOGLE_API_KEY or not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("❌ Variabili d'ambiente mancanti! Controlla .env")

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    gemini_client = genai.Client(api_key=GOOGLE_API_KEY)
    youtube_service = build('youtube', 'v3', developerKey=GOOGLE_API_KEY)
except Exception as e:
    raise RuntimeError(f"Errore inizializzazione servizi: {e}")

# =========================
# UTILITY
# =========================
def log(msg):
    print(f"[{datetime.now(timezone.utc).isoformat()}] {msg}", flush=True)

def url_exists(url: str) -> bool:
    """Controlla se il video è già nel DB per evitare duplicati."""
    res = supabase.table("intelligence_feed").select("id").eq("url", url).execute()
    return len(res.data) > 0

def get_or_create_source(name, type_, base_url):
    """Gestisce la tabella 'sources' per collegare i video al canale giusto."""
    res = supabase.table("sources").select("*").eq("name", name).execute()
    data = getattr(res, 'data', [])
    if data:
        return data[0]["id"]
    
    new_res = supabase.table("sources").insert({
        "name": name,
        "type": type_,
        "base_url": base_url 
    }).execute()
    new_data = getattr(new_res, 'data', [])
    return new_data[0]["id"] if new_data else None

# =========================
# LOGICA YOUTUBE (IBRIDA)
# =========================

def get_channel_id_from_handle(handle: str) -> Optional[str]:
    """Ottiene l'ID numerico del canale partendo dall'handle (@Nome)."""
    try:
        request = youtube_service.channels().list(part="id", forHandle=handle)
        response = request.execute()
        return response['items'][0]['id'] if response['items'] else None
    except HttpError as e:
        log(f"⚠️ Errore API Channel ID per {handle}: {e}")
        return None

def get_uploads_playlist_id(channel_id: str) -> Optional[str]:
    """Trova la playlist 'Uploads' che contiene tutti i video del canale (costa poca quota)."""
    try:
        request = youtube_service.channels().list(part="contentDetails", id=channel_id)
        response = request.execute()
        if response['items']:
            return response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
        return None
    except HttpError as e:
        log(f"⚠️ Errore recupero playlist uploads: {e}")
        return None

def get_latest_videos(playlist_id: str, limit=10) -> List[Dict]:
    """Scarica gli ultimi video dalla playlist Uploads."""
    videos = []
    try:
        request = youtube_service.playlistItems().list(
            part="snippet",
            playlistId=playlist_id,
            maxResults=limit
        )
        response = request.execute()
        
        for item in response.get('items', []):
            snippet = item['snippet']
            published_at_str = snippet['publishedAt']
            # Conversione data sicura
            published_dt = datetime.fromisoformat(published_at_str.replace('Z', '+00:00'))
            
            videos.append({
                "id": snippet['resourceId']['videoId'],
                "title": snippet['title'],
                "description": snippet['description'],
                "published_at": published_dt,
                "channel_title": snippet['channelTitle'],
                "url": f"https://www.youtube.com/watch?v={snippet['resourceId']['videoId']}"
            })
    except HttpError as e:
        log(f"⚠️ Errore recupero video lista: {e}")
    
    return videos

def get_hybrid_transcript(video_id: str) -> str:
    """
    Scarica i sottotitoli usando youtube_transcript_api.
    Gestisce correttamente gli oggetti e le traduzioni.
    """
    try:
        # 1. Istanziamo l'oggetto API (Fondamentale per il thread safety)
        ytt_api = YouTubeTranscriptApi() 

        # 2. Otteniamo la lista dei transcript disponibili
        transcript_list_obj = ytt_api.list(video_id)

        # 3. Cerchiamo Italiano o Inglese
        try:
            transcript = transcript_list_obj.find_transcript(['it', 'en'])
        except Exception:
            # Fallback: Prendi il primo disponibile (es. Spagnolo) e traducilo in IT
            first_transcript = next(iter(transcript_list_obj))
            transcript = first_transcript.translate('it') 

        # 4. Scarichiamo i dati
        # fetch() restituisce una lista di oggetti, NON dizionari
        transcript_data = transcript.fetch()
        
        # 5. Uniamo il testo accedendo alla proprietà .text dell'oggetto
        full_text = " ".join([item.text for item in transcript_data])
        return full_text

    except (TranscriptsDisabled, NoTranscriptFound):
        # Nessun sottotitolo disponibile
        return ""
    except Exception as e:
        log(f"⚠️ Warning Transcript ({video_id}): {e}")
        return ""

# =========================
# LOGICA INTELLIGENZA ARTIFICIALE
# =========================

def analyze_with_gemini(text: str) -> dict:
    """Analizza il testo con Gemini 2.0 Flash e restituisce un JSON."""
    if not text or len(text) < 50:
        return {"summary": "N/A", "risk_level": "LOW", "countries_involved": [], "keywords": []}

    prompt = """
    Sei un analista geopolitico e finanziario. Analizza il testo fornito.
    Restituisci ESCLUSIVAMENTE un JSON valido con questa struttura esatta:
    {
        "summary": "riassunto in italiano max 3 frasi",
        "countries_involved": ["paese1", "paese2"],
        "risk_level": "LOW" | "MEDIUM" | "HIGH",
        "keywords": ["tag1", "tag2", "tag3"]
    }
    """
    try:
        # Limitiamo il testo per evitare token overflow
        response = gemini_client.models.generate_content(
            model="gemini-2.0-flash",
            contents=f"{prompt}\n\nTesto da analizzare:\n{text[:25000]}",
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        
        # Pulizia JSON (a volte Gemini aggiunge backticks)
        raw_json = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(raw_json)
    
    except Exception as e:
        log(f"❌ Errore Analisi AI: {e}")
        return {"summary": "Errore AI", "error": str(e)}

# =========================
# PROCESSO PRINCIPALE
# =========================

def process_channel(handle_or_id: str):
    # 1. Trova ID Canale
    channel_id = handle_or_id
    if handle_or_id.startswith("@"):
        channel_id = get_channel_id_from_handle(handle_or_id)
        if not channel_id: return

    # 2. Trova Playlist Uploads (Metodo economico)
    uploads_id = get_uploads_playlist_id(channel_id)
    if not uploads_id: return

    log(f"📡 Scansione canale: {channel_id}...")
    videos = get_latest_videos(uploads_id, limit=10) # Ultimi 10 video

    if not videos: return

    # Gestione Source ID nel DB
    channel_name = videos[0]['channel_title']
    source_id = get_or_create_source(channel_name, "youtube", f"https://youtube.com/channel/{channel_id}")

    for video in videos:
        # --- FILTRO DATE ---
        video_date = video['published_at'].date()
        now = datetime.now(timezone.utc).date()

        if MODE == "LIVE":
            # Accetta solo video di oggi o ieri
            if (now - video_date).days > 1:
                continue
        else: # BACKFILL
            if not (BACKFILL_START <= video_date <= BACKFILL_END):
                continue

        # --- FILTRO DUPLICATI ---
        if url_exists(video['url']):
            log(f"⏭️ Saltato (già presente): {video['title']}")
            continue
        
        log(f"🔄 Elaborazione: {video['title']}")

        # 3. Scarica Testo (Sottotitoli O Fallback)
        full_text = get_hybrid_transcript(video['id'])
        
        if full_text:
            log("✅ Sottotitoli trovati")
        else:
            # FALLBACK CRUCIALE
            full_text = f"TITOLO: {video['title']}\nDESCRIZIONE: {video['description']}"
            log("⚠️ Sottotitoli assenti -> Usato Fallback Titolo+Descrizione")

        # 4. Analisi AI
        analysis = analyze_with_gemini(full_text)

        # 5. Salvataggio DB
        try:
            supabase.table("intelligence_feed").insert({
                "source_id": source_id,
                "title": video['title'],
                "url": video['url'],
                "published_at": video['published_at'].isoformat(),
                "content": full_text,
                "analysis": analysis,
                "raw_metadata": {"id": video['id'], "channel_id": channel_id}
            }).execute()
            log(f"💾 Salvato nel DB")

            # --- RATE LIMITING ---
            # Pausa di 10 secondi per evitare l'errore 429 di Gemini
            log("⏳ Attesa 10s per quota AI...")
            time.sleep(10)

        except Exception as e:
            log(f"❌ Errore salvataggio DB: {e}")

# =========================
# ENTRY POINT
# =========================
if __name__ == "__main__":
    log(f"--- WORKER START (MODE={MODE}) ---")
    
    for handle in YOUTUBE_CHANNELS:
        process_channel(handle)

    log("--- WORKER DONE ---")