import os
import json
import time
from typing import cast, List, Dict, Any

# Libreria ufficiale Apify
from apify_client import ApifyClient

from googleapiclient.discovery import build
from google import genai
from google.genai import types
from supabase import create_client, Client

# --- CONFIGURAZIONE ---
print("\n🔧 [INIT] Avvio script (APIFY OFFICIAL CLIENT)...")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
APIFY_TOKEN = os.getenv("APIFY_TOKEN")

if not all([SUPABASE_URL, SUPABASE_KEY, GOOGLE_API_KEY, APIFY_TOKEN]):
    print("❌ ERRORE: Variabili d'ambiente mancanti (Controlla i Secrets di GitHub).")
    exit(1)

try:
    # Inizializzazione client secondo la classe ApifyClient che hai postato
    apify_client = ApifyClient(token=APIFY_TOKEN)
    
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    gemini_client = genai.Client(api_key=GOOGLE_API_KEY)
    youtube_service = build('youtube', 'v3', developerKey=GOOGLE_API_KEY)
    print("✅ Tutti i client (Apify, Supabase, Gemini, YouTube) inizializzati.")
except Exception as e:
    print(f"❌ ERRORE DURANTE L'INIZIALIZZAZIONE: {e}")
    exit(1)

YOUTUBE_CHANNELS = ["@InvestireBiz"]

# --- FUNZIONE TRASCRITTO (VIA APIFY CLIENT) ---
def get_transcript_apify(video_url: str) -> str:
    print(f"   🤖 [APIFY] Delegando recupero sottotitoli per: {video_url}")
    
    # Utilizziamo l'Actor più affidabile ed economico per i transcript
    # ID Actor: 'streamot/youtube-transcript-scraper'
    actor_id = "streamot/youtube-transcript-scraper"
    
    run_input = {
        "videoUrls": [video_url],
        "subtitlesLanguage": "it",
        "addVideoMetadata": False
    }

    try:
        # Invocazione dell'Actor (Metodo sincrono .call() visto nella classe _BaseApifyClient)
        # Questo comando attende che l'elaborazione cloud sia finita.
        run = apify_client.actor(actor_id).call(run_input=run_input)
        
        # Accesso al Dataset (il contenitore dei risultati della Run)
        # Utilizziamo il metodo .dataset() della classe ApifyClient
        dataset_items = apify_client.dataset(run["defaultDatasetId"]).list_items().items
        
        if dataset_items:
            item = dataset_items[0]
            # Estrazione del testo: l'actor restituisce 'transcript' o 'text'
            transcript = item.get("transcript") or item.get("text") or ""
            
            if isinstance(transcript, list):
                # Se i sottotitoli sono divisi in segmenti, li uniamo
                transcript = " ".join([segment.get("text", "") for segment in transcript])
            
            if len(transcript) > 50:
                print(f"      ✅ Trascrizione ottenuta: {len(transcript)} caratteri.")
                return transcript
        
        print("      ⚠️ Attenzione: Apify ha concluso ma il dataset è vuoto.")
    except Exception as e:
        print(f"      ❌ Errore durante la chiamata ad Apify: {e}")
        
    return ""

# --- ANALISI GEMINI 2.0 FLASH ---
def analyze_gemini(text: str) -> dict:
    if not text or len(text) < 50:
        return {"summary": "Analisi non disponibile", "risk_level": "UNKNOWN"}
    
    print(f"   🧠 [GEMINI] Analisi del testo ({len(text)} caratteri)...")
    
    prompt = (
        "Analizza il seguente trascritto di un video finanziario e restituisci un JSON con questa struttura:\n"
        "{\n"
        "  \"summary\": \"riassunto dettagliato in italiano\",\n"
        "  \"risk_level\": \"LOW/MEDIUM/HIGH\",\n"
        "  \"countries_involved\": [\"lista paesi\"],\n"
        "  \"key_takeaway\": \"punto chiave principale\"\n"
        "}\n"
        f"TEXT: {text[:28000]}" # Limite di sicurezza per il context window
    )

    for attempt in range(3):
        try:
            response = gemini_client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json")
            )
            return json.loads(response.text.strip())
        except Exception as e:
            if "429" in str(e):
                print(f"      ⚠️ Quota Gemini esaurita (429). Tentativo {attempt+1}/3. Attesa 35s...")
                time.sleep(35)
            else:
                print(f"      ❌ Errore Gemini: {e}")
                return {}
    return {}

# --- GESTIONE DATABASE (SUPABASE) ---
def get_source_id(name, ch_id):
    try:
        res = supabase.table("sources").select("id").eq("name", name).execute()
        data = cast(List[Dict[str, Any]], res.data)
        if data: return str(data[0]['id'])
        
        # Se non esiste, crea la sorgente (type 'youtube' per via del check constraint)
        new = supabase.table("sources").insert({
            "name": name, 
            "type": "youtube", 
            "base_url": ch_id
        }).execute()
        new_data = cast(List[Dict[str, Any]], new.data)
        if new_data: return str(new_data[0]['id'])
    except Exception as e:
        print(f"   ❌ Errore DB Source ID: {e}")
    return None

def get_channel_videos(handle):
    videos = []
    try:
        # Recupero ID canale e Playlist Uploads
        res = youtube_service.channels().list(part="contentDetails,snippet", forHandle=handle).execute()
        if not res.get('items'): return []
        
        uploads_playlist_id = res['items'][0]['contentDetails']['relatedPlaylists']['uploads']
        channel_title = res['items'][0]['snippet']['title']
        channel_id = res['items'][0]['id']
        
        # Recupero ultimi 5 video
        playlist_res = youtube_service.playlistItems().list(
            part="snippet", 
            playlistId=uploads_playlist_id, 
            maxResults=5
        ).execute()
        
        for item in playlist_res.get('items', []):
            snippet = item['snippet']
            videos.append({
                "id": snippet['resourceId']['videoId'],
                "title": snippet['title'],
                "desc": snippet['description'],
                "date": snippet['publishedAt'],
                "url": f"https://www.youtube.com/watch?v={snippet['resourceId']['videoId']}",
                "ch_title": channel_title,
                "ch_id": channel_id
            })
    except Exception as e:
        print(f"   ❌ Errore YouTube API: {e}")
    return videos

# --- MAIN LOOP ---
if __name__ == "__main__":
    print("\n--- 🚀 START WORKER (APIFY CLOUD INTEGRATION) ---")
    
    for handle in YOUTUBE_CHANNELS:
        latest_videos = get_channel_videos(handle)
        
        for video in latest_videos:
            print(f"\n🔄 Processando: {video['title'][:50]}...")
            
            # Verifica se già presente nel DB per evitare sprechi di credito Apify/Gemini
            try:
                check = supabase.table("intelligence_feed").select("id").eq("url", video['url']).execute()
                if check.data:
                    print("   ⏭️  Video già analizzato. Salto.")
                    continue
            except: pass

            # 1. Recupero Sottotitoli tramite Apify
            transcript_text = get_transcript_apify(video['url'])
            processing_method = "Apify-Cloud"
            
            if not transcript_text:
                print("   ⚠️ Sottotitoli non trovati. Uso Descrizione come fallback.")
                transcript_text = f"TITOLO: {video['title']}\nDESCRIZIONE: {video['desc']}"
                processing_method = "YouTube-Description-Fallback"

            # 2. Analisi AI con Gemini
            analysis_result = analyze_gemini(transcript_text)
            
            # 3. Salvataggio nel Database
            source_id = get_source_id(video['ch_title'], video['ch_id'])
            
            if source_id:
                try:
                    insert_data = {
                        "source_id": source_id,
                        "title": video['title'],
                        "url": video['url'],
                        "published_at": video['date'],
                        "content": transcript_text,
                        "analysis": analysis_result,
                        "raw_metadata": {"method": processing_method, "vid": video['id']}
                    }
                    supabase.table("intelligence_feed").insert(insert_data).execute()
                    print(f"   💾 SALVATO CON SUCCESSO!")
                except Exception as e:
                    if "23505" in str(e):
                        print("   ⏭️  Duplicato rilevato in fase di salvataggio.")
                    else:
                        print(f"   ❌ Errore inserimento DB: {e}")
            
            # Breve pausa per non saturare le API
            time.sleep(2)
            
    print("\n--- ✅ WORKER COMPLETATO ---")