import os
import json
import re
import html
import datetime as dt
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google import genai
from google.genai import types
from supabase import create_client, Client

# =========================
# CONFIG
# =========================
MODE = os.getenv("MODE", "LIVE").upper()
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY") # Usata sia per Gemini che per YouTube Data API

# Usa gli Handle (@Nome) o direttamente i Channel ID se li hai per risparmiare quota
YOUTUBE_CHANNELS = [
    "@InvestireBiz" 
]

BACKFILL_START = dt.date(2026, 1, 1)
BACKFILL_END = dt.date(2026, 1, 25)

# =========================
# INIT CLIENTS
# =========================
if not GOOGLE_API_KEY or not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Mancano variabili d'ambiente critiche (GOOGLE_API_KEY, SUPABASE_URL/KEY)")

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    gemini_client = genai.Client(api_key=GOOGLE_API_KEY)
    # Servizio YouTube Data API v3
    youtube_service = build('youtube', 'v3', developerKey=GOOGLE_API_KEY)
except Exception as e:
    raise RuntimeError(f"Errore init client: {e}")

# =========================
# UTILS & LOGGING
# =========================
def log(msg):
    print(f"[{datetime.now(timezone.utc).isoformat()}] {msg}", flush=True)

def clean_html(raw_html):
    """Pulisce i tag HTML dalle descrizioni o dai sottotitoli grezzi."""
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
# YOUTUBE OFFICIAL API LOGIC
# =========================

def get_channel_id_from_handle(handle: str) -> Optional[str]:
    """
    Converte un handle (@Nome) in Channel ID.
    Costo Quota: 1 unit (channels.list)
    """
    try:
        request = youtube_service.channels().list(
            part="id",
            forHandle=handle
        )
        response = request.execute()
        if response['items']:
            return response['items'][0]['id']
        return None
    except HttpError as e:
        log(f"Errore API Channel ID per {handle}: {e}")
        return None

def get_uploads_playlist_id(channel_id: str) -> Optional[str]:
    """
    Ottiene l'ID della playlist "Uploads" del canale.
    Questo è il metodo PIÙ EFFICIENTE per ottenere i video (evita search.list).
    Costo Quota: 1 unit
    """
    try:
        request = youtube_service.channels().list(
            part="contentDetails",
            id=channel_id
        )
        response = request.execute()
        if response['items']:
            # La playlist "uploads" contiene tutti i video del canale
            return response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
        return None
    except HttpError as e:
        log(f"Errore recupero playlist uploads: {e}")
        return None

def get_latest_videos(playlist_id: str, limit=10) -> List[Dict]:
    """
    Scarica gli ultimi video dalla playlist Uploads.
    Costo Quota: 1 unit
    """
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
            # Data in formato ISO 8601 (es. 2026-01-20T10:00:00Z)
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
        log(f"Errore recupero video playlist: {e}")
    
    return videos

def get_official_transcript(video_id: str) -> str:
    """
    Tenta di scaricare i sottotitoli usando l'API ufficiale.
    NOTA: Spesso fallisce (403 Forbidden) per video non di proprietà.
    Costo Quota: ~50-100 units (alto!)
    """
    try:
        # 1. Lista delle caption disponibili (Costo: 50)
        list_request = youtube_service.captions().list(
            part="snippet",
            videoId=video_id
        )
        list_response = list_request.execute()
        
        caption_id = None
        # Cerca traccia in Italiano o Inglese
        for item in list_response.get('items', []):
            lang = item['snippet']['language']
            if 'it' in lang or 'en' in lang:
                caption_id = item['id']
                break
        
        if not caption_id:
            return ""

        # 2. Download della caption (Costo: 50)
        # Attenzione: Potrebbe dare 403 se l'autore non permette il download di terze parti
        download_request = youtube_service.captions().download(
            id=caption_id,
            tfmt="sbv" # SubViewer format (più pulito di altri)
        )
        subtitle_content = download_request.execute()
        
        # Il contenuto arriva come bytes o stringa formattata, va pulito dai timestamp
        text_content = str(subtitle_content)
        # Semplice pulizia regex per rimuovere timestamp (00:00:01,000)
        clean_text = re.sub(r'\d{1,2}:\d{2}:\d{2}.\d{3},?|-->', '', text_content)
        return clean_html(clean_text)

    except HttpError as e:
        # 403 è comune per video altrui via API ufficiale
        if e.resp.status == 403:
            log(f"Permesso negato per sottotitoli (API limit): {video_id}")
        else:
            log(f"Errore sottotitoli API: {e}")
        return ""

# =========================
# CORE LOGIC
# =========================

def analyze_with_gemini(text: str) -> dict:
    if not text or len(text) < 50:
        return {"summary": "N/A", "risk_level": "LOW", "countries_involved": [], "keywords": []}

    prompt = """
    Sei un analista geopolitico. Analizza il testo fornito.
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
            contents=f"{prompt}\n\nTesto da analizzare:\n{text[:25000]}", # Limite token safe
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        # Pulizia backticks se Gemini li aggiunge
        raw_json = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(raw_json)
    except Exception as e:
        log(f"Errore AI: {e}")
        return {"summary": "Errore AI", "error": str(e)}

def process_channel(handle_or_id: str):
    # 1. Risolvi ID Canale
    channel_id = handle_or_id
    if handle_or_id.startswith("@"):
        channel_id = get_channel_id_from_handle(handle_or_id)
        if not channel_id:
            log(f"Impossibile trovare ID per {handle_or_id}")
            return

    # 2. Ottieni ID Playlist "Uploads" (Metodo efficiente)
    uploads_id = get_uploads_playlist_id(channel_id)
    if not uploads_id:
        log(f"Nessuna playlist uploads trovata per {channel_id}")
        return

    # 3. Ottieni lista video
    log(f"Scansione video per canale ID: {channel_id}...")
    videos = get_latest_videos(uploads_id, limit=10)

    if not videos:
        log("Nessun video trovato.")
        return

    # Salva/Recupera Source ID nel DB
    channel_name = videos[0]['channel_title'] if videos else handle_or_id
    source_id = get_or_create_source(channel_name, "youtube", f"https://youtube.com/channel/{channel_id}")

    for video in videos:
        video_date = video['published_at'].date()
        now = datetime.now(timezone.utc).date()

        # LOGICA FILTRO DATE
        if MODE == "LIVE":
            # Accetta video di oggi e ieri
            if (now - video_date).days > 1:
                continue
        else: # BACKFILL
            if not (BACKFILL_START <= video_date <= BACKFILL_END):
                continue

        # CHECK DUPLICATI
        if url_exists(video['url']):
            log(f"Saltato (esistente): {video['title']}")
            continue
        
        log(f"Elaborazione: {video['title']}")

        # 4. Ottieni contenuto (Transcript API o Fallback Descrizione)
        # Nota: L'API ufficiale fallirà quasi sempre per i sub di terzi (Costoso e Restrittivo)
        # Usiamo un approccio ibrido: prova API, se fallisce usa descrizione ricca.
        
        full_text = ""
        # Decommenta sotto se vuoi provare a spendere quota per i sub (spesso 403 Forbidden)
        # full_text = get_official_transcript(video['id'])
        
        if not full_text:
            # Fallback robusto: Uniamo Titolo + Descrizione
            full_text = f"TITOLO: {video['title']}\nDESCRIZIONE: {video['description']}"
            log("Usato Titolo+Descrizione (No sub disponibili via API Ufficiale)")

        # 5. Analisi AI
        analysis = analyze_with_gemini(full_text)

        # 6. Salvataggio su Supabase
        try:
            supabase.table("intelligence_feed").insert({
                "source_id": source_id,
                "title": video['title'],
                "url": video['url'],
                "published_at": video['published_at'].isoformat(),
                "content": full_text, # Salviamo quello che abbiamo trovato
                "analysis": analysis,
                "raw_metadata": {"id": video['id'], "channel_id": channel_id}
            }).execute()
            log(f"✅ Salvato: {video['title']}")
        except Exception as e:
            log(f"Errore salvataggio DB: {e}")

# =========================
# MAIN
# =========================
if __name__ == "__main__":
    log(f"--- WORKER START (MODE={MODE}) ---")
    
    for handle in YOUTUBE_CHANNELS:
        process_channel(handle)

    log("--- WORKER DONE ---")