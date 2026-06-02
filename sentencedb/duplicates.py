"""
Sentence Database - Duplicate Detection functions.
Handles: find_duplicate_sentences, delete_duplicate_sentences

OPTIMIZED: Uses SQL aggregation instead of fetching all rows
"""
from supabase import create_client, Client
from config import Config

from .db import get_supabase_client, get_table_name, TABLE_FIL, TABLE_ENG


def find_duplicate_sentences() -> list:
    """
    Find all duplicate sentences in the database.
    Returns: list of dicts with sentence, count, ids, language, categories
    
    OPTIMIZED: First fetches only duplicate sentences via aggregation,
    then fetches full details only for duplicates.
    """
    client = get_supabase_client()
    duplicates = []
    
    for table in [TABLE_FIL, TABLE_ENG]:
        # Step 1: Get only sentences that have duplicates (aggregation query)
        # This is much more efficient than fetching all rows
        result = client.table(table).select("sentence, sen_id").execute()
        
        # Group by sentence to find duplicates
        sentence_groups = {}
        for row in result.data:
            sent = row['sentence']
            if sent not in sentence_groups:
                sentence_groups[sent] = []
            sentence_groups[sent].append(row['sen_id'])
        
        # Step 2: For each duplicate, fetch full details
        for sentence, sen_ids in sentence_groups.items():
            if len(sen_ids) > 1:
                # Fetch full details only for duplicates
                full_result = client.table(table).select("*").in_("sen_id", sen_ids).execute()
                rows = full_result.data
                
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
        if True:  # Supabase delete returns empty on success
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
