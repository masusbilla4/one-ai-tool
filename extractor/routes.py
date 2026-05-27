"""
Data Extractor - Flask routes.
All URL routes for the Universal Data Extractor module.
"""
import os
from flask import Blueprint, render_template, request, jsonify, session, send_file, current_app, flash, redirect, url_for
from werkzeug.utils import secure_filename

from .reddit_scraper import RedditScraper
from .youtube_comments import YouTubeCommentScraper
from .youtube_subtitles import YouTubeSubtitleExtractor
from .document_extractor import DocumentExtractor
from .output_manager import OutputManager

from auth.routes import login_required
from config import Config

extractor_bp = Blueprint('extractor', __name__, template_folder='templates')

# Store extraction results in memory (per session)
_extraction_results = {}


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
    data = request.json
    url_or_id = data.get('url_or_id', '')
    
    if not url_or_id:
        return jsonify({'error': 'URL or post ID is required'}), 400
    
    scraper = RedditScraper()
    
    # Authenticate with credentials from config
    if Config.REDDIT_CLIENT_ID and Config.REDDIT_CLIENT_SECRET:
        scraper.authenticate(
            Config.REDDIT_CLIENT_ID,
            Config.REDDIT_CLIENT_SECRET,
            Config.REDDIT_USER_AGENT
        )
    else:
        return jsonify({'error': 'Reddit API credentials not configured'}), 400
    
    try:
        post_id = scraper.extract_post_id(url_or_id)
        if not post_id:
            return jsonify({'error': 'Invalid Reddit URL or ID'}), 400
        
        results = scraper.scrape(post_id)
        
        # Store results
        task_id = f"reddit_{len(_extraction_results) + 1}"
        _extraction_results[task_id] = results
        
        return jsonify({
            'success': True,
            'count': len(results),
            'task_id': task_id,
            'data': results[:10]  # Return first 10 for preview
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ========== YOUTUBE COMMENTS ==========

@extractor_bp.route('/youtube/comments', methods=['POST'])
@login_required
def extract_youtube_comments():
    """Extract comments from YouTube video."""
    data = request.json
    url = data.get('url', '')
    max_results = data.get('max_results', 100)
    
    if not url:
        return jsonify({'error': 'YouTube URL is required'}), 400
    
    if not Config.YOUTUBE_API_KEY:
        return jsonify({'error': 'YouTube API key not configured'}), 400
    
    scraper = YouTubeCommentScraper(Config.YOUTUBE_API_KEY)
    
    try:
        video_id = scraper.extract_video_id(url)
        if not video_id:
            return jsonify({'error': 'Invalid YouTube URL'}), 400
        
        results = scraper.scrape(video_id, max_results)
        
        task_id = f"yt_comments_{len(_extraction_results) + 1}"
        _extraction_results[task_id] = results
        
        return jsonify({
            'success': True,
            'count': len(results),
            'task_id': task_id,
            'data': results[:10]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ========== YOUTUBE SUBTITLES ==========

@extractor_bp.route('/youtube/subtitles', methods=['POST'])
@login_required
def extract_youtube_subtitles():
    """Extract subtitles from YouTube video."""
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
        
        task_id = f"yt_subs_{len(_extraction_results) + 1}"
        _extraction_results[task_id] = results
        
        return jsonify({
            'success': True,
            'count': len(results),
            'task_id': task_id,
            'data': results[:10]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ========== DOCUMENT EXTRACTOR ==========

@extractor_bp.route('/document', methods=['POST'])
@login_required
def extract_document():
    """Extract text from uploaded documents."""
    if 'files' not in request.files:
        return jsonify({'error': 'No files uploaded'}), 400
    
    files = request.files.getlist('files')
    if not files:
        return jsonify({'error': 'No files selected'}), 400
    
    # Save uploaded files
    upload_folder = current_app.config.get('UPLOAD_FOLDER', '/tmp')
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
        
        task_id = f"doc_{len(_extraction_results) + 1}"
        _extraction_results[task_id] = results
        
        return jsonify({
            'success': True,
            'count': len(results),
            'task_id': task_id,
            'data': results[:10]
        })
    except Exception as e:
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
