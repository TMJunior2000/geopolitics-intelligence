from supabase import create_client, Client
from core.config import Config

_client = None

def get_db_client() -> Client:
    global _client
    if _client is None:
        _client = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
    return _client