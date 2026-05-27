"""
ASR Aligner - Flask routes.
All URL routes for the ASR Web App module.
"""
from flask import Blueprint, render_template, request, jsonify, session, send_file, flash, redirect, url_for
import os
import csv
from io import BytesIO, StringIO

from .alignment_engine import run_alignment, align_translation_local

from auth.routes import login_required

asr_bp = Blueprint('asr', __name__, template_folder='templates')

# Store alignment results in memory (per session)
_alignment_results = {}


@asr_bp.route('/')
@login_required
def asr_home():
    """ASR Aligner home page."""
    return render_template('asr/aligner.html')


@asr_bp.route('/align', methods=['POST'])
@login_required
def align():
    """Run ASR alignment."""
    data = request.json
    true_text = data.get('true_text', '')
    asr_text = data.get('asr_text', '')
    
    if not true_text.strip() or not asr_text.strip():
        return jsonify({'error': 'Both True and ASR text are required'}), 400
    
    true_lines = [l.strip() for l in true_text.strip().split('\n') if l.strip()]
    asr_lines = [l.strip() for l in asr_text.strip().split('\n') if l.strip()]
    
    if not true_lines or not asr_lines:
        return jsonify({'error': 'No valid lines found'}), 400
    
    try:
        result = run_alignment(true_lines, asr_lines)
        
        # Store result
        task_id = f"asr_{len(_alignment_results) + 1}"
        _alignment_results[task_id] = {
            'true_lines': true_lines,
            'asr_lines': asr_lines,
            'alignment_data': result['alignment_data'],
            'overall_wer': result['overall_wer'],
            'overall_stats': result['overall_stats']
        }
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'overall_wer': result['overall_wer'],
            'overall_stats': result['overall_stats'],
            'alignment_data': result['alignment_data'][:10]  # First 10 for preview
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@asr_bp.route('/align/translation', methods=['POST'])
@login_required
def align_translation():
    """Align translation text to ASR segments."""
    data = request.json
    task_id = data.get('task_id')
    translation_text = data.get('translation_text', '')
    
    if not task_id or task_id not in _alignment_results:
        return jsonify({'error': 'Invalid task ID'}), 400
    
    if not translation_text.strip():
        return jsonify({'error': 'Translation text is required'}), 400
    
    try:
        stored = _alignment_results[task_id]
        alignment_data = stored['alignment_data']
        
        translations, method = align_translation_local(alignment_data, translation_text)
        
        # Update alignment data with translations
        for i, trans in enumerate(translations):
            if i < len(alignment_data):
                alignment_data[i]['translation'] = trans
        
        return jsonify({
            'success': True,
            'method': method,
            'translations': translations
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@asr_bp.route('/results/<task_id>')
@login_required
def get_results(task_id):
    """Get alignment results for a task."""
    if task_id not in _alignment_results:
        return jsonify({'error': 'Task not found'}), 404
    
    stored = _alignment_results[task_id]
    return jsonify({
        'success': True,
        'overall_wer': stored['overall_wer'],
        'overall_stats': stored['overall_stats'],
        'alignment_data': stored['alignment_data']
    })


@asr_bp.route('/export/csv/<task_id>')
@login_required
def export_csv(task_id):
    """Export alignment results as CSV."""
    if task_id not in _alignment_results:
        flash('Task not found.', 'error')
        return redirect(url_for('asr.asr_home'))
    
    stored = _alignment_results[task_id]
    alignment_data = stored['alignment_data']
    
    csv_buffer = StringIO()
    fieldnames = ['id', 'true', 'count', 'asr_separated', 'wer', 'score', 'translation', 'ai_reason']
    writer = csv.DictWriter(csv_buffer, fieldnames=fieldnames, extrasaction='ignore')
    writer.writeheader()
    
    for row in alignment_data:
        writer.writerow({
            'id': row['id'],
            'true': row['true'],
            'count': row['count'],
            'asr_separated': row['asr_separated'],
            'wer': row['wer'],
            'score': row['score'],
            'translation': row.get('translation', ''),
            'ai_reason': row.get('ai_reason', '')
        })
    
    output = BytesIO()
    output.write(csv_buffer.getvalue().encode('utf-8'))
    output.seek(0)
    
    return send_file(
        output,
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'asr_alignment_{task_id}.csv'
    )


@asr_bp.route('/export/excel/<task_id>')
@login_required
def export_excel(task_id):
    """Export alignment results as Excel."""
    if task_id not in _alignment_results:
        flash('Task not found.', 'error')
        return redirect(url_for('asr.asr_home'))
    
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, Alignment, PatternFill
        
        stored = _alignment_results[task_id]
        alignment_data = stored['alignment_data']
        
        wb = Workbook()
        ws = wb.active
        ws.title = "ASR Alignment"
        
        # Header styling
        header_fill = PatternFill(start_color="3b82f6", end_color="3b82f6", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF", size=11)
        headers = ['ID', 'True Text', 'Word Count', 'ASR Text', 'WER', 'Score', 'Translation', 'AI Reason']
        
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center", vertical="center")
        
        # Data rows
        for row_idx, data in enumerate(alignment_data, 2):
            ws.cell(row=row_idx, column=1, value=data['id'])
            ws.cell(row=row_idx, column=2, value=data['true'])
            ws.cell(row=row_idx, column=3, value=data['count'])
            ws.cell(row=row_idx, column=4, value=data['asr_separated'])
            ws.cell(row=row_idx, column=5, value=data['wer'])
            ws.cell(row=row_idx, column=6, value=data['score'])
            ws.cell(row=row_idx, column=7, value=data.get('translation', ''))
            ws.cell(row=row_idx, column=8, value=data.get('ai_reason', ''))
        
        # Auto-adjust column widths
        for col in ws.columns:
            max_length = 0
            column = col[0].column_letter
            for cell in col:
                if cell.value:
                    max_length = max(max_length, len(str(cell.value)))
            ws.column_dimensions[column].width = min(max_length + 2, 50)
        
        output = BytesIO()
        wb.save(output)
        output.seek(0)
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'asr_alignment_{task_id}.xlsx'
        )
    except Exception as e:
        flash(f'Export failed: {str(e)}', 'error')
        return redirect(url_for('asr.asr_home'))
