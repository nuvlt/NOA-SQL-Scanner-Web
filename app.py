"""
NOA SQL Scanner Web Edition
Main Flask Application
"""

from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_socketio import SocketIO, emit
from functools import wraps
import secrets
import hashlib
from datetime import datetime
import json

from auth import check_password, hash_password
from dork_engine import GoogleDork, YandexDork
from scanner_api import ScannerAPI
from database import Database

app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_hex(32)
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize components
db = Database()
scanner_api = ScannerAPI(socketio)

# Access password (değiştir!)
ACCESS_PASSWORD_HASH = hash_password("NOA2025SecurePass!")

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'authenticated' not in session:
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
        
        # Start scan in background
        scan_id = scanner_api.start_scan(target_url, enable_subdomains, enable_deep)
        
        return redirect(url_for('scan_progress', scan_id=scan_id))
    
    return render_template('scan.html')

@app.route('/scan/progress/<scan_id>')
@login_required
def scan_progress(scan_id):
    scan_info = db.get_scan_info(scan_id)
    return render_template('scan_progress.html', scan_id=scan_id, scan_info=scan_info)

@app.route('/dork', methods=['GET', 'POST'])
@login_required
def dork_search():
    if request.method == 'POST':
        dork_query = request.form.get('dork_query')
        search_engine = request.form.get('engine', 'google')  # google or yandex
        max_results = int(request.form.get('max_results', 50))
        
        # Perform dork search
        if search_engine == 'google':
            dork = GoogleDork()
        else:
            dork = YandexDork()
        
        urls = dork.search(dork_query, max_results)
        
        # Save to database
        dork_id = db.save_dork_results(dork_query, search_engine, urls)
        
        return render_template('dork_results.html', urls=urls, dork_query=dork_query)
    
    # Predefined dorks
    predefined_dorks = [
        "inurl:php?id=",
        "inurl:asp?id=",
        "inurl:product.php?id=",
        "inurl:index.php?id=",
        "inurl:news.php?id=",
        "inurl:item.php?id=",
        "inurl:page.php?id=",
        "inurl:gallery.php?id=",
    ]
    
    return render_template('dork.html', predefined_dorks=predefined_dorks)

@app.route('/reports')
@login_required
def reports():
    all_scans = db.get_all_scans()
    return render_template('reports.html', scans=all_scans)

@app.route('/report/<scan_id>')
@login_required
def view_report(scan_id):
    scan_data = db.get_scan_details(scan_id)
    vulnerabilities = db.get_vulnerabilities(scan_id)
    return render_template('report.html', scan=scan_data, vulnerabilities=vulnerabilities)

# API Endpoints
@app.route('/api/scan/status/<scan_id>')
@login_required
def api_scan_status(scan_id):
    status = db.get_scan_status(scan_id)
    return jsonify(status)

@app.route('/api/scan/stop/<scan_id>', methods=['POST'])
@login_required
def api_stop_scan(scan_id):
    scanner_api.stop_scan(scan_id)
    return jsonify({'status': 'stopped'})

# WebSocket events for real-time updates
@socketio.on('connect')
def handle_connect():
    if 'authenticated' not in session:
        return False
    emit('connected', {'message': 'Connected to NOA Scanner'})

@socketio.on('subscribe_scan')
def handle_subscribe(data):
    scan_id = data.get('scan_id')
    # Join room for this scan
    from flask_socketio import join_room
    join_room(f'scan_{scan_id}')

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
