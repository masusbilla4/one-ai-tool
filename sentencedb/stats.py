"""
Sentence Database - Statistics functions.
Handles: get_stats, get_remaining_stats, get_categories, get_category_stats, get_database_info

OPTIMIZATIONS:
- Uses Supabase count queries instead of fetching all data
- Caches results to reduce API calls
- Combines multiple queries into single requests where possible
"""
from supabase import create_client, Client
from config import Config
from functools import lru_cache
import time

from .db import get_supabase_client, get_table_name, TABLE_FIL, TABLE_ENG

# Cache for stats (invalidate when data changes)
_stats_cache = {}
_CACHE_TTL = 30  # Cache TTL in seconds


def _get_cached(key):
    """Get cached value if not expired."""
    if key in _stats_cache:
        data, timestamp = _stats_cache[key]
        if time.time() - timestamp < _CACHE_TTL:
            return data
    return None


def _set_cached(key, data):
    """Set cached value with timestamp."""
    _stats_cache[key] = (data, time.time())


def _invalidate_cache():
    """Invalidate all cached stats."""
    _stats_cache.clear()


def get_stats() -> tuple:
    """
    Get total sentence counts.
    Returns: (total, eng, fil)
    
    OPTIMIZED: Uses count="exact" instead of fetching all rows
    """
    # Check cache
    cached = _get_cached('stats')
    if cached:
        return cached
    
    client = get_supabase_client()
    
    # Use count query - much faster than fetching all data
    result_fil = client.table(TABLE_FIL).select("sen_id", count="exact").execute()
    fil = result_fil.count if hasattr(result_fil, 'count') else len(result_fil.data)
    
    result_eng = client.table(TABLE_ENG).select("sen_id", count="exact").execute()
    eng = result_eng.count if hasattr(result_eng, 'count') else len(result_eng.data)
    
    result = (fil + eng, eng, fil)
    _set_cached('stats', result)
    return result


def get_remaining_stats() -> tuple:
    """
    Get remaining (unused) sentence counts.
    Returns: (fil_remaining, eng_remaining)
    
    OPTIMIZED: Uses filtered count query instead of fetching all data
    """
    # Check cache
    cached = _get_cached('remaining')
    if cached:
        return cached
    
    client = get_supabase_client()
    
    # Filtered count query - only counts unused sentences
    result_fil = client.table(TABLE_FIL).select("sen_id", count="exact").eq("used", 0).execute()
    fil = result_fil.count if hasattr(result_fil, 'count') else len(result_fil.data)
    
    result_eng = client.table(TABLE_ENG).select("sen_id", count="exact").eq("used", 0).execute()
    eng = result_eng.count if hasattr(result_eng, 'count') else len(result_eng.data)
    
    result = (fil, eng)
    _set_cached('remaining', result)
    return result


def get_categories() -> list:
    """
    Get all unique categories from both tables.
    
    OPTIMIZED: Only selects category column, not all data
    """
    # Check cache
    cached = _get_cached('categories')
    if cached:
        return cached
    
    client = get_supabase_client()
    
    # Only fetch category column - much less data
    result_fil = client.table(TABLE_FIL).select("category").execute()
    result_eng = client.table(TABLE_ENG).select("category").execute()
    
    categories = set()
    for row in result_fil.data:
        if row.get('category'):
            categories.add(row['category'])
    for row in result_eng.data:
        if row.get('category'):
            categories.add(row['category'])
    
    result = sorted(list(categories))
    _set_cached('categories', result)
    return result


def get_category_stats() -> list:
    """
    Get statistics per category.
    Returns: list of dicts with category breakdown
    
    OPTIMIZED: 
    - Uses aggregated count queries per category
    - Fetches only needed columns (category, used)
    """
    # Check cache
    cached = _get_cached('category_stats')
    if cached:
        return cached
    
    client = get_supabase_client()
    
    # Get categories first (cached)
    categories = get_categories()
    
    stats = []
    for cat in categories:
        entry = {"category": cat}
        
        # Count total and used for Filipino
        fil_total = client.table(TABLE_FIL).select("sen_id", count="exact").eq("category", cat).execute()
        fil_used = client.table(TABLE_FIL).select("sen_id", count="exact").eq("category", cat).eq("used", 1).execute()
        
        # Count total and used for English
        eng_total = client.table(TABLE_ENG).select("sen_id", count="exact").eq("category", cat).execute()
        eng_used = client.table(TABLE_ENG).select("sen_id", count="exact").eq("category", cat).eq("used", 1).execute()
        
        entry["fil_total"] = fil_total.count if hasattr(fil_total, 'count') else 0
        entry["fil_used"] = fil_used.count if hasattr(fil_used, 'count') else 0
        entry["fil_remaining"] = entry["fil_total"] - entry["fil_used"]
        
        entry["eng_total"] = eng_total.count if hasattr(eng_total, 'count') else 0
        entry["eng_used"] = eng_used.count if hasattr(eng_used, 'count') else 0
        entry["eng_remaining"] = entry["eng_total"] - entry["eng_used"]
        
        stats.append(entry)
    
    _set_cached('category_stats', stats)
    return stats


def get_database_info() -> dict:
    """
    Get comprehensive database information.
    Returns: dict with all stats
    """
    total, eng, fil = get_stats()
    fil_remaining, eng_remaining = get_remaining_stats()
    categories = get_categories()
    
    # Count duplicates
    duplicates = count_duplicates()
    
    return {
        'fil_total': fil,
        'fil_used': fil - fil_remaining,
        'fil_available': fil_remaining,
        'eng_total': eng,
        'eng_used': eng - eng_remaining,
        'eng_available': eng_remaining,
        'categories': len(categories),
        'duplicates': duplicates
    }


def count_duplicates() -> int:
    """Count total duplicate sentences across both tables."""
    client = get_supabase_client()
    duplicates = 0
    
    for table in [TABLE_FIL, TABLE_ENG]:
        result = client.table(table).select("sentence").execute()
        sentences = [r['sentence'] for r in result.data]
        dup_counts = {}
        for s in sentences:
            dup_counts[s] = dup_counts.get(s, 0) + 1
        for s, c in dup_counts.items():
            if c > 1:
                duplicates += c - 1
    
    return duplicates
