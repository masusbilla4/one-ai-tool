"""
YouTube Comment Scraper.
Uses YouTube Data API v3 to extract comments from videos.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import re

import requests


class YouTubeCommentScraper:
    """YouTube comment scraper class."""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key
        self.base_url = "https://www.googleapis.com/youtube/v3/commentThreads"
    
    def set_api_key(self, api_key: str):
        """Set the YouTube API key."""
        self.api_key = api_key
    
    def clean_comment(self, text: str) -> str:
        """Clean comment text by removing special characters."""
        cleaned = re.sub(r'[^\w\s.,?!¡¿:;""\'()-]', '', text, flags=re.UNICODE)
        return re.sub(r'\s+', ' ', cleaned).strip()
    
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
    
    def scrape(self, video_id: str, max_results: int = 100) -> List[Dict[str, Any]]:
        """
        Scrape comments from a YouTube video.
        Returns: list of comment dicts
        """
        if not self.api_key:
            raise ValueError("API key not set")
        
        results = []
        count = 0
        next_page_token = None
        
        while True:
            params = {
                "part": "snippet",
                "videoId": video_id,
                "maxResults": min(max_results - count, 100),
                "textFormat": "plainText",
                "key": self.api_key
            }
            
            if next_page_token:
                params["pageToken"] = next_page_token
            
            response = requests.get(self.base_url, params=params)
            
            if response.status_code != 200:
                break
            
            data = response.json()
            
            for item in data.get("items", []):
                comment = item["snippet"]["topLevelComment"]["snippet"]["textDisplay"]
                cleaned = self.clean_comment(comment)
                timestamp = datetime.now(tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
                
                results.append({
                    'sentence': cleaned,
                    'word_count': len(cleaned.split()),
                    'source': f"https://youtube.com/watch?v={video_id}",
                    'source_type': 'YouTube Comment',
                    'timestamp': timestamp
                })
                
                count += 1
                if count >= max_results:
                    break
            
            if "nextPageToken" in data and count < max_results:
                next_page_token = data["nextPageToken"]
            else:
                break
        
        return results
