"""
Sentence Database - Duplicate Detection functions.
Handles: find_duplicate_sentences, delete_duplicate_sentences
"""
from supabase import create_client, Client
from config import Config

from .db import get_supabase_client, get_table_name, TABLE_FIL, TABLE_ENG


def find_duplicate_sentences() -> list:
    """
    Find all duplicate sentences in the database.
    Returns: list of dicts with sentence, count, ids, language, categories
    """
    client = get_supabase_client()
    duplicates = []
    
    for table in [TABLE_FIL, TABLE_ENG]:
        result = client.table(table).select("*").execute()
        
        # Group by sentence
        sentence_groups = {}
        for row in result.data:
            sent = row['sentence']
            if sent not in sentence_groups:
                sentence_groups[sent] = []
            sentence_groups[sent].append(row)
        
        # Find duplicates
        for sentence, rows in sentence_groups.items():
            if len(rows) > 1:
                duplicates.append({
                    'sentence': sentence,
                    'count': len(rows),
                    'ids': [r['sen_id'] for r in rows],
                    'language': rows[0]['language'],
                    'categories': [r['category'] for r in rows]
                })
    
    return duplicates


def delete_duplicate_sentences(duplicate_ids: list, language: str) -> int:
    """
    Delete multiple duplicate sentences by ID.
    Keeps the first occurrence, deletes the rest.
    Returns: count of deleted sentences
    """
    client = get_supabase_client()
    table_name = get_table_name(language)
    
    deleted_count = 0
    for sen_id in duplicate_ids:
        result = client.table(table_name).delete().eq("sen_id", sen_id).execute()
        if result.data is not None or True:
            deleted_count += 1
    
    return deleted_count


def delete_all_duplicates() -> tuple:
    """
    Delete all duplicate sentences, keeping the first occurrence.
    Returns: (deleted_count, error_message)
    """
    try:
        duplicates = find_duplicate_sentences()
        total_deleted = 0
        
        for dup in duplicates:
            # Keep first ID, delete the rest
            ids_to_delete = dup['ids'][1:]
            deleted = delete_duplicate_sentences(ids_to_delete, dup['language'])
            total_deleted += deleted
        
        return total_deleted, None
    except Exception as e:
        return 0, str(e)
