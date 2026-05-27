"""
Document Text Extractor.
Extracts text from PDF, DOCX, PPTX, TXT files using various libraries.
"""
from typing import List, Dict, Any
from datetime import datetime, timezone
import os
import re

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

try:
    import docx
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

try:
    import pptx
    PPTX_AVAILABLE = True
except ImportError:
    PPTX_AVAILABLE = False

try:
    from markitdown import MarkItDown
    MARKITDOWN_AVAILABLE = True
except ImportError:
    MARKITDOWN_AVAILABLE = False

try:
    import nltk
    NLTK_AVAILABLE = True
    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        nltk.download('punkt', quiet=True)
        nltk.download('punkt_tab', quiet=True)
except ImportError:
    NLTK_AVAILABLE = False


class DocumentExtractor:
    """Document text extractor class."""
    
    MARKITDOWN_EXTENSIONS = {'.pdf', '.docx', '.pptx', '.ppt', '.xlsx', '.xls', '.html', '.htm', '.epub', '.txt'}
    
    def __init__(self):
        self._markitdown = None
        if MARKITDOWN_AVAILABLE:
            try:
                self._markitdown = MarkItDown()
            except Exception:
                self._markitdown = None
    
    def extract_text(self, file_path: str) -> str:
        """Extract text from a document file."""
        ext = os.path.splitext(file_path)[1].lower()
        
        # Try MarkItDown first (supports many formats)
        if MARKITDOWN_AVAILABLE and self._markitdown and ext in self.MARKITDOWN_EXTENSIONS:
            return self._extract_via_markitdown(file_path)
        
        # Fallback to specific extractors
        if ext == '.pdf' and PDFPLUMBER_AVAILABLE:
            return self._extract_pdf(file_path)
        elif ext == '.docx' and DOCX_AVAILABLE:
            return self._extract_docx(file_path)
        elif ext == '.txt':
            return self._extract_txt(file_path)
        
        return ""
    
    def _extract_via_markitdown(self, file_path: str) -> str:
        """Extract text using MarkItDown."""
        try:
            result = self._markitdown.convert(file_path)
            return self._strip_markdown(result.text_content)
        except Exception:
            return ""
    
    def _strip_markdown(self, text: str) -> str:
        """Strip markdown formatting from text."""
        if not text:
            return ""
        text = re.sub(r'!\[.*?\]\(.*?\)', '', text)
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
        text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
        text = re.sub(r'\*{1,3}([^*]+)\*{1,3}', r'\1', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()
    
    def _extract_pdf(self, path: str) -> str:
        """Extract text from PDF using pdfplumber."""
        text = ""
        try:
            with pdfplumber.open(path) as pdf:
                for page in pdf.pages:
                    t = page.extract_text()
                    if t:
                        text += t + "\n"
        except Exception:
            pass
        return text
    
    def _extract_docx(self, path: str) -> str:
        """Extract text from DOCX using python-docx."""
        try:
            doc = docx.Document(path)
            return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        except Exception:
            return ""
    
    def _extract_txt(self, path: str) -> str:
        """Read plain text file."""
        try:
            with open(path, encoding='utf-8', errors='ignore') as f:
                return f.read()
        except Exception:
            return ""
    
    def split_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        if NLTK_AVAILABLE:
            return [s.strip() for s in nltk.sent_tokenize(text) if s.strip()]
        return [s.strip() for s in re.split(r'(?<=[.!?])\s+', text.strip()) if s.strip()]
    
    def extract(self, file_paths: List[str]) -> List[Dict[str, Any]]:
        """
        Extract sentences from multiple files.
        Returns: list of sentence dicts
        """
        results = []
        timestamp = datetime.now(tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
        
        for file_path in file_paths:
            text = self.extract_text(file_path)
            if text:
                for sentence in self.split_sentences(text):
                    if len(sentence.split()) >= 2:
                        results.append({
                            'sentence': sentence,
                            'word_count': len(sentence.split()),
                            'source': os.path.basename(file_path),
                            'source_type': 'Document',
                            'timestamp': timestamp
                        })
        
        return results
