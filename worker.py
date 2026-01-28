import os
import json
import time
import requests
import datetime as dt
from datetime import datetime
from typing import Optional, Dict, Any

from googleapiclient.discovery import build
from google import genai
from google.genai import types
from supabase import create_client, Client

# --- CONFIGURAZIONE ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not SUPABASE_URL or not SUPABASE_KEY or not GOOGLE_API_KEY:
    raise ValueError("❌ ERRORE: Variabili mancanti.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
gemini_client = genai.Client(api_key=GOOGLE_API_KEY)
youtube_service = build('youtube', 'v3', developerKey=GOOGLE_API_KEY)

YOUTUBE_CHANNELS = ["@InvestireBiz"]

# --- FUNZIONE RECUPERO TESTO (STRATEGIA INVIDIOUS) ---
def get_transcript_via_invidious(video_id: str) -> str:
    """Scarica sottotitoli usando una rotazione di server Invidious."""
    instances = [
        "https://inv.tux.pizza",
        "https://invidious.drgns.space",
        "https://vid.puffyan.us",
        "https://inv.zzls.xyz",
        "https://yt.artemislena.eu"
    ]
    
    print("   🕵️  Cerco sottotitoli su Invidious...")
    
    for instance in instances:
        try:
            # Chiede metadati sottotitoli
            url = f"{instance}/api/v1/captions/{video_id}"
            res = requests.get(url, timeout=5)
            if res.status_code != 200: continue
            
            captions = res.json()
            if not captions or not isinstance(captions, list): continue

            # Cerca Italiano > Inglese > Primo disponibile
            target = None
            for c in captions:
                if c.get('language') == 'Italian' or c.get('code') == 'it':
                    target = c; break
            
            # Se non trova italiano, cerca inglese
            if not target:
                for c in captions:
                    if 'en' in c.get('code', ''): target = c; break
            
            # Se nemmeno inglese, prendi il primo
            if not target: target = captions[0]

            # Scarica il testo vero e proprio
            full_url = f"{instance}{target['url']}"
            text_res = requests.get(full_url, timeout=5)
            
            if text_res.status_code == 200:
                # Pulizia VTT (rimuove timestamp e header)
                lines = [l.strip() for l in text_res.text.splitlines() 
                         if "-->" not in l and l.strip() and not l.startswith(("WEBVTT", "NOTE"))]
                
                # Rimuove duplicati consecutivi
                clean_text = []
                for l in lines:
                    if not clean_text or clean_text[-1] != l:
                        clean_text.append(l)
                
                print(f"   ✅ Trovati su: {instance}")
                return " ".join(clean_text)

        except Exception:
            continue
            
    return ""

# --- ANALISI AI ---
def analyze_gemini(text: str) -> dict:
    if not text or len(text) < 50: 
        return {"summary": "N/A", "risk_level": "LOW", "countries_involved": []}
    
    prompt = """
    Analizza il testo. Output JSON ESCLUSIVO:
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
        ch_res = youtube_service.channels().list(part="id,contentDetails,snippet", forHandle=handle).execute()
        if not ch_res.get('items'): return []
        upl = ch_res['items'][0]['contentDetails']['relatedPlaylists']['uploads']
        ch_title = ch_res['items'][0]['snippet']['title']
        ch_id = ch_res['items'][0]['id']
        
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
    print("--- 🚀 START WORKER (INVIDIOUS MODE) ---")
    for handle in YOUTUBE_CHANNELS:
        for v in get_channel_videos(handle):
            if url_exists(v['url']): continue
            
            print(f"🔄 {v['title'][:40]}...")
            
            # 1. TENTA INVIDIOUS (Sottotitoli)
            text = get_transcript_via_invidious(v['id'])
            method = "Invidious"
            
            # 2. FALLBACK DESCRIZIONE
            if not text:
                print("   ⚠️ Sottotitoli non trovati. Uso descrizione.")
                text = f"{v['title']}\n{v['desc']}"
                method = "Descrizione"
            
            # 3. ANALISI & SALVATAGGIO
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
                except Exception as e:
                    if "duplicate" in str(e): print("   ⏭️ Duplicato.")
                    else: print(f"   ❌ Errore DB: {e}")
            
            time.sleep(2)
    print("--- END ---")