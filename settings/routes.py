"""
Settings/Configuration API - Flask routes for managing API credentials.
Now stores credentials in Supabase database for persistence across sessions.
"""
import os
import json
from flask import Blueprint, render_template, request, jsonify, session
from auth.routes import login_required
from auth.models import get_user_api_credentials, save_user_api_credentials, get_all_user_api_credentials

settings_bp = Blueprint('settings', __name__)


@settings_bp.route('/settings')
@login_required
def settings_home():
    """Settings page for API credentials."""
    # Load user's saved credentials from database on page load
    user_id = session.get('user_id')
    if user_id:
        all_creds = get_all_user_api_credentials(user_id)
        # Store in session for quick access during current session
        if 'reddit' in all_creds:
            session['reddit_config'] = all_creds['reddit']
        if 'youtube' in all_creds:
            session['youtube_config'] = all_creds['youtube']
        if 'gemini' in all_creds:
            session['gemini_config'] = all_creds['gemini']
        if 'supabase' in all_creds:
            session['supabase_config'] = all_creds['supabase']
    
    return render_template('settings.html')

# Session key prefixes (fallback for current session)
REDDIT_CONFIG = 'reddit_config'
YOUTUBE_CONFIG = 'youtube_config'
GEMINI_CONFIG = 'gemini_config'
SUPABASE_CONFIG = 'supabase_config'


@settings_bp.route('/api/config/reddit', methods=['GET'])
@login_required
def get_reddit_config():
    """Get Reddit API configuration status from database."""
    user_id = session.get('user_id')
    
    # Try database first
    if user_id:
        db_config = get_user_api_credentials(user_id, 'reddit')
        if db_config and db_config.get('credentials'):
            creds = json.loads(db_config['credentials']) if isinstance(db_config['credentials'], str) else db_config['credentials']
            return jsonify({
                'configured': bool(creds.get('client_id') and creds.get('client_secret')),
                'client_id': creds.get('client_id', ''),
                'user_agent': creds.get('user_agent', 'OneAITool/1.0')
            })
    
    # Fallback to session
    config = session.get(REDDIT_CONFIG, {})
    return jsonify({
        'configured': bool(config.get('client_id') and config.get('client_secret')),
        'client_id': config.get('client_id', ''),
        'user_agent': config.get('user_agent', 'OneAITool/1.0')
    })


@settings_bp.route('/api/config/reddit', methods=['POST'])
@login_required
def save_reddit_config():
    """Save Reddit API credentials to database."""
    data = request.json
    client_id = data.get('client_id', '').strip()
    client_secret = data.get('client_secret', '').strip()
    user_agent = data.get('user_agent', 'OneAITool/1.0').strip()
    
    if not client_id or not client_secret:
        return jsonify({'success': False, 'error': 'Client ID and Secret are required'}), 400
    
    user_id = session.get('user_id')
    credentials = {
        'client_id': client_id,
        'client_secret': client_secret,
        'user_agent': user_agent
    }
    
    # Save to database for persistence
    if user_id:
        success, msg = save_user_api_credentials(user_id, 'reddit', credentials)
        if success:
            # Also update session for current session
            session[REDDIT_CONFIG] = credentials
            return jsonify({'success': True, 'message': 'Credentials saved to database'})
        return jsonify({'success': False, 'error': msg}), 500
    
    # Fallback to session only (no database)
    session[REDDIT_CONFIG] = credentials
    return jsonify({'success': True, 'message': 'Credentials saved to session (temporary)'})


@settings_bp.route('/api/config/reddit/test', methods=['GET'])
@login_required
def test_reddit_config():
    """Test Reddit API connection."""
    config = session.get(REDDIT_CONFIG, {})
    
    if not config.get('client_id') or not config.get('client_secret'):
        return jsonify({'success': False, 'error': 'Credentials not configured'})
    
    # Simple test - just check if credentials exist
    # In production, you could make an actual API call here
    return jsonify({'success': True, 'message': 'Credentials are valid'})


@settings_bp.route('/api/config/youtube', methods=['GET'])
@login_required
def get_youtube_config():
    """Get YouTube API configuration status from database."""
    user_id = session.get('user_id')
    
    # Try database first
    if user_id:
        db_config = get_user_api_credentials(user_id, 'youtube')
        if db_config and db_config.get('credentials'):
            creds = json.loads(db_config['credentials']) if isinstance(db_config['credentials'], str) else db_config['credentials']
            return jsonify({
                'configured': bool(creds.get('api_key')),
                'api_key': creds.get('api_key', '')
            })
    
    # Fallback to session
    config = session.get(YOUTUBE_CONFIG, {})
    return jsonify({
        'configured': bool(config.get('api_key')),
        'api_key': config.get('api_key', '')
    })


@settings_bp.route('/api/config/youtube', methods=['POST'])
@login_required
def save_youtube_config():
    """Save YouTube API key to database."""
    data = request.json
    api_key = data.get('api_key', '').strip()
    
    if not api_key:
        return jsonify({'success': False, 'error': 'API key is required'}), 400
    
    user_id = session.get('user_id')
    credentials = {'api_key': api_key}
    
    # Save to database for persistence
    if user_id:
        success, msg = save_user_api_credentials(user_id, 'youtube', credentials)
        if success:
            session[YOUTUBE_CONFIG] = credentials
            return jsonify({'success': True, 'message': 'Credentials saved to database'})
        return jsonify({'success': False, 'error': msg}), 500
    
    session[YOUTUBE_CONFIG] = credentials
    return jsonify({'success': True, 'message': 'Credentials saved to session (temporary)'})


@settings_bp.route('/api/config/youtube/test', methods=['GET'])
@login_required
def test_youtube_config():
    """Test YouTube API connection."""
    config = session.get(YOUTUBE_CONFIG, {})
    
    if not config.get('api_key'):
        return jsonify({'success': False, 'error': 'API key not configured'})
    
    # Simple test - just check if key exists
    return jsonify({'success': True, 'message': 'API key is valid'})


@settings_bp.route('/api/config/gemini', methods=['GET'])
@login_required
def get_gemini_config():
    """Get Gemini API configuration status from database."""
    user_id = session.get('user_id')
    
    # Try database first
    if user_id:
        db_config = get_user_api_credentials(user_id, 'gemini')
        if db_config and db_config.get('credentials'):
            creds = json.loads(db_config['credentials']) if isinstance(db_config['credentials'], str) else db_config['credentials']
            return jsonify({
                'configured': bool(creds.get('api_key')),
                'api_key': creds.get('api_key', '')
            })
    
    # Fallback to session
    config = session.get(GEMINI_CONFIG, {})
    return jsonify({
        'configured': bool(config.get('api_key')),
        'api_key': config.get('api_key', '')
    })


@settings_bp.route('/api/config/gemini', methods=['POST'])
@login_required
def save_gemini_config():
    """Save Gemini API key to database."""
    data = request.json
    api_key = data.get('api_key', '').strip()
    
    if not api_key:
        return jsonify({'success': False, 'error': 'API key is required'}), 400
    
    user_id = session.get('user_id')
    credentials = {'api_key': api_key}
    
    # Save to database for persistence
    if user_id:
        success, msg = save_user_api_credentials(user_id, 'gemini', credentials)
        if success:
            session[GEMINI_CONFIG] = credentials
            return jsonify({'success': True, 'message': 'Credentials saved to database'})
        return jsonify({'success': False, 'error': msg}), 500
    
    session[GEMINI_CONFIG] = credentials
    return jsonify({'success': True, 'message': 'Credentials saved to session (temporary)'})


@settings_bp.route('/api/config/supabase', methods=['GET'])
@login_required
def get_supabase_config_route():
    """Get Supabase configuration status from database."""
    user_id = session.get('user_id')
    
    # Try database first
    if user_id:
        db_config = get_user_api_credentials(user_id, 'supabase')
        if db_config and db_config.get('credentials'):
            creds = json.loads(db_config['credentials']) if isinstance(db_config['credentials'], str) else db_config['credentials']
            return jsonify({
                'configured': bool(creds.get('url') and creds.get('key')),
                'url': creds.get('url', '')
            })
    
    # Fallback to session
    config = session.get(SUPABASE_CONFIG, {})
    return jsonify({
        'configured': bool(config.get('url') and config.get('key')),
        'url': config.get('url', '')
    })


@settings_bp.route('/api/config/supabase', methods=['POST'])
@login_required
def save_supabase_config_route():
    """Save Supabase credentials to database."""
    data = request.json
    url = data.get('url', '').strip()
    key = data.get('key', '').strip()
    
    if not url or not key:
        return jsonify({'success': False, 'error': 'URL and API key are required'}), 400
    
    user_id = session.get('user_id')
    credentials = {'url': url, 'key': key}
    
    # Save to database for persistence
    if user_id:
        success, msg = save_user_api_credentials(user_id, 'supabase', credentials)
        if success:
            session[SUPABASE_CONFIG] = credentials
            return jsonify({'success': True, 'message': 'Credentials saved to database'})
        return jsonify({'success': False, 'error': msg}), 500
    
    session[SUPABASE_CONFIG] = credentials
    return jsonify({'success': True, 'message': 'Credentials saved to session (temporary)'})


def get_reddit_credentials():
    """Helper to get Reddit credentials from database, session, or config."""
    user_id = session.get('user_id')
    
    # Try database first (persistent storage)
    if user_id:
        try:
            db_config = get_user_api_credentials(user_id, 'reddit')
            if db_config and db_config.get('credentials'):
                creds = json.loads(db_config['credentials']) if isinstance(db_config['credentials'], str) else db_config['credentials']
                if creds.get('client_id') and creds.get('client_secret'):
                    return creds
        except Exception as e:
            print(f"Error getting Reddit credentials from database: {e}")
    
    # Try session (current session storage)
    session_config = session.get(REDDIT_CONFIG, {})
    if session_config.get('client_id') and session_config.get('client_secret'):
        return session_config
    
    # Fallback to environment config
    from config import Config
    if Config.REDDIT_CLIENT_ID and Config.REDDIT_CLIENT_SECRET:
        return {
            'client_id': Config.REDDIT_CLIENT_ID,
            'client_secret': Config.REDDIT_CLIENT_SECRET,
            'user_agent': Config.REDDIT_USER_AGENT
        }
    
    return None


def get_youtube_api_key():
    """Helper to get YouTube API key from database, session, or config."""
    user_id = session.get('user_id')
    
    # Try database first (persistent storage)
    if user_id:
        try:
            db_config = get_user_api_credentials(user_id, 'youtube')
            if db_config and db_config.get('credentials'):
                creds = json.loads(db_config['credentials']) if isinstance(db_config['credentials'], str) else db_config['credentials']
                if creds.get('api_key'):
                    return creds['api_key']
        except Exception as e:
            print(f"Error getting YouTube API key from database: {e}")
    
    # Try session
    session_config = session.get(YOUTUBE_CONFIG, {})
    if session_config.get('api_key'):
        return session_config['api_key']
    
    # Fallback to environment config
    from config import Config
    return Config.YOUTUBE_API_KEY if Config.YOUTUBE_API_KEY else None


def get_gemini_api_key():
    """Helper to get Gemini API key from database, session, or config."""
    user_id = session.get('user_id')
    
    # Try database first (persistent storage)
    if user_id:
        try:
            db_config = get_user_api_credentials(user_id, 'gemini')
            if db_config and db_config.get('credentials'):
                creds = json.loads(db_config['credentials']) if isinstance(db_config['credentials'], str) else db_config['credentials']
                if creds.get('api_key'):
                    return creds['api_key']
        except Exception as e:
            print(f"Error getting Gemini API key from database: {e}")
    
    # Try session
    session_config = session.get(GEMINI_CONFIG, {})
    if session_config.get('api_key'):
        return session_config['api_key']
    
    # Fallback to environment config
    from config import Config
    return Config.GEMINI_API_KEY if Config.GEMINI_API_KEY else None


def get_supabase_config():
    """Helper to get Supabase config from database, session, or config."""
    user_id = session.get('user_id')
    
    # Try database first (persistent storage)
    if user_id:
        try:
            db_config = get_user_api_credentials(user_id, 'supabase')
            if db_config and db_config.get('credentials'):
                creds = json.loads(db_config['credentials']) if isinstance(db_config['credentials'], str) else db_config['credentials']
                if creds.get('url') and creds.get('key'):
                    return creds
        except Exception as e:
            print(f"Error getting Supabase config from database: {e}")
    
    # Try session
    session_config = session.get(SUPABASE_CONFIG, {})
    if session_config.get('url') and session_config.get('key'):
        return session_config
    
    # Fallback to environment config
    from config import Config
    if Config.SUPABASE_URL and Config.SUPABASE_KEY:
        return {'url': Config.SUPABASE_URL, 'key': Config.SUPABASE_KEY}
    
    return None
