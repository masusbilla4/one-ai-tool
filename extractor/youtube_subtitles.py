"""
YouTube Subtitle Extractor.
Uses yt-dlp to download and parse YouTube subtitles (VTT format).
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import os
import re
import json

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
    
    def get_available_subtitles(self, video_id: str) -> Dict[str, Any]:
        """
        Get list of available subtitles (manual and auto-generated) for a video.
        Returns: dict with 'manual' and 'auto' lists of language codes
        """
        if not YT_DLP_AVAILABLE:
            return {'manual': [], 'auto': [], 'error': 'yt-dlp not available'}
        
        # Check for cookies file
        cookies_path = os.environ.get('YOUTUBE_COOKIES_PATH', '')
        cookies_data = os.environ.get('YOUTUBE_COOKIES', '')
        
        ydl_opts = {
            'quiet': False,  # Show more output for debugging
            'no_warnings': False,
            'skip_download': True,
            'no_check_certificate': True,
            'extract_flat': False,
            'ignoreerrors': True,
            # Use multiple player clients to bypass bot detection
            'extractor_args': {
                'youtube': {
                    'player_client': ['web', 'web_embedded', 'android', 'ios'],
                    'player_skip': ['webpage'],
                }
            },
        }
        
        # Add cookies if available
        if cookies_path and os.path.exists(cookies_path):
            ydl_opts['cookies'] = cookies_path
            print(f"Using cookies from file: {cookies_path}")
        elif cookies_data:
            # Write cookies to temp file in /tmp directory (writable on Render)
            temp_cookies = '/tmp/youtube_cookies.txt'
            try:
                with open(temp_cookies, 'w') as f:
                    f.write(cookies_data)
                ydl_opts['cookies'] = temp_cookies
                print(f"Using cookies from environment variable, written to: {temp_cookies}")
                print(f"Cookies file size: {len(cookies_data)} bytes")
                # Verify first few lines
                first_lines = cookies_data.split('\n')[:3]
                print(f"Cookies header: {first_lines}")
            except Exception as e:
                print(f"Failed to write temp cookies: {e}")
                ydl_opts['cookies'] = None
        else:
            print("No cookies configured")
        
        print(f"yt-dlp options: {ydl_opts}")
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                print(f"Fetching subtitle info for video: {video_id}")
                info = ydl.extract_info(f"https://youtube.com/watch?v={video_id}", download=False)
                
                result = {'manual': [], 'auto': [], 'error': None}
                
                if info is None:
                    print(f"No info returned for video {video_id}")
                    result['error'] = 'No data returned from YouTube - cookies may be expired'
                    return result
                
                # Get manual subtitles (subtitles key)
                if 'subtitles' in info and info['subtitles']:
                    result['manual'] = [lang for lang in info['subtitles'].keys() if info['subtitles'][lang]]
                    print(f"Manual subtitles found: {result['manual']}")
                
                # Get auto-generated subtitles (automatic_captions key)
                if 'automatic_captions' in info and info['automatic_captions']:
                    result['auto'] = [lang for lang in info['automatic_captions'].keys() if info['automatic_captions'][lang]]
                    print(f"Auto subtitles found: {result['auto']}")
                
                if not result['manual'] and not result['auto']:
                    print(f"No subtitles found for video {video_id}")
                    print(f"Available info keys: {list(info.keys()) if info else 'None'}")
                    result['error'] = 'No subtitles available for this video'
                
                return result
                
        except Exception as e:
            print(f"Error getting subtitles: {e}")
            return {'manual': [], 'auto': [], 'error': str(e)}
    
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
                'writeautomaticsub': True,  # Always enable auto subtitles as fallback
                'subtitleslangs': [language],
                'skip_download': True,
                'subtitlesformat': 'vtt',
                'outtmpl': os.path.join(self.subtitles_dir, video_id),
                'no_check_certificate': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([f"https://youtube.com/watch?v={video_id}"])
            
            # Find downloaded VTT file - try multiple patterns
            vtt_path = None
            priority_patterns = [
                f"{video_id}.{language}.vtt",  # Exact language match
                f"{video_id}.{language.split('-')[0]}.vtt",  # Language code without region
            ]
            
            # First try exact matches
            for pattern in priority_patterns:
                potential_path = os.path.join(self.subtitles_dir, pattern)
                if os.path.exists(potential_path):
                    vtt_path = potential_path
                    break
            
            # If no exact match, find any VTT file for this video
            if not vtt_path:
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
