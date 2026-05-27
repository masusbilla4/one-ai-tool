"""
Sentence Database - Import and Export functions.
Handles: import_from_csv, import_from_sqlite, export_to_csv
"""
import csv
import sqlite3
import tempfile
import os
from io import StringIO
from supabase import create_client, Client
from config import Config

from .db import get_supabase_client, get_table_name, TABLE_FIL, TABLE_ENG, insert_sentence, check_sentence_exists


def import_from_csv_to_db(csv_content: str, skip_duplicates: bool = True) -> tuple:
    """
    Import sentences from CSV content.
    CSV format: sentence,category,language
    Returns: (imported_count, skipped_count, error_message)
    """
    try:
        lines = csv_content.strip().split('\n')
        reader = csv.reader(lines)
        header = next(reader, None)
        
        if not header:
            return 0, 0, "Empty CSV file"
        
        imported = 0
        skipped = 0
        
        for row in reader:
            if not row or not row[0].strip():
                continue
            
            sentence = row[0].strip() if len(row) > 0 else ""
            category = row[1].strip() if len(row) > 1 else "imported"
            language = row[2].strip().lower() if len(row) > 2 else "fil"
            
            # Normalize language
            if language in ["en", "eng", "english"]:
                language = "en"
            elif language in ["fil", "filipino", "tagalog"]:
                language = "fil"
            else:
                language = "fil"
            
            if not sentence:
                continue
            
            # Check for duplicates
            if skip_duplicates:
                exists, _, _, _ = check_sentence_exists(sentence, language)
                if exists:
                    skipped += 1
                    continue
            
            insert_sentence(sentence, category, language)
            imported += 1
        
        return imported, skipped, None
    
    except Exception as e:
        return 0, 0, str(e)


def import_from_sqlite_file(uploaded_file_path: str) -> tuple:
    """
    Import sentences from an uploaded SQLite file.
    Returns: (imported_count, skipped_count, error_message)
    """
    try:
        conn = sqlite3.connect(uploaded_file_path)
        cursor = conn.cursor()
        
        imported = 0
        skipped = 0
        
        for table in [TABLE_FIL, TABLE_ENG]:
            try:
                cursor.execute(f"SELECT sentence, category, language FROM {table}")
                for row in cursor.fetchall():
                    sentence, category, language = row
                    
                    exists, _, _, _ = check_sentence_exists(sentence, language)
                    if exists:
                        skipped += 1
                        continue
                    
                    insert_sentence(sentence, category or "imported", language or "fil")
                    imported += 1
            except sqlite3.OperationalError:
                pass  # Table might not exist
        
        conn.close()
        os.remove(uploaded_file_path)
        
        return imported, skipped, None
    
    except Exception as e:
        return 0, 0, str(e)


def export_to_csv_string() -> str:
    """
    Export all sentences to CSV string.
    Returns: CSV content as string
    """
    client = get_supabase_client()
    csv_buffer = StringIO()
    writer = csv.writer(csv_buffer)
    writer.writerow(["sentence", "category", "language", "word_count", "used"])
    
    for table in [TABLE_FIL, TABLE_ENG]:
        result = client.table(table).select("*").execute()
        for row in result.data:
            writer.writerow([
                row['sentence'],
                row['category'],
                row['language'],
                row.get('word_count', 0),
                row.get('used', 0)
            ])
    
    return csv_buffer.getvalue()


def export_to_csv_file(output_path: str) -> bool:
    """
    Export all sentences to a CSV file.
    Returns: True if success
    """
    try:
        csv_data = export_to_csv_string()
        with open(output_path, 'w', encoding='utf-8', newline='') as f:
            f.write(csv_data)
        return True
    except Exception:
        return False
