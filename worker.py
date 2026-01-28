import os
import json
import time
import requests
import traceback
from datetime import datetime
from typing import cast, List, Dict, Any

from googleapiclient.discovery import build
from google import genai
from google.genai import types
from supabase import create_client, Client

# --- SETUP & CONFIG ---
print("\n🔧 [INIT] Avvio script...")
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

# --- 1. SCARICAMENTO SOTTOTITOLI (Proxy + Invidious Extended) ---
def get_transcript_via_proxy(video_id: str) -> str:
    print(f"   🕵️  [SUB] Cerco sottotitoli per {video_id}...")
    
    # LISTA ESTESA DI ISTANZE (Per massimizzare le chance)
    instances = [
        "https://inv.nadeko.net",
        "https://invidious.jing.rocks",
        "https://yewtu.be",
        "https://vid.puffyan.us",
        "https://inv.zzls.xyz",
        "https://invidious.nerdvpn.de",
        "https://invidious.incogni.to",
        "https://yt.drgnz.club",
        "https://invidious.no-logs.com"
    ]
    
    # Proxy SOCKS5h (Risoluzione DNS remota)
    proxies = {
        "http": "socks5h://127.0.0.1:40000",
        "https": "socks5h://127.0.0.1:40000"
    }

    for instance in instances:
        try:
            # Timeout breve per scorrere veloce
            res = requests.get(f"{instance}/api/v1/captions/{video_id}", proxies=proxies, timeout=5)
            
            if res.status_code != 200: continue
            
            captions = res.json()
            if not isinstance(captions, list): continue
            
            # Logica scelta lingua: IT > EN > Primo
            target = None
            for c in captions:
                if c.get('language') == 'Italian' or c.get('code') == 'it':
                    target = c; break
            
            if not target:
                for c in captions:
                    if 'en' in c.get('code', ''): target = c; break
            
            if not target and captions: target = captions[0]

            if target:
                print(f"      ⬇️  Trovato su {instance}. Scarico...")
                full_url = f"{instance}{target['url']}"
                text_res = requests.get(full_url, proxies=proxies, timeout=10)
                
                if text_res.status_code == 200:
                    raw_text = text_res.text
                    clean_text = ""
                    
                    # Parsing JSON (alcune istanze tornano JSON)
                    if raw_text.strip().startswith('{') or raw_text.strip().startswith('['):
                        try:
                            data = json.loads(raw_text)
                            clean_text = " ".join([x.get('content', '') for x in data if 'content' in x])
                        except: pass
                    # Parsing VTT
                    else:
                        lines = [l.strip() for l in raw_text.splitlines() 
                                 if "-->" not in l and l.strip() and not l.startswith(("WEBVTT", "NOTE"))]
                        clean_text = " ".join(dict.fromkeys(lines)) # Deduplica mantenendo ordine

                    if len(clean_text) > 50:
                        print(f"   ✅ Testo estratto: {len(clean_text)} chars.")
                        return clean_text

        except Exception:
            # print(f"Debug: fail su {instance}") # Decommenta se vuoi vedere i fallimenti
            continue
            
    print("   ⚠️ Sottotitoli non trovati (Fallback Descrizione).")
    return ""

# --- 2. ANALISI GEMINI (Con Retry 429) ---
def analyze_gemini(text: str) -> dict:
    if not text or len(text) < 50: return {"summary": "N/A"}
    
    print(f"   🧠 [AI] Invio a Gemini ({len(text)} chars)...")
    
    for attempt in range(3): # 3 Tentativi
        try:
            res = gemini_client.models.generate_content(
                model="gemini-2.0-flash",
                contents=f'Analizza JSON: {{ "summary": "Riassunto dettagliato", "risk_level": "LOW", "countries_involved": [], "key_takeaway": "Punto chiave" }}\nTEXT:{text[:25000]}',
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

# --- 3. GESTIONE DB (Source ID) ---
def get_source_id(name, ch_id):
    try:
        # Check esistenza
        res = supabase.table("sources").select("id").eq("name", name).execute()
        data = cast(List[Dict[str, Any]], res.data)
        
        if data: return str(data[0]['id'])
        
        # Creazione Nuova Source
        print("      ➕ Creo nuova source nel DB...")
        
        # type='youtube' è corretto per il tuo DB
        new = supabase.table("sources").insert({
            "name": name, 
            "type": "youtube",
            "base_url": ch_id
        }).execute()
        
        new_data = cast(List[Dict[str, Any]], new.data)
        if new_data: return str(new_data[0]['id'])
            
    except Exception as e:
        print(f"   ❌ [DB ERROR] get_source_id: {e}")
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
    print("\n--- 🚀 START WORKER (OPTIMIZED) ---")
    
    for handle in YOUTUBE_CHANNELS:
        videos = get_channel_videos(handle)
        
        for v in videos:
            print(f"\n🔄 {v['title'][:40]}...")
            
            # Check DB Preliminare (Per risparmiare API Gemini)
            try:
                exists = supabase.table("intelligence_feed").select("id").eq("url", v['url']).execute()
                exists_data = cast(List[Dict[str, Any]], exists.data)
                if exists_data:
                    print("   ⏭️  Video già analizzato. Salto.")
                    continue
            except: pass

            # 1. Testo
            text = get_transcript_via_proxy(v['id'])
            method = "Invidious+Proxy"
            if not text:
                text = f"{v['title']}\n{v['desc']}"
                method = "Descrizione"
            
            # 2. Analisi
            analysis = analyze_gemini(text)
            
            # 3. Salvataggio
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
                    # Gestione elegante dell'errore duplicato
                    if "23505" in str(e) or "duplicate key" in str(e):
                         print("   ⏭️  Già presente (rilevato all'inserimento).")
                    else:
                        print(f"   ❌ ERRORE INSERT: {e}")
            
            # Pausa anti-ban
            print("   💤 Pause 10s...")
            time.sleep(10)
            
    print("\n--- ✅ FINITO ---")