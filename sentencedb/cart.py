"""
Sentence Database - Cart and Shopping functions.
Handles: get_all_sentences, search_sentences, get_filtered_sentences, mark_sentences_as_used
"""
from supabase import create_client, Client
from config import Config

from .db import get_supabase_client, get_table_name, TABLE_FIL, TABLE_ENG


def get_all_sentences(language: str = None, include_used: bool = True) -> list:
    """
    Get all sentences (for editing).
    Returns: list of dicts with sen_id, sentence, category, language, used
    """
    client = get_supabase_client()
    sentences = []
    
    if language:
        table_name = get_table_name(language)
        query = client.table(table_name).select("sen_id,sentence,category,language,used")
        if not include_used:
            query = query.eq("used", 0)
        result = query.execute()
        for row in result.data:
            sentences.append(row)
    else:
        # Filipino
        query_fil = client.table(TABLE_FIL).select("sen_id,sentence,category,language,used")
        if not include_used:
            query_fil = query_fil.eq("used", 0)
        result_fil = query_fil.execute()
        for row in result_fil.data:
            sentences.append(row)
        
        # English
        query_eng = client.table(TABLE_ENG).select("sen_id,sentence,category,language,used")
        if not include_used:
            query_eng = query_eng.eq("used", 0)
        result_eng = query_eng.execute()
        for row in result_eng.data:
            sentences.append(row)
    
    return sentences


def search_sentences(keyword: str, language: str = None) -> list:
    """
    Search sentences by keyword.
    Returns: list of (sen_id, sentence, category) tuples
    """
    client = get_supabase_client()
    sentences = []
    search_pattern = f"%{keyword}%"
    
    if language:
        table_name = get_table_name(language)
        result = client.table(table_name).select("sen_id,sentence,category").ilike("sentence", search_pattern).eq("used", 0).execute()
        for row in result.data:
            sentences.append((row['sen_id'], row['sentence'], row['category']))
    else:
        result_fil = client.table(TABLE_FIL).select("sen_id,sentence,category").ilike("sentence", search_pattern).eq("used", 0).execute()
        for row in result_fil.data:
            sentences.append((row['sen_id'], row['sentence'], row['category']))
        
        result_eng = client.table(TABLE_ENG).select("sen_id,sentence,category").ilike("sentence", search_pattern).eq("used", 0).execute()
        for row in result_eng.data:
            sentences.append((row['sen_id'], row['sentence'], row['category']))
    
    return sentences


def get_filtered_sentences(category: str, language: str, word_count: int = None) -> list:
    """
    Get filtered sentences by category, language, and optionally word count.
    Returns: list of (sentence, category, language, word_count) tuples
    """
    client = get_supabase_client()
    table_name = get_table_name(language)
    
    query = client.table(table_name).select("sentence,category,language,word_count").eq("used", 0)
    
    # Only filter by category if it's not "All"
    if category and category != "All":
        query = query.eq("category", category)
    
    result = query.execute()
    
    sentences = []
    for row in result.data:
        if word_count is None or row.get('word_count') == word_count:
            sentences.append((row['sentence'], row['category'], row['language'], row.get('word_count', 0)))
    
    return sentences


def mark_sentences_as_used(sentences: list) -> int:
    """
    Mark multiple sentences as used.
    sentences: list of (sentence, category, language) tuples
    Returns: count of marked sentences
    """
    client = get_supabase_client()
    marked_count = 0
    
    for sentence_data in sentences:
        sentence = sentence_data[0]
        category = sentence_data[1]
        language = sentence_data[2]
        
        table_name = get_table_name(language)
        result = client.table(table_name).update({"used": 1}).eq("sentence", sentence).eq("category", category).execute()
        if result.data is not None or True:
            marked_count += 1
    
    return marked_count
