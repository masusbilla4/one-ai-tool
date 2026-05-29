"""
Sentence Database - Core Supabase CRUD operations.
Handles: insert, update, delete, check_exists, generate_id

OPTIMIZED: Invalidates stats cache when data changes
"""
from supabase import create_client, Client
from config import Config
from settings.routes import get_supabase_config

# Import cache invalidation
try:
    from .stats import _invalidate_cache
except ImportError:
    _invalidate_cache = lambda: None


# Table names
TABLE_FIL = "fil_sentences"
TABLE_ENG = "eng_sentences"


def get_supabase_client() -> Client:
    """Create and return Supabase client using session or config credentials."""
    creds = get_supabase_config()
    if not creds:
        raise ValueError("Supabase credentials not configured. Go to Settings to add them.")
    return create_client(creds['url'], creds['key'])


def get_table_name(language: str) -> str:
    """Get table name for language."""
    return TABLE_ENG if language == "en" else TABLE_FIL


def generate_sen_id(language: str) -> str:
    """Generate next sentence ID for language."""
    client = get_supabase_client()
    table_name = get_table_name(language)
    prefix = "eng" if language == "en" else "fil"
    
    # Get last ID
    result = client.table(table_name).select("sen_id").order("sen_id", desc=True).limit(1).execute()
    
    if result.data:
        last_num = int(result.data[0]['sen_id'].split('_')[-1])
        next_num = last_num + 1
    else:
        next_num = 1
    
    return f"{prefix}_{next_num:06d}"


def check_sentence_exists(sentence: str, language: str = None) -> tuple:
    """
    Check if sentence exists in database.
    Returns: (exists: bool, sen_id: str, category: str, lang: str)
    """
    client = get_supabase_client()
    
    # Check Filipino table
    result = client.table(TABLE_FIL).select("sen_id,category,language").eq("sentence", sentence).execute()
    if result.data:
        row = result.data[0]
        return True, row['sen_id'], row['category'], row['language']
    
    # Check English table
    result = client.table(TABLE_ENG).select("sen_id,category,language").eq("sentence", sentence).execute()
    if result.data:
        row = result.data[0]
        return True, row['sen_id'], row['category'], row['language']
    
    return False, None, None, None


def insert_sentence(sentence: str, category: str, language: str) -> dict:
    """
    Insert a new sentence into the database.
    Returns: dict with sen_id and status
    
    OPTIMIZED: Invalidates stats cache after insert
    """
    char_count = len(sentence)
    word_count = len(sentence.split())
    sentence_count = max(1, sentence.count('.') + sentence.count('?'))
    
    table_name = get_table_name(language)
    sen_id = generate_sen_id(language)
    
    data = {
        "sen_id": sen_id,
        "sentence": sentence,
        "category": category,
        "language": language,
        "used": 0,
        "char_count": char_count,
        "word_count": word_count,
        "sentence_count": sentence_count
    }
    
    client = get_supabase_client()
    result = client.table(table_name).insert(data).execute()
    
    # Invalidate cache after data change
    _invalidate_cache()
    
    return {
        "sen_id": sen_id,
        "success": result.data is not None,
        "language": language,
        "category": category,
        "word_count": word_count
    }


def update_sentence(sen_id: str, text: str, language: str) -> dict:
    """
    Update an existing sentence.
    Returns: dict with status
    
    OPTIMIZED: Invalidates stats cache after update
    """
    client = get_supabase_client()
    table_name = get_table_name(language)
    
    result = client.table(table_name).update({"sentence": text}).eq("sen_id", sen_id).execute()
    
    # Invalidate cache after data change
    _invalidate_cache()
    
    return {
        "success": result.data is not None,
        "sen_id": sen_id
    }


def delete_sentence(sen_id: str, language: str) -> dict:
    """
    Delete a sentence by ID.
    Returns: dict with status
    
    OPTIMIZED: Invalidates stats cache after delete
    """
    client = get_supabase_client()
    table_name = get_table_name(language)
    
    result = client.table(table_name).delete().eq("sen_id", sen_id).execute()
    
    # Invalidate cache after data change
    _invalidate_cache()
    
    return {
        "success": result.data is not None or True,  # Supabase returns empty on success
        "sen_id": sen_id
    }


def mark_sentence_as_used(sentence: str, language: str, category: str) -> bool:
    """
    Mark a sentence as used.
    
    OPTIMIZED: Invalidates stats cache after marking used
    """
    client = get_supabase_client()
    table_name = get_table_name(language)
    
    result = client.table(table_name).update({"used": 1}).eq("sentence", sentence).eq("category", category).execute()
    
    # Invalidate cache after data change
    _invalidate_cache()
    
    return result.data is not None


def get_sentence_by_id(sen_id: str, language: str) -> dict:
    """Get a single sentence by ID."""
    client = get_supabase_client()
    table_name = get_table_name(language)
    
    result = client.table(table_name).select("*").eq("sen_id", sen_id).execute()
    if result.data:
        return result.data[0]
    return None
