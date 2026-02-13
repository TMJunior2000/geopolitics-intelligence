from typing import List, Dict, Any, Optional, cast
from supabase.client import create_client, Client
from core.config import Config

class DBService:
    def __init__(self):
        self.client: Client = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)

