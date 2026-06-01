"""
Reddit Comment Scraper.
Uses PRAW (Python Reddit API Wrapper) to extract comments from Reddit posts.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

try:
    import praw
    PRAW_AVAILABLE = True
except ImportError:
    PRAW_AVAILABLE = False


class RedditScraper:
    """Reddit comment scraper class."""
    
    def __init__(self):
        self.reddit = None
    
    def authenticate(self, client_id: str, client_secret: str, user_agent: str) -> bool:
        """
        Authenticate with Reddit API.
        Returns: True if successful
        """
        if not PRAW_AVAILABLE:
            return False
        
        try:
            self.reddit = praw.Reddit(
                client_id=client_id,
                client_secret=client_secret,
                user_agent=user_agent
            )
            self.reddit.read_only = True
            # Test connection
            _ = self.reddit.user.me()
            return True
        except Exception:
            return False
    
    def extract_post_id(self, url_or_id: str) -> Optional[str]:
        """Extract post ID from Reddit URL or return the ID if already provided."""
        from urllib.parse import urlparse
        
        url_or_id = url_or_id.strip()
        
        if url_or_id.startswith("http"):
            path_parts = urlparse(url_or_id).path.split('/')
            try:
                idx = path_parts.index('comments')
                return path_parts[idx + 1]
            except (ValueError, IndexError):
                return None
        
        return url_or_id
    
    def scrape(self, post_id: str, max_comments: int = 500) -> List[Dict[str, Any]]:
        """
        Scrape comments from a Reddit post.
        Returns: list of comment dicts with sentence, word_count, source, source_type, timestamp
        
        Args:
            post_id: Reddit post ID
            max_comments: Maximum number of comments to fetch (default 500 to prevent OOM)
        """
        if not self.reddit:
            raise ValueError("Not authenticated with Reddit")
        
        results = []
        
        try:
            submission = self.reddit.submission(id=post_id)
            
            # Limit replace_more to prevent memory exhaustion on large posts
            # limit=50 means fetch up to 50 "more comments" objects
            submission.comments.replace_more(limit=50)
            
            # Get comments with limit to prevent OOM
            comments = []
            for comment in submission.comments.list():
                if len(comments) >= max_comments:
                    break
                if hasattr(comment, 'body'):
                    text = comment.body.replace('\n', ' ').strip()
                    if text:
                        timestamp = datetime.fromtimestamp(comment.created_utc, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
                        comments.append({
                            'sentence': text,
                            'word_count': len(text.split()),
                            'source': f"https://reddit.com{comment.permalink}",
                            'source_type': 'Reddit',
                            'timestamp': timestamp
                        })
            
            results = comments[:max_comments]
            
        except MemoryError:
            # Handle out of memory - return what we have
            pass
        except Exception as e:
            # Log error but don't crash
            error_msg = str(e)
            if "rate limit" in error_msg.lower() or "sleep" in error_msg.lower():
                raise ValueError("Reddit API rate limit reached. Please wait a moment and try again.")
            elif "timeout" in error_msg.lower():
                raise ValueError("Request timed out. The post may have too many comments.")
            else:
                raise ValueError(f"Error scraping Reddit: {error_msg}")
        
        return results
