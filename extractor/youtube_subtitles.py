"""
YouTube Subtitle Extractor.
Uses yt-dlp to download and parse YouTube subtitles (VTT format).
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import os
import re

try:
    import yt_dlp
    YT_DLP_AVAILABLE = True
except ImportError:
    YT_DLP_AVAILABLE = False

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


class YouTubeSubtitleExtractor:
    """YouTube subtitle extractor class."""
    
    def __init__(self, subtitles_dir: str = None):
        self.subtitles_dir = subtitles_dir
    
    def extract_video_id(self, url: str) -> Optional[str]:
        """Extract video ID from YouTube URL."""
        patterns = [
            r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})',
            r'^([a-zA-Z0-9_-]{11})$'
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    def download_and_parse_vtt(self, video_id: str, language: str = 'en', include_auto: bool = True) -> List[Dict[str, Any]]:
        """
        Download and parse YouTube subtitles.
        Returns: list of sentence dicts
        """
        if not YT_DLP_AVAILABLE:
            return []
        
        if not self.subtitles_dir:
            self.subtitles_dir = os.path.join(os.path.dirname(__file__), '..', 'subtitles')
        os.makedirs(self.subtitles_dir, exist_ok=True)
        
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'writesubtitles': True,
                'writeautomaticsub': include_auto,
                'subtitleslangs': [language],
                'skip_download': True,
                'subtitlesformat': 'vtt',
                'outtmpl': os.path.join(self.subtitles_dir, video_id),
                'no_check_certificate': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([f"https://youtube.com/watch?v={video_id}"])
            
            # Find downloaded VTT file
            vtt_path = None
            for file in os.listdir(self.subtitles_dir):
                if video_id in file and file.endswith('.vtt'):
                    vtt_path = os.path.join(self.subtitles_dir, file)
                    break
            
            if vtt_path:
                return self.parse_vtt_file(vtt_path, video_id)
            return []
            
        except Exception:
            return []
    
    def parse_vtt_file(self, vtt_path: str, video_id: str) -> List[Dict[str, Any]]:
        """Parse VTT subtitle file and extract sentences."""
        results = []
        
        try:
            with open(vtt_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            captions = []
            prev = ""
            
            for line in lines:
                line = line.strip()
                if not line or "-->" in line or line.startswith("WEBVTT") or "align:" in line:
                    continue
                
                # Remove VTT tags
                line = re.sub(r"<.*?>", "", line)
                line = re.sub(r"\s+", " ", line).strip()
                
                if not line:
                    continue
                
                if prev and line.startswith(prev):
                    new_text = line[len(prev):].strip()
                else:
                    new_text = line
                
                if new_text and len(new_text) > 2:
                    captions.append(new_text)
                
                prev = line
            
            # Join all captions and split into sentences
            all_text = " ".join(captions)
            
            if NLTK_AVAILABLE:
                sentences = nltk.sent_tokenize(all_text)
            else:
                sentences = re.split(r'(?<=[.!?])\s+', all_text)
            
            seen = set()
            timestamp = datetime.now(tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
            
            for sentence in sentences:
                sentence = sentence.strip()
                if len(sentence) < 5 or len(sentence.split()) < 2:
                    continue
                
                normalized = sentence.lower()
                if normalized in seen:
                    continue
                seen.add(normalized)
                
                results.append({
                    'sentence': sentence,
                    'word_count': len(sentence.split()),
                    'source': f"https://youtube.com/watch?v={video_id}",
                    'source_type': 'YouTube Subtitle (VTT)',
                    'timestamp': timestamp
                })
        
        except Exception:
            pass
        
        return results
