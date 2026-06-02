"""
Data Extractor - Flask routes.
All URL routes for the Universal Data Extractor module.
"""
import os
import threading
from flask import Blueprint, render_template, request, jsonify, session, send_file, current_app, flash, redirect, url_for
from werkzeug.utils import secure_filename

from .reddit_scraper import RedditScraper
from .youtube_comments import YouTubeCommentScraper
from .youtube_subtitles import YouTubeSubtitleExtractor
from .document_extractor import DocumentExtractor
from .output_manager import OutputManager

from auth.routes import login_required
from config import Config
from settings.routes import get_reddit_credentials, get_youtube_api_key

# Use Config.UPLOADS_DIR for consistent upload folder path
UPLOAD_FOLDER = Config.UPLOADS_DIR

extractor_bp = Blueprint('extractor', __name__, template_folder='templates')

# Store extraction results in memory (per session) - thread-safe
_extraction_lock = threading.Lock()
_extraction_results = {}
_result_counter = 0


def get_next_task_id(prefix):
    """Generate unique task ID (thread-safe)."""
    global _result_counter
    with _extraction_lock:
        _result_counter += 1
        return f"{prefix}_{_result_counter}"


@extractor_bp.route('/')
@login_required
def extractor_home():
    """Data Extractor home page."""
    return render_template('extractor/extractor.html')


# ========== REDDIT SCRAPER ==========

@extractor_bp.route('/reddit', methods=['POST'])
@login_required
def extract_reddit():
    """Extract comments from Reddit post."""
    global _result_counter
    data = request.json
    url_or_id = data.get('url_or_id', '')
    
    if not url_or_id:
        return jsonify({'error': 'URL or post ID is required'}), 400
    
    scraper = RedditScraper()
    
    # Get credentials from session (user-specific) or fallback to config
    creds = get_reddit_credentials()
    if creds:
        scraper.authenticate(
            creds['client_id'],
            creds['client_secret'],
            creds.get('user_agent', 'OneAITool/1.0')
        )
    else:
        return jsonify({'error': 'Reddit API credentials not configured. Go to Settings to add them.'}), 400
    
    try:
        post_id = scraper.extract_post_id(url_or_id)
        if not post_id:
            return jsonify({'error': 'Invalid Reddit URL or ID'}), 400
        
        results = scraper.scrape(post_id)
        
        # Store results with unique task ID (thread-safe)
        with _extraction_lock:
            _result_counter += 1
            task_id = f"reddit_{_result_counter}"
            _extraction_results[task_id] = results
            # Also store task_id in session for export
            if 'extraction_task_ids' not in session:
                session['extraction_task_ids'] = []
            session['extraction_task_ids'].append(task_id)
            session.modified = True
        
        return jsonify({
            'success': True,
            'count': len(results),
            'task_id': task_id,
            'data': results  # Return ALL data for display
        })
    except Exception as e:
        print(f"Reddit extraction error: {e}")
        return jsonify({'error': str(e)}), 500


# ========== YOUTUBE COMMENTS ==========

@extractor_bp.route('/youtube/comments', methods=['POST'])
@login_required
def extract_youtube_comments():
    """Extract comments from YouTube video."""
    global _result_counter
    data = request.json
    url = data.get('url', '')
    max_results = data.get('max_results', 100)
    
    if not url:
        return jsonify({'error': 'YouTube URL is required'}), 400
    
    # Get API key from session (user-specific) or fallback to config
    api_key = get_youtube_api_key()
    if not api_key:
        return jsonify({'error': 'YouTube API key not configured. Go to Settings to add it.'}), 400
    
    scraper = YouTubeCommentScraper(api_key)
    
    try:
        video_id = scraper.extract_video_id(url)
        if not video_id:
            return jsonify({'error': 'Invalid YouTube URL'}), 400
        
        results = scraper.scrape(video_id, max_results)
        
        with _extraction_lock:
            _result_counter += 1
            task_id = f"yt_comments_{_result_counter}"
            _extraction_results[task_id] = results
            # Store task_id in session for export
            if 'extraction_task_ids' not in session:
                session['extraction_task_ids'] = []
            session['extraction_task_ids'].append(task_id)
            session.modified = True
        
        return jsonify({
            'success': True,
            'count': len(results),
            'task_id': task_id,
            'data': results  # Return ALL data for display
        })
    except Exception as e:
        print(f"YouTube comments extraction error: {e}")
        return jsonify({'error': str(e)}), 500


# ========== YOUTUBE SUBTITLES ==========

@extractor_bp.route('/youtube/subtitles', methods=['POST'])
@login_required
def extract_youtube_subtitles():
    """Extract subtitles from YouTube video."""
    global _result_counter
    data = request.json
    url = data.get('url', '')
    language = data.get('language', 'en')
    
    if not url:
        return jsonify({'error': 'YouTube URL is required'}), 400
    
    extractor = YouTubeSubtitleExtractor()
    
    try:
        video_id = extractor.extract_video_id(url)
        if not video_id:
            return jsonify({'error': 'Invalid YouTube URL'}), 400
        
        results = extractor.download_and_parse_vtt(video_id, language)
        
        with _extraction_lock:
            _result_counter += 1
            task_id = f"yt_subs_{_result_counter}"
            _extraction_results[task_id] = results
            # Store task_id in session for export
            if 'extraction_task_ids' not in session:
                session['extraction_task_ids'] = []
            session['extraction_task_ids'].append(task_id)
            session.modified = True
        
        return jsonify({
            'success': True,
            'count': len(results),
            'task_id': task_id,
            'data': results  # Return ALL data for display
        })
    except Exception as e:
        print(f"YouTube subtitles extraction error: {e}")
        return jsonify({'error': str(e)}), 500


# ========== DOCUMENT EXTRACTOR ==========

@extractor_bp.route('/document', methods=['POST'])
@login_required
def extract_document():
    """Extract text from uploaded documents."""
    global _result_counter
    if 'files' not in request.files:
        return jsonify({'error': 'No files uploaded'}), 400
    
    files = request.files.getlist('files')
    if not files:
        return jsonify({'error': 'No files selected'}), 400
    
    # Save uploaded files to configured upload folder
    upload_folder = UPLOAD_FOLDER
    os.makedirs(upload_folder, exist_ok=True)
    
    file_paths = []
    for file in files:
        if file.filename:
            filename = secure_filename(file.filename)
            file_path = os.path.join(upload_folder, filename)
            file.save(file_path)
            file_paths.append(file_path)
    
    try:
        extractor = DocumentExtractor()
        results = extractor.extract(file_paths)
        
        # Clean up uploaded files
        for file_path in file_paths:
            try:
                os.remove(file_path)
            except:
                pass
        
        with _extraction_lock:
            _result_counter += 1
            task_id = f"doc_{_result_counter}"
            _extraction_results[task_id] = results
            # Store task_id in session for export
            if 'extraction_task_ids' not in session:
                session['extraction_task_ids'] = []
            session['extraction_task_ids'].append(task_id)
            session.modified = True
        
        return jsonify({
            'success': True,
            'count': len(results),
            'task_id': task_id,
            'data': results  # Return ALL data for display
        })
    except Exception as e:
        print(f"Document extraction error: {e}")
        return jsonify({'error': str(e)}), 500


# ========== EXPORT RESULTS ==========

@extractor_bp.route('/export/csv/<task_id>')
@login_required
def export_csv(task_id):
    """Export extraction results as CSV."""
    results = _extraction_results.get(task_id)
    if not results:
        flash('No results found for this task.', 'error')
        return redirect(url_for('extractor.extractor_home'))
    
    csv_data = OutputManager.save_csv(results)
    
    from io import BytesIO
    output = BytesIO()
    output.write(csv_data.encode('utf-8'))
    output.seek(0)
    
    return send_file(
        output,
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'extraction_{task_id}.csv'
    )


@extractor_bp.route('/export/excel/<task_id>')
@login_required
def export_excel(task_id):
    """Export extraction results as Excel."""
    results = _extraction_results.get(task_id)
    if not results:
        flash('No results found for this task.', 'error')
        return redirect(url_for('extractor.extractor_home'))
    
    output = OutputManager.to_excel_bytes(results)
    if not output:
        flash('Failed to generate Excel file.', 'error')
        return redirect(url_for('extractor.extractor_home'))
    
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'extraction_{task_id}.xlsx'
    )


# ========== GET RESULTS ==========

@extractor_bp.route('/results/<task_id>')
@login_required
def get_results(task_id):
    """Get extraction results for a task."""
    results = _extraction_results.get(task_id)
    if not results:
        return jsonify({'error': 'Task not found'}), 404
    
    return jsonify({
        'success': True,
        'count': len(results),
        'data': results
    })
