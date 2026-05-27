# One AI Tool

A unified Flask web application combining **Sentence Database**, **Universal Data Extractor**, and **ASR Aligner** tools with Supabase backend.

## Features

### 🔹 Sentence Database
- Add, edit, search, and manage Filipino and English sentences
- Supabase cloud database integration
- Category management and filtering
- Import/Export CSV functionality
- Duplicate detection and removal
- Shopping cart for sentence selection

### 🔹 Universal Data Extractor
- **Reddit**: Extract comments from Reddit posts (requires PRAW API credentials)
- **YouTube Comments**: Extract comments from YouTube videos (requires YouTube Data API)
- **YouTube Subtitles**: Download and parse YouTube VTT subtitles
- **Document Extractor**: Extract text from PDF, DOCX, PPTX, TXT files
- Export results to CSV or Excel

### 🔹 ASR Aligner
- Compare ASR transcriptions with reference text
- Word-level alignment using Hirschberg algorithm
- WER (Word Error Rate) calculation
- Translation alignment
- Export alignment results to CSV/Excel

## Installation

### Prerequisites
- Python 3.8 or higher
- Supabase account (free tier available at https://supabase.com)
- (Optional) Reddit API credentials for Reddit extraction
- (Optional) YouTube Data API key for YouTube extraction

### 1. Clone/Setup

```bash
cd "One AI Tool"
```

### 2. Create Virtual Environment

```bash
python -m venv venv
venv\Scripts\activate  # Windows
# or
source venv/bin/activate  # Linux/Mac
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env` with your settings:

```env
# Flask Settings
SECRET_KEY=your-secret-key-here
FLASK_ENV=development

# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-or-service-role-key

# Reddit API (optional - for Reddit extraction)
REDDIT_CLIENT_ID=your-reddit-client-id
REDDIT_CLIENT_SECRET=your-reddit-client-secret
REDDIT_USER_AGENT=your-app-name

# YouTube API (optional - for YouTube extraction)
YOUTUBE_API_KEY=your-youtube-api-key
```

### 5. Set Up Supabase Database

Go to your Supabase project and create the following tables:

#### Table 1: `app_users` (for authentication)
```sql
CREATE TABLE app_users (
    id BIGSERIAL PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    email TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    is_admin BOOLEAN DEFAULT FALSE,
    password_updated_at TIMESTAMP
);
```

#### Table 2: `fil_sentences` (Filipino sentences)
```sql
CREATE TABLE fil_sentences (
    sen_id TEXT PRIMARY KEY,
    sentence TEXT NOT NULL,
    category TEXT,
    language TEXT DEFAULT 'fil',
    used INTEGER DEFAULT 0,
    char_count INTEGER,
    word_count INTEGER,
    sentence_count INTEGER
);
```

#### Table 3: `eng_sentences` (English sentences)
```sql
CREATE TABLE eng_sentences (
    sen_id TEXT PRIMARY KEY,
    sentence TEXT NOT NULL,
    category TEXT,
    language TEXT DEFAULT 'en',
    used INTEGER DEFAULT 0,
    char_count INTEGER,
    word_count INTEGER,
    sentence_count INTEGER
);
```

### 6. Run the Application

```bash
python app.py
```

Or with Flask directly:

```bash
flask run
```

Open your browser and navigate to: **http://127.0.0.1:5000**

## Usage

### First-Time Setup

1. Navigate to the home page
2. Click "Register" to create your first admin account
3. Login with your credentials
4. Start using the tools!

### Sentence Database

1. **Dashboard**: View statistics and quick actions
2. **Add Sentence**: Add new sentences with category and language
3. **Edit**: Search and edit existing sentences
4. **Shop**: Select random sentences by category/language
5. **Import/Export**: Import from CSV/SQLite or export all data
6. **Duplicates**: Find and remove duplicate sentences

### Universal Extractor

1. **Reddit**: Paste Reddit post URL, extract comments
2. **YouTube Comments**: Paste YouTube URL, extract video comments
3. **YouTube Subtitles**: Download and parse video subtitles
4. **Documents**: Upload PDF/DOCX/TXT files for text extraction
5. **Export**: Download results as CSV or Excel

### ASR Aligner

1. Paste reference text (true text)
2. Paste ASR transcription
3. Click "Align" to compare
4. View word-level differences and WER
5. Optionally align translations
6. Export results

## Project Structure

```
One AI Tool/
├── app.py                 # Main Flask application
├── config.py              # Configuration settings
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables (create from .env.example)
├── .env.example           # Example environment file
├── .gitignore             # Git ignore file
├── auth/                  # Authentication module
│   ├── __init__.py
│   ├── models.py          # User authentication functions
│   └── routes.py          # Login/Register routes
├── sentencedb/            # Sentence Database module
│   ├── __init__.py
│   ├── db.py              # Supabase CRUD operations
│   ├── stats.py           # Statistics functions
│   ├── cart.py            # Shopping cart functions
│   ├── import_export.py   # Import/Export functions
│   ├── duplicates.py      # Duplicate detection
│   └── routes.py          # Web routes
├── extractor/             # Data Extractor module
│   ├── __init__.py
│   ├── reddit_scraper.py  # Reddit extraction
│   ├── youtube_comments.py # YouTube comments
│   ├── youtube_subtitles.py # YouTube subtitles
│   ├── document_extractor.py # Document text extraction
│   ├── output_manager.py  # CSV/Excel export
│   └── routes.py          # Web routes
├── asr/                   # ASR Aligner module
│   ├── __init__.py
│   ├── alignment_engine.py # Core alignment algorithm
│   └── routes.py          # Web routes
└── templates/             # HTML templates
    ├── base.html          # Base template
    ├── index.html         # Home page
    ├── login.html         # Login page
    ├── register.html      # Registration page
    ├── users.html         # User management (admin)
    ├── sentencedb/        # Sentence DB templates
    ├── extractor/         # Extractor templates
    └── asr/               # ASR templates
```

## API Endpoints

### Authentication
- `GET/POST /login` - User login
- `GET/POST /register` - User registration
- `GET /logout` - User logout
- `GET /users` - User management (admin only)

### Sentence Database
- `GET /sentencedb/` - Dashboard
- `GET/POST /sentencedb/add` - Add sentence
- `GET/POST /sentencedb/edit` - Edit sentences
- `GET/POST /sentencedb/shop` - Shopping cart
- `GET/POST /sentencedb/import` - Import/Export
- `GET /sentencedb/duplicates` - Find duplicates
- `GET /sentencedb/stats` - API: Get statistics

### Data Extractor
- `GET /extractor/` - Extractor home
- `POST /extractor/reddit` - Extract Reddit comments
- `POST /extractor/youtube/comments` - Extract YouTube comments
- `POST /extractor/youtube/subtitles` - Extract YouTube subtitles
- `POST /extractor/document` - Extract from documents
- `GET /extractor/export/csv/<task_id>` - Export as CSV
- `GET /extractor/export/excel/<task_id>` - Export as Excel

### ASR Aligner
- `GET /asr/` - ASR home
- `POST /asr/align` - Run alignment
- `POST /asr/align/translation` - Align translation
- `GET /asr/results/<task_id>` - Get results
- `GET /asr/export/csv/<task_id>` - Export as CSV
- `GET /asr/export/excel/<task_id>` - Export as Excel

## Deployment

### Deploy to Render/Heroku/Railway

1. Create a new web service
2. Set build command: `pip install -r requirements.txt`
3. Set start command: `gunicorn app:app`
4. Add environment variables from `.env`

### Production Considerations

- Set `FLASK_ENV=production`
- Use a strong `SECRET_KEY`
- Enable HTTPS
- Use Supabase service role key for production
- Consider adding rate limiting
- Set up proper logging

## Troubleshooting

### Common Issues

**"Module not found" errors:**
```bash
pip install -r requirements.txt
```

**"Supabase connection failed":**
- Check your `SUPABASE_URL` and `SUPABASE_KEY` in `.env`
- Ensure tables are created in Supabase

**"Reddit API error":**
- Get credentials at https://www.reddit.com/prefs/apps
- Update `.env` with your credentials

**"YouTube API quota exceeded":**
- Get a new API key at https://console.cloud.google.com
- Consider enabling billing for higher quota

## License

This project is for internal use. All rights reserved.

## Credits

- Flask web framework
- Supabase backend
- Tailwind CSS for styling
- Font Awesome for icons
- PRAW for Reddit API
- yt-dlp for YouTube downloads
- openpyxl for Excel export
