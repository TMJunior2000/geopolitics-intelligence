import os
import json
import re
import html
import datetime as dt
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

# Librerie Ufficiali Google
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google import genai
from google.genai import types

# Libreria "Unofficial" per i sottotitoli
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound

from supabase import create_client, Client

# =========================
# CONFIG
# =========================
MODE = os.getenv("MODE", "LIVE").upper()
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")

YOUTUBE_CHANNELS = [
    "@InvestireBiz" 
]

BACKFILL_START = dt.date(2026, 1, 1)
BACKFILL_END = dt.date(2026, 1, 25)

# =========================
# INIT CLIENTS
# =========================
if not GOOGLE_API_KEY or not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Mancano variabili d'ambiente critiche")

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    gemini_client = genai.Client(api_key=GOOGLE_API_KEY)
    youtube_service = build('youtube', 'v3', developerKey=GOOGLE_API_KEY)
except Exception as e:
    raise RuntimeError(f"Errore init client: {e}")

# =========================
# UTILS & LOGGING
# =========================
def log(msg):
    print(f"[{datetime.now(timezone.utc).isoformat()}] {msg}", flush=True)

def clean_html(raw_html):
    cleanr = re.compile('<.*?>')
    cleantext = re.sub(cleanr, '', raw_html)
    return html.unescape(cleantext)

def url_exists(url: str) -> bool:
    res = supabase.table("intelligence_feed").select("id").eq("url", url).execute()
    return len(res.data) > 0

def get_or_create_source(name, type_, base_url):
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
# YOUTUBE LOGIC (HYBRID)
# =========================

def get_channel_id_from_handle(handle: str) -> Optional[str]:
    try:
        request = youtube_service.channels().list(part="id", forHandle=handle)
        response = request.execute()
        return response['items'][0]['id'] if response['items'] else None
    except HttpError as e:
        log(f"Errore API Channel ID: {e}")
        return None

def get_uploads_playlist_id(channel_id: str) -> Optional[str]:
    try:
        request = youtube_service.channels().list(part="contentDetails", id=channel_id)
        response = request.execute()
        if response['items']:
            return response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
        return None
    except HttpError as e:
        log(f"Errore recupero playlist: {e}")
        return None

def get_latest_videos(playlist_id: str, limit=10) -> List[Dict]:
    videos = []
    try:
        request = youtube_service.playlistItems().list(
            part="snippet,contentDetails",
            playlistId=playlist_id,
            maxResults=limit
        )
        response = request.execute()
        
        for item in response.get('items', []):
            snippet = item['snippet']
            published_at_str = snippet['publishedAt']
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
        log(f"Errore recupero video: {e}")
    
    return videos

def get_hybrid_transcript(video_id: str) -> str:
    """
    Scarica i sottotitoli ISTANZIANDO la classe YouTubeTranscriptApi.
    """
    try:
        # 1. ISTANZIAMENTO DELL'OGGETTO
        # La documentazione dice: "Make sure to initialize an instance... per thread"
        ytt_api = YouTubeTranscriptApi() 

        # 2. CHIAMATA AL METODO DI ISTANZA .list()
        # Non usare metodi statici, usiamo l'oggetto creato.
        transcript_list_obj = ytt_api.list(video_id)

        # 3. LOGICA DI RICERCA (Identica a prima, ma lavora sull'oggetto restituito)
        # Cerchiamo Italiano o Inglese (manuale o auto-generato)
        try:
            # find_transcript è un metodo dell'oggetto TranscriptList restituito da .list()
            transcript = transcript_list_obj.find_transcript(['it', 'en'])
        except Exception:
            # Fallback: Se non c'è IT/EN, prendi il primo disponibile e traduci
            # TranscriptList è iterabile, il primo elemento è il primo transcript trovato
            first_transcript = next(iter(transcript_list_obj))
            transcript = first_transcript.translate('it') 

        # 4. SCARICAMENTO DATI
        # fetch() restituisce la lista di dizionari [{'text': ...}, ...]
        transcript_data = transcript.fetch()
        
        # 5. UNIONE TESTO
        full_text = " ".join([item.text for item in transcript_data])
        return full_text

    except Exception as e:
        # Cattura TranscriptsDisabled, NoTranscriptFound e altri errori
        # print(f"⚠️ Errore o sottotitoli assenti per {video_id}: {e}")
        return ""

# =========================
# CORE LOGIC
# =========================

def analyze_with_gemini(text: str) -> dict:
    if not text or len(text) < 50:
        return {"summary": "N/A", "risk_level": "LOW", "countries_involved": [], "keywords": []}

    prompt = """
    Sei un analista geopolitico. Analizza il testo fornito (trascrizione video o descrizione).
    Restituisci ESCLUSIVAMENTE un JSON valido con questa struttura:
    {
        "summary": "riassunto italiano max 3 frasi",
        "countries_involved": ["paese1", "paese2"],
        "risk_level": "LOW" | "MEDIUM" | "HIGH",
        "keywords": ["tag1", "tag2"]
    }
    """
    try:
        response = gemini_client.models.generate_content(
            model="gemini-2.0-flash",
            contents=f"{prompt}\n\nTesto:\n{text[:25000]}",
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        raw_json = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(raw_json)
    except Exception as e:
        log(f"Errore AI: {e}")
        return {"summary": "Errore AI", "error": str(e)}

def process_channel(handle_or_id: str):
    # 1. Risoluzione ID e Playlist (Via API Ufficiale - Safe)
    channel_id = handle_or_id
    if handle_or_id.startswith("@"):
        channel_id = get_channel_id_from_handle(handle_or_id)
        if not channel_id: return

    uploads_id = get_uploads_playlist_id(channel_id)
    if not uploads_id: return

    log(f"Scansione video per canale ID: {channel_id}...")
    videos = get_latest_videos(uploads_id, limit=10)

    if not videos: return

    channel_name = videos[0]['channel_title']
    source_id = get_or_create_source(channel_name, "youtube", f"https://youtube.com/channel/{channel_id}")

    for video in videos:
        # Filtri Data e Duplicati rimossi per brevità (uguali a prima)
        if url_exists(video['url']):
            log(f"Saltato (esistente): {video['title']}")
            continue
        
        log(f"Elaborazione: {video['title']}")

        # 2. Ottieni Transcript (Via Libreria "Unofficial")
        full_text = get_hybrid_transcript(video['id'])
        
        if full_text:
            log("✅ Sottotitoli scaricati con successo")
        else:
            # 3. Fallback se proprio non esistono
            full_text = f"TITOLO: {video['title']}\nDESCRIZIONE: {video['description']}"
            log("⚠️ Usato Fallback Titolo+Descrizione")

        analysis = analyze_with_gemini(full_text)

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
            log(f"💾 Salvato DB: {video['title']}")
        except Exception as e:
            log(f"Errore salvataggio DB: {e}")

if __name__ == "__main__":
    log(f"--- WORKER START (MODE={MODE}) ---")
    for handle in YOUTUBE_CHANNELS:
        process_channel(handle)
    log("--- WORKER DONE ---")