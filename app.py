"""
NOA SQL Scanner Web Edition
Production-ready Flask Application
"""

from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash, send_file
from flask_socketio import SocketIO, emit, join_room
from functools import wraps
import secrets
import os
from datetime import datetime, timedelta

from auth import check_password, hash_password
from dork_engine import GoogleDork, YandexDork, SQL_DORKS, DEMO_URLS
from scanner_api import ScannerAPI
from database import Database
from config_web import Config

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Initialize SocketIO
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Initialize components
db = Database(app.config['DATABASE_PATH'])
scanner_api = ScannerAPI(socketio, db)

# Access password hash
ACCESS_PASSWORD_HASH = hash_password(app.config['ACCESS_PASSWORD'])

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'authenticated' not in session:
            flash('Please login first', 'warning')
            return redirect(url_for('login'))
        
        # Check session timeout
        login_time = session.get('login_time')
        if login_time:
            login_dt = datetime.fromisoformat(login_time)
            if datetime.now() - login_dt > timedelta(minutes=Config.SESSION_TIMEOUT):
                session.clear()
                flash('Session expired. Please login again.', 'warning')
                return redirect(url_for('login'))
        
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    if 'authenticated' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form.get('password')
        
        if check_password(password, ACCESS_PASSWORD_HASH):
            session['authenticated'] = True
            session['login_time'] = datetime.now().isoformat()
            session['session_id'] = secrets.token_hex(16)
            flash('Successfully logged in!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid password!', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Successfully logged out!', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    stats = db.get_statistics()
    recent_scans = db.get_recent_scans(limit=10)
    return render_template('dashboard.html', stats=stats, recent_scans=recent_scans)

@app.route('/scan', methods=['GET', 'POST'])
@login_required
def scan():
    if request.method == 'POST':
        target_url = request.form.get('url')
        enable_subdomains = request.form.get('subdomains') == 'on'
        enable_deep = request.form.get('deep') == 'on'
        
        # Validate URL
        if not target_url.startswith(('http://', 'https://')):
            flash('Invalid URL format. Must start with http:// or https://', 'danger')
            return redirect(url_for('scan'))
        
        # Start scan in background
        scan_id = scanner_api.start_scan(target_url, enable_subdomains, enable_deep)
        flash('Scan started successfully!', 'success')
        
        return redirect(url_for('scan_progress', scan_id=scan_id))
    
    # Check if URL is passed as query parameter (from dork results)
    preset_url = request.args.get('url', '')
    return render_template('scan.html', preset_url=preset_url)

@app.route('/scan/progress/<scan_id>')
@login_required
def scan_progress(scan_id):
    scan_info = scanner_api.get_scan_status(scan_id)
    if not scan_info:
        flash('Scan not found', 'danger')
        return redirect(url_for('dashboard'))
    return render_template('scan_progress.html', scan_id=scan_id, scan_info=scan_info)

@app.route('/dork', methods=['GET', 'POST'])
@login_required
def dork_search():
    if request.method == 'POST':
        dork_query = request.form.get('dork_query')
        search_engine = request.form.get('engine', 'google')
        max_results = int(request.form.get('max_results', 50))
        
        # Validate max results
        if max_results > Config.DORK_MAX_RESULTS:
            max_results = Config.DORK_MAX_RESULTS
        
        try:
            # Perform dork search
            if search_engine == 'google':
                dork = GoogleDork()
            else:
                dork = YandexDork()
            
            flash('Searching... This may take a few minutes.', 'info')
            urls = dork.search(dork_query, max_results)
            
            # Eğer sonuç yoksa demo URL'leri göster
            if not urls:
                flash('No results found from search engine. Showing demo vulnerable URLs for testing.', 'warning')
                urls = DEMO_URLS
            
            # Save to database
            dork_id = db.save_dork_results(dork_query, search_engine, urls)
            
            flash(f'Found {len(urls)} URLs!', 'success')
            return render_template('dork_results.html', urls=urls, dork_query=dork_query)
        
        except Exception as e:
            flash(f'Error during search: {str(e)}', 'danger')
            print(f"[!] Dork search error: {e}")
            import traceback
            traceback.print_exc()
            return redirect(url_for('dork_search'))
    
    return render_template('dork.html', predefined_dorks=SQL_DORKS)

@app.route('/reports')
@login_required
def reports():
    all_scans = db.get_all_scans()
    return render_template('reports.html', scans=all_scans)

@app.route('/report/<scan_id>')
@login_required
def view_report(scan_id):
    scan_data = db.get_scan_details(scan_id)
    if not scan_data:
        flash('Report not found', 'danger')
        return redirect(url_for('reports'))
    
    vulnerabilities = db.get_vulnerabilities(scan_id)
    return render_template('report.html', scan=scan_data, vulnerabilities=vulnerabilities)

@app.route('/download/<scan_id>')
@login_required
def download_report(scan_id):
    scan_info = db.get_scan_info(scan_id)
    if not scan_info or not scan_info.get('report_file'):
        flash('Report file not found', 'danger')
        return redirect(url_for('reports'))
    
    report_file = scan_info['report_file']
    if os.path.exists(report_file):
        return send_file(report_file, as_attachment=True, download_name=f'noa_scan_{scan_id[:8]}.txt')
    else:
        flash('Report file does not exist', 'danger')
        return redirect(url_for('reports'))

# API Endpoints
@app.route('/api/scan/status/<scan_id>')
@login_required
def api_scan_status(scan_id):
    status = scanner_api.get_scan_status(scan_id)
    if status:
        return jsonify(status)
    return jsonify({'error': 'Scan not found'}), 404

@app.route('/api/scan/stop/<scan_id>', methods=['POST'])
@login_required
def api_stop_scan(scan_id):
    try:
        scanner_api.stop_scan(scan_id)
        return jsonify({'status': 'stopped', 'success': True})
    except Exception as e:
        print(f"[!] Error stopping scan: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/stats')
@login_required
def api_stats():
    stats = db.get_statistics()
    return jsonify(stats)

# WebSocket events
@socketio.on('connect')
def handle_connect():
    if 'authenticated' not in session:
        return False
    emit('connected', {'message': 'Connected to NOA Scanner'})

@socketio.on('subscribe_scan')
def handle_subscribe(data):
    scan_id = data.get('scan_id')
    join_room(f'scan_{scan_id}')
    emit('subscribed', {'scan_id': scan_id})

@socketio.on('disconnect')
def handle_disconnect():
    pass

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

# Health check endpoint for deployment platforms
@app.route('/health')
def health():
    return jsonify({'status': 'healthy', 'version': '1.9.0.3'}), 200

# For local development only
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port, debug=True, allow_unsafe_werkzeug=True)
