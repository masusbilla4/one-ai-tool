"""
Sentence Database - Statistics functions.
Handles: get_stats, get_remaining_stats, get_categories, get_category_stats, get_database_info
"""
from supabase import create_client, Client
from config import Config

from .db import get_supabase_client, get_table_name, TABLE_FIL, TABLE_ENG


def get_stats() -> tuple:
    """
    Get total sentence counts.
    Returns: (total, eng, fil)
    """
    client = get_supabase_client()
    
    result_fil = client.table(TABLE_FIL).select("sen_id", count="exact").execute()
    fil = result_fil.count if hasattr(result_fil, 'count') else len(result_fil.data)
    
    result_eng = client.table(TABLE_ENG).select("sen_id", count="exact").execute()
    eng = result_eng.count if hasattr(result_eng, 'count') else len(result_eng.data)
    
    return fil + eng, eng, fil


def get_remaining_stats() -> tuple:
    """
    Get remaining (unused) sentence counts.
    Returns: (fil_remaining, eng_remaining)
    """
    client = get_supabase_client()
    
    result_fil = client.table(TABLE_FIL).select("sen_id", count="exact").eq("used", 0).execute()
    fil = result_fil.count if hasattr(result_fil, 'count') else len(result_fil.data)
    
    result_eng = client.table(TABLE_ENG).select("sen_id", count="exact").eq("used", 0).execute()
    eng = result_eng.count if hasattr(result_eng, 'count') else len(result_eng.data)
    
    return fil, eng


def get_categories() -> list:
    """Get all unique categories from both tables."""
    client = get_supabase_client()
    
    result_fil = client.table(TABLE_FIL).select("category").execute()
    result_eng = client.table(TABLE_ENG).select("category").execute()
    
    categories = set()
    for row in result_fil.data:
        if row.get('category'):
            categories.add(row['category'])
    for row in result_eng.data:
        if row.get('category'):
            categories.add(row['category'])
    
    return sorted(list(categories))


def get_category_stats() -> list:
    """
    Get statistics per category.
    Returns: list of dicts with category breakdown
    """
    client = get_supabase_client()
    
    # Get all data
    result_fil = client.table(TABLE_FIL).select("*").execute()
    result_eng = client.table(TABLE_ENG).select("*").execute()
    
    categories = set()
    for row in result_fil.data:
        if row.get('category'):
            categories.add(row['category'])
    for row in result_eng.data:
        if row.get('category'):
            categories.add(row['category'])
    
    stats = []
    for cat in sorted(categories):
        entry = {"category": cat}
        
        fil_data = [r for r in result_fil.data if r.get('category') == cat]
        eng_data = [r for r in result_eng.data if r.get('category') == cat]
        
        entry["fil_total"] = len(fil_data)
        entry["fil_used"] = len([r for r in fil_data if r.get('used') == 1])
        entry["fil_remaining"] = entry["fil_total"] - entry["fil_used"]
        
        entry["eng_total"] = len(eng_data)
        entry["eng_used"] = len([r for r in eng_data if r.get('used') == 1])
        entry["eng_remaining"] = entry["eng_total"] - entry["eng_used"]
        
        stats.append(entry)
    
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
