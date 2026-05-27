"""
One AI Tool - Unified Flask Web Application
Main entry point that registers all blueprints.
"""
import os
from flask import Flask, render_template, redirect, url_for, session

from config import Config

# Import blueprints
from auth.routes import auth_bp
from sentencedb.routes import sentencedb_bp
from extractor.routes import extractor_bp
from asr.routes import asr_bp
from settings.routes import settings_bp


def create_app(config_class=Config):
    """Application factory for creating Flask app."""
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(sentencedb_bp, url_prefix='/sentencedb')
    app.register_blueprint(extractor_bp, url_prefix='/extractor')
    app.register_blueprint(asr_bp, url_prefix='/asr')
    app.register_blueprint(settings_bp)
    
    # Main routes
    @app.route('/')
    def index():
        """Landing page - redirect to dashboard if logged in."""
        if session.get('user_id'):
            return redirect(url_for('main_dashboard'))
        return render_template('index.html')
    
    @app.route('/dashboard')
    def main_dashboard():
        """Unified dashboard with all tools in one page (tabs)."""
        if not session.get('user_id'):
            return redirect(url_for('auth.login'))
        return render_template('main_dashboard.html')
    
    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('error.html', error_code=404, error_message='Page not found'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return render_template('error.html', error_code=500, error_message='Internal server error'), 500
    
    return app


if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)
