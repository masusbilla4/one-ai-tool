"""
Sentence Database - Flask routes.
All URL routes for the Sentence DB module.
"""
import os
import csv
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify, send_file, current_app
from werkzeug.utils import secure_filename

from .db import insert_sentence, update_sentence, delete_sentence, check_sentence_exists, get_sentence_by_id
from .stats import get_stats, get_remaining_stats, get_categories, get_category_stats, get_database_info, _invalidate_cache
from .cart import get_all_sentences, search_sentences, get_filtered_sentences, mark_sentences_as_used
from .import_export import import_from_csv_to_db, import_from_sqlite_file, export_to_csv_string
from .duplicates import find_duplicate_sentences, delete_duplicate_sentences

from auth.routes import login_required

sentencedb_bp = Blueprint('sentencedb', __name__, template_folder='templates')


@sentencedb_bp.route('/')
@login_required
def dashboard():
    """Main Sentence DB dashboard."""
    total, eng, fil = get_stats()
    fil_remaining, eng_remaining = get_remaining_stats()
    return render_template('sentencedb/dashboard.html', 
                         total=total, eng=eng, fil=fil,
                         fil_remaining=fil_remaining, eng_remaining=eng_remaining)


@sentencedb_bp.route('/stats')
@login_required
def get_stats_api():
    """API: Get database statistics."""
    info = get_database_info()
    return jsonify(info)


@sentencedb_bp.route('/category-stats')
@login_required
def get_category_stats_api():
    """API: Get category breakdown."""
    stats = get_category_stats()
    return jsonify(stats)


# ========== ADD SENTENCE ==========

@sentencedb_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    """Add new sentence page."""
    if request.method == 'POST':
        sentence = request.form.get('sentence', '').strip()
        category = request.form.get('category', '').strip()
        language = request.form.get('language', 'fil')
        
        if not sentence:
            flash('Sentence cannot be empty!', 'error')
            return render_template('sentencedb/add.html', categories=get_categories())
        
        # Validate category - reject __NEW__ placeholder
        if not category or category == '__NEW__':
            flash('Please select or enter a valid category!', 'error')
            return render_template('sentencedb/add.html', categories=get_categories())
        
        # Check for duplicates
        exists, existing_id, existing_cat, existing_lang = check_sentence_exists(sentence)
        if exists:
            flash(f'Duplicate detected! ID: {existing_id}, Category: {existing_cat}', 'warning')
            return render_template('sentencedb/add.html', categories=get_categories(), 
                                 existing={'id': existing_id, 'category': existing_cat})
        
        result = insert_sentence(sentence, category, language)
        flash(f'Sentence added! ID: {result["sen_id"]}', 'success')
        return redirect(url_for('sentencedb.dashboard'))
    
    return render_template('sentencedb/add.html', categories=get_categories())


# ========== EDIT SENTENCE ==========

@sentencedb_bp.route('/edit', methods=['GET', 'POST'])
@login_required
def edit():
    """Edit sentences page."""
    search_keyword = request.args.get('search', '')
    sentences = []
    
    if search_keyword:
        sentences = search_sentences(search_keyword)
    else:
        sentences = get_all_sentences()
    
    if request.method == 'POST':
        sen_id = request.form.get('sen_id')
        edited_text = request.form.get('edited_text', '').strip()
        language = request.form.get('language', 'fil')
        
        if sen_id and edited_text:
            result = update_sentence(sen_id, edited_text, language)
            if result['success']:
                flash('Sentence updated!', 'success')
            else:
                flash('Failed to update sentence.', 'error')
        return redirect(url_for('sentencedb.edit'))
    
    return render_template('sentencedb/edit.html', sentences=sentences, search_keyword=search_keyword)


# ========== SHOP / CART ==========

@sentencedb_bp.route('/shop', methods=['GET', 'POST'])
@login_required
def shop():
    """Shop for sentences page."""
    fil_remaining, eng_remaining = get_remaining_stats()
    categories = get_categories()
    
    # Get cart from session
    cart = session.get('cart', [])
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add_to_cart':
            category = request.form.get('category')
            language = request.form.get('language', 'fil')
            quantity = int(request.form.get('quantity', 10))
            
            sentences = get_filtered_sentences(category if category != 'All' else None, language, None)
            
            # Filter out already in cart
            cart_set = set((item[0], item[1], item[2]) for item in cart)
            available = [s for s in sentences if (s[0], s[1], s[2]) not in cart_set]
            
            if available:
                import random
                selected = random.sample(available, min(quantity, len(available)))
                cart.extend(selected)
                session['cart'] = cart
                flash(f'Added {len(selected)} sentences to cart!', 'success')
        
        elif action == 'remove_selected':
            # Remove selected items from cart
            indices_to_remove = request.form.getlist('cart_indices')
            if indices_to_remove:
                indices_to_remove = [int(i) for i in indices_to_remove]
                # Sort in reverse order to remove from end first (preserves indices)
                for i in sorted(indices_to_remove, reverse=True):
                    if 0 <= i < len(cart):
                        cart.pop(i)
                session['cart'] = cart
                flash(f'Removed {len(indices_to_remove)} items from cart.', 'success')
        
        elif action == 'clear_cart':
            session['cart'] = []
            flash('Cart cleared.', 'info')
        
        elif action == 'checkout':
            if cart:
                marked = mark_sentences_as_used(cart)
                session['cart'] = []
                flash(f'Checkout complete! {marked} sentences marked as used.', 'success')
                # Generate CSV for download
                session['export_csv'] = True
    
    # Redirect back to dashboard with flash message and section parameter
    if request.method == 'POST':
        return redirect(url_for('main_dashboard') + '#shop')
    
    return redirect(url_for('main_dashboard') + '#shop')


@sentencedb_bp.route('/shop/export')
@login_required
def shop_export():
    """Export cart as CSV."""
    cart = session.get('cart', [])
    if not cart:
        flash('Cart is empty!', 'error')
        return redirect(url_for('sentencedb.shop'))
    
    # Generate CSV
    csv_buffer = export_cart_csv(cart)
    return send_file(
        csv_buffer,
        mimetype='text/csv',
        as_attachment=True,
        download_name='exported_sentences.csv'
    )


def export_cart_csv(cart):
    """Generate CSV from cart data."""
    from io import BytesIO
    output = BytesIO()
    writer = csv.writer(output)
    writer.writerow(['sentence', 'category', 'language', 'word_count'])
    writer.writerows(cart)
    output.seek(0)
    return output


# ========== IMPORT/EXPORT ==========

@sentencedb_bp.route('/import', methods=['GET', 'POST'])
@login_required
def import_page():
    """Import data page."""
    total, eng, fil = get_stats()
    
    if request.method == 'POST':
        import_type = request.form.get('import_type')
        
        if import_type == 'csv':
            file = request.files.get('csv_file')
            if file:
                csv_content = file.read().decode('utf-8')
                imported, skipped, error = import_from_csv_to_db(csv_content)
                if error:
                    flash(f'Error: {error}', 'error')
                else:
                    flash(f'Imported: {imported} | Skipped: {skipped}', 'success')
        
        elif import_type == 'sqlite':
            file = request.files.get('sqlite_file')
            if file:
                # Save temp file
                temp_path = os.path.join(current_app.config.get('UPLOAD_FOLDER', '/tmp'), secure_filename(file.filename))
                file.save(temp_path)
                imported, skipped, error = import_from_sqlite_file(temp_path)
                if error:
                    flash(f'Error: {error}', 'error')
                else:
                    flash(f'Imported: {imported} | Skipped: {skipped}', 'success')
        
        elif import_type == 'export':
            csv_data = export_to_csv_string()
            return send_file(
                f'data:text/csv;charset=utf-8,{csv_data}',
                mimetype='text/csv',
                as_attachment=True,
                download_name='database_export.csv'
            )
    
    return render_template('sentencedb/import.html', total=total, eng=eng, fil=fil)


@sentencedb_bp.route('/import/template')
@login_required
def download_template():
    """Download CSV import template."""
    from io import BytesIO
    import csv
    
    # Create CSV in memory
    output = BytesIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['sentence', 'category', 'language'])
    
    # Write sample rows
    writer.writerow(['Magandang umaga', 'Greetings', 'fil'])
    writer.writerow(['Good morning', 'Greetings', 'en'])
    writer.writerow(['Salamat', 'Greetings', 'fil'])
    writer.writerow(['Thank you', 'Greetings', 'en'])
    writer.writerow(['Kumusta ka?', 'Greetings', 'fil'])
    writer.writerow(['How are you?', 'Greetings', 'en'])
    
    output.seek(0)
    
    return send_file(
        output,
        mimetype='text/csv',
        as_attachment=True,
        download_name='sentence_import_template.csv'
    )


# ========== DUPLICATE MANAGEMENT ==========

@sentencedb_bp.route('/duplicates')
@login_required
def duplicates():
    """Find and manage duplicates."""
    duplicates = find_duplicate_sentences()
    return render_template('sentencedb/duplicates.html', duplicates=duplicates)


@sentencedb_bp.route('/duplicates/delete', methods=['POST'])
@login_required
def delete_duplicates():
    """Delete selected duplicates."""
    sen_ids = request.form.getlist('sen_ids')
    language = request.form.get('language', 'fil')
    
    if sen_ids:
        deleted = delete_duplicate_sentences(sen_ids, language)
        flash(f'Deleted {deleted} duplicates!', 'success')
    
    return redirect(url_for('sentencedb.duplicates'))
