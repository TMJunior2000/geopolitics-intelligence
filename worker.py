import os
import json
import time
import glob
import re
from datetime import datetime
from typing import cast, List, Dict, Any

# Importiamo yt-dlp
import yt_dlp

from googleapiclient.discovery import build
from google import genai
from google.genai import types
from supabase import create_client, Client

# --- CONFIGURAZIONE ---
print("\n🔧 [INIT] Avvio script (yt-dlp MODE)...")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not SUPABASE_URL or not SUPABASE_KEY or not GOOGLE_API_KEY:
    print("❌ ERRORE: Variabili mancanti.")
    exit(1)

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    gemini_client = genai.Client(api_key=GOOGLE_API_KEY)
    youtube_service = build('youtube', 'v3', developerKey=GOOGLE_API_KEY)
    print("✅ Client inizializzati.")
except Exception as e:
    print(f"❌ ERRORE INIT: {e}")
    exit(1)

YOUTUBE_CHANNELS = ["@InvestireBiz"]

# --- FUNZIONE PULIZIA TESTO VTT ---
def clean_vtt_text(vtt_content: str) -> str:
    """Rimuove timestamp, header e tag HTML dal formato VTT"""
    lines = vtt_content.splitlines()
    text_lines = []
    seen = set() # Per rimuovere duplicati consecutivi o frasi ripetute
    
    for line in lines:
        line = line.strip()
        # Filtra metadati VTT, timestamp e numeri di sequenza
        if (not line or 
            line.startswith("WEBVTT") or 
            "-->" in line or 
            line.startswith("Kind:") or 
            line.startswith("Language:") or
            re.match(r'^\d+$', line)): 
            continue
        
        # Rimuove tag HTML interni (es. <c.colorE5E5E5>)
        line = re.sub(r'<[^>]+>', '', line)
        # Rimuove caratteri strani iniziali
        line = line.replace("&nbsp;", " ")
        
        if line and line not in seen:
            text_lines.append(line)
            seen.add(line)
            
    return " ".join(text_lines)

# --- 1. RECUPERO TESTO (yt-dlp via Proxy) ---
def get_transcript_ytdlp(video_url: str) -> str:
    print(f"   🕵️  [YT-DLP] Scarico subs per {video_url}...")
    
    # Configurazione per passare dal Proxy WARP
    ydl_opts = {
        'proxy': 'socks5://127.0.0.1:40000', # <--- PASSA DAL TUNNEL CLOUDFLARE
        'skip_download': True,               # Non scaricare il video
        'writesubtitles': True,              # Scarica subs manuali
        'writeautomaticsub': True,           # Scarica subs auto-generati (IMPORTANTE!)
        'subtitleslangs': ['it', 'en'],      # Prima Italiano, poi Inglese
        'outtmpl': '/tmp/%(id)s',            # Salva nella cartella temporanea
        'quiet': True,
        'no_warnings': True,
        'socket_timeout': 10,
    }

    try:
        # Pulisce vecchi file in /tmp per non fare confusione
        for f in glob.glob("/tmp/*.vtt"): os.remove(f)

        # Esegue il download dei soli sottotitoli
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])

        # Cerca il file scaricato
        files = glob.glob("/tmp/*.vtt")
        if not files:
            print("      ⚠️ yt-dlp non ha trovato file VTT (niente subs).")
            return ""
        
        # Se c'è sia IT che EN, preferisci IT (yt-dlp aggiunge la lingua nel nome file)
        target_file = files[0]
        for f in files:
            if ".it." in f: 
                target_file = f
                break
        
        print(f"      ✅ File VTT scaricato: {os.path.basename(target_file)}")
        
        # Legge e pulisce
        with open(target_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        clean_text = clean_vtt_text(content)
        
        if len(clean_text) > 100:
            print(f"      ✅ Testo pulito ed estratto: {len(clean_text)} caratteri.")
            return clean_text
        else:
            print("      ⚠️ Testo troppo breve dopo la pulizia.")
            return ""

    except Exception as e:
        print(f"      ❌ Errore yt-dlp: {e}")
        return ""

# --- 2. ANALISI GEMINI (Retry 429) ---
def analyze_gemini(text: str) -> dict:
    if not text or len(text) < 50: return {"summary": "N/A"}
    
    print(f"   🧠 [AI] Invio a Gemini ({len(text)} chars)...")
    
    for attempt in range(3):
        try:
            res = gemini_client.models.generate_content(
                model="gemini-2.0-flash",
                contents=f'Analizza JSON: {{ "summary": "Riassunto dettagliato", "risk_level": "LOW", "countries_involved": [], "key_takeaway": "Punto chiave" }}\nTEXT:{text[:28000]}',
                config=types.GenerateContentConfig(response_mime_type="application/json")
            )
            return json.loads(res.text.replace("```json","").replace("```","").strip())
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                wait = 35 * (attempt + 1)
                print(f"      ⚠️ Quota AI esaurita. Attendo {wait}s...")
                time.sleep(wait)
            else:
                print(f"      ❌ Errore AI: {e}")
                return {}
    return {}

# --- 3. DATABASE (Fix Constraint) ---
def get_source_id(name, ch_id):
    try:
        res = supabase.table("sources").select("id").eq("name", name).execute()
        # Fix per typing Pylance
        data = cast(List[Dict[str, Any]], res.data)
        
        if data: return str(data[0]['id'])
        
        print("      ➕ Creo nuova source...")
        # type='youtube' è fondamentale per il check constraint del DB
        new = supabase.table("sources").insert({
            "name": name, 
            "type": "youtube", 
            "base_url": ch_id
        }).execute()
        
        new_data = cast(List[Dict[str, Any]], new.data)
        if new_data: return str(new_data[0]['id'])
            
    except Exception as e:
        print(f"   ❌ DB Error: {e}")
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

# --- MAIN LOOP ---
if __name__ == "__main__":
    print("\n--- 🚀 START WORKER (YT-DLP + AUTO-SUBS) ---")
    
    for handle in YOUTUBE_CHANNELS:
        videos = get_channel_videos(handle)
        
        for v in videos:
            print(f"\n🔄 {v['title'][:40]}...")
            
            # Check DB
            try:
                exists = supabase.table("intelligence_feed").select("id").eq("url", v['url']).execute()
                exists_data = cast(List[Dict[str, Any]], exists.data)
                if exists_data:
                    print("   ⏭️  Già presente nel DB.")
                    continue
            except: pass

            # 1. RECUPERO TESTO (Priorità yt-dlp)
            text = get_transcript_ytdlp(v['url'])
            method = "yt-dlp+Proxy"
            
            # Fallback solo se yt-dlp fallisce totalmente
            if not text:
                print("   ⚠️ Fallback Descrizione (subs assenti).")
                text = f"{v['title']}\n{v['desc']}"
                method = "Descrizione"
            else:
                print("   🔥 SUBS RECUPERATI!")

            # 2. ANALISI
            analysis = analyze_gemini(text)
            
            # 3. SALVATAGGIO
            sid = get_source_id(v['ch_title'], v['ch_id'])
            
            if sid:
                try:
                    data = {
                        "source_id": sid, 
                        "title": v['title'], 
                        "url": v['url'],
                        "published_at": v['date'], 
                        "content": text, 
                        "analysis": analysis,
                        "raw_metadata": {"vid": v['id'], "method": method}
                    }
                    supabase.table("intelligence_feed").insert(data).execute()
                    print(f"   💾 SALVATO CON SUCCESSO!")
                except Exception as e:
                    if "duplicate" in str(e) or "23505" in str(e):
                        print("   ⏭️  Già presente (rilevato al salvataggio).")
                    else:
                        print(f"   ❌ Errore Insert: {e}")
            
            print("   💤 Pause 10s...")
            time.sleep(10)
            
    print("\n--- ✅ FINITO ---")