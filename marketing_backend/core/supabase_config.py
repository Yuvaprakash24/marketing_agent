import os

from django.utils.functional import SimpleLazyObject
from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')


def _build_client() -> Client:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError(
            'SUPABASE_URL and SUPABASE_KEY must be set to use Supabase authentication.'
        )
    return create_client(SUPABASE_URL, SUPABASE_KEY)


# Built on first use so management commands still run without credentials.
supabase: Client = SimpleLazyObject(_build_client)
