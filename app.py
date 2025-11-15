"""
NOA SQL Scanner Web Edition
Production-ready Flask Application with Debug Tools
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
    """Dork Search - Wayback Machine focused"""
    if request.method == 'POST':
        dork_query = request.form.get('dork_query')
        search_engine = request.form.get('engine', 'wayback')
        max_results = int(request.form.get('max_results', 50))
        
        if max_results > Config.DORK_MAX_RESULTS:
            max_results = Config.DORK_MAX_RESULTS
        
        all_urls = []
        errors = []
        
        try:
            # Wayback Machine search
            if search_engine == 'wayback' or search_engine == 'multi':
                flash('Searching Wayback Machine...', 'info')
                
                import requests
                import re
                
                # Extract domain from dork query
                domain_match = re.search(r'site:([^\s]+)', dork_query)
                
                if domain_match:
                    domain = domain_match.group(1).strip()
                    
                    # Extract inurl pattern if exists
                    inurl_match = re.search(r'inurl:"([^"]+)"', dork_query)
                    inurl_pattern = inurl_match.group(1) if inurl_match else None
                    
                    # Build Wayback patterns
                    if inurl_pattern:
                        patterns = [
                            f'*.{domain}/*{inurl_pattern}*',
                            f'*.{domain}/*.php?id=*',
                            f'*.{domain}/*?id=*',
                        ]
                    else:
                        patterns = [
                            f'*.{domain}/*.php?*',
                            f'*.{domain}/*?id=*',
                            f'*.{domain}/*',
                        ]
                    
                    wayback_found = 0
                    
                    for pattern in patterns:
                        try:
                            url = "http://web.archive.org/cdx/search/cdx"
                            params = {
                                'url': pattern,
                                'matchType': 'domain',
                                'output': 'json',
                                'fl': 'original',
                                'collapse': 'urlkey',
                                'limit': max_results
                            }
                            
                            response = requests.get(url, params=params, timeout=30)
                            
                            if response.status_code == 200:
                                data = response.json()
                                
                                # Skip header (first item)
                                for item in data[1:]:
                                    if isinstance(item, list) and len(item) > 0:
                                        found_url = item[0]
                                        
                                        # Accept ANY http URL
                                        if found_url.startswith('http'):
                                            all_urls.append(found_url)
                                            wayback_found += 1
                                
                                print(f"[+] Wayback pattern '{pattern}': Found {len(data)-1} URLs")
                            
                        except Exception as e:
                            print(f"[-] Wayback pattern error: {e}")
                            continue
                    
                    if wayback_found > 0:
                        flash(f'Wayback Machine: Found {wayback_found} archived URLs!', 'success')
                    else:
                        errors.append(f'Wayback: No archived URLs for {domain}')
                        flash('Wayback found no results. Try a broader domain (e.g., site:.tr)', 'warning')
                
                else:
                    flash('Please use site: syntax (e.g., site:.tr or site:.com.tr)', 'warning')
                    errors.append('Missing site: in query')
            
            # Try other engines if multi and we have few results
            if len(all_urls) < 5 and search_engine == 'multi':
                try:
                    from dork_engine_improved import DuckDuckGoAPIDork
                    
                    flash('Trying DuckDuckGo as backup...', 'info')
                    ddg = DuckDuckGoAPIDork()
                    urls = ddg.search(dork_query, 20)
                    
                    if urls:
                        all_urls.extend(urls)
                        flash(f'DuckDuckGo: Found {len(urls)} URLs', 'success')
                        
                except Exception as e:
                    errors.append(f'DuckDuckGo: {str(e)}')
            
            # Remove duplicates
            all_urls = list(set(all_urls))
            
            # Show results or demo
            if not all_urls:
                flash('No results from any source. Showing demo vulnerable URLs.', 'warning')
                
                # Get demo URLs
                try:
                    from dork_engine_improved import DEMO_URLS as IMPROVED_DEMO
                    all_urls = IMPROVED_DEMO
                except ImportError:
                    all_urls = DEMO_URLS
            else:
                flash(f'Success! Found {len(all_urls)} unique URLs', 'success')
                
                # Save to database
                try:
                    dork_id = db.save_dork_results(dork_query, search_engine, all_urls)
                except Exception as e:
                    print(f"[!] DB save error: {e}")
            
            # Show errors
            for error in errors:
                flash(error, 'warning')
            
            return render_template('dork_results.html', 
                                 urls=all_urls, 
                                 dork_query=dork_query, 
                                 errors=errors)
        
        except Exception as e:
            flash(f'Search error: {str(e)}', 'danger')
            print(f"[!] Dork search error: {e}")
            import traceback
            traceback.print_exc()
            
            # Fallback to demo
            return render_template('dork_results.html', 
                                 urls=DEMO_URLS, 
                                 dork_query=dork_query, 
                                 errors=[str(e)])
    
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

# ============================================================================
# DEBUG ENDPOINTS
# ============================================================================

@app.route('/debug/simple-test')
@login_required
def debug_simple_test():
    """Simplest possible test"""
    import requests
    
    results = []
    results.append("="*70)
    results.append("NOA SQL Scanner - Simple Connectivity Test")
    results.append("="*70)
    
    # Test 1: Basic connectivity
    results.append("\n=== Test 1: Basic Connectivity ===")
    test_sites = [
        ('Google', 'https://www.google.com'),
        ('DuckDuckGo API', 'https://api.duckduckgo.com/'),
        ('Wayback Machine', 'http://web.archive.org'),
    ]
    
    for name, url in test_sites:
        try:
            r = requests.get(url, timeout=10)
            results.append(f"✓ {name}: HTTP {r.status_code}")
        except Exception as e:
            results.append(f"✗ {name}: {str(e)}")
    
    # Test 2: Wayback API
    results.append("\n=== Test 2: Wayback Machine API ===")
    try:
        r = requests.get(
            'http://web.archive.org/cdx/search/cdx',
            params={'url': '*.github.com/*', 'limit': 5, 'output': 'json'},
            timeout=30
        )
        results.append(f"✓ Wayback API: HTTP {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            results.append(f"  Results: {len(data)} items")
    except Exception as e:
        results.append(f"✗ Wayback API: {str(e)}")
    
    # Test 3: Module imports
    results.append("\n=== Test 3: Module Imports ===")
    try:
        from dork_engine_improved import DEMO_URLS
        results.append("✓ dork_engine_improved imported")
        results.append(f"  Demo URLs: {len(DEMO_URLS)}")
    except ImportError as e:
        results.append(f"✗ Import failed: {str(e)}")
    
    results.append("\n" + "="*70)
    
    return '<html><head><title>Simple Test</title></head><body><pre style="font-family:monospace;background:#1e1e1e;color:#00ff00;padding:20px;">' + '\n'.join(results) + '</pre></body></html>'


@app.route('/debug/wayback-direct')
@login_required
def debug_wayback_direct():
    """Direct Wayback Machine test"""
    import requests
    
    results = []
    results.append("="*70)
    results.append("Wayback Machine Direct Test")
    results.append("="*70)
    
    test_patterns = [
        ('*.com.tr/*', 'Turkish Commercial'),
        ('*.org.tr/*', 'Turkish Organizations'),
        ('*.github.com/*', 'GitHub'),
    ]
    
    total_found = 0
    all_urls = []
    
    for pattern, description in test_patterns:
        results.append(f"\n=== {description} ===")
        results.append(f"Pattern: {pattern}")
        
        try:
            r = requests.get(
                'http://web.archive.org/cdx/search/cdx',
                params={
                    'url': pattern,
                    'matchType': 'domain',
                    'output': 'json',
                    'fl': 'original',
                    'limit': 10
                },
                timeout=30
            )
            
            results.append(f"HTTP: {r.status_code}")
            
            if r.status_code == 200:
                data = r.json()
                count = len(data) - 1
                
                if count > 0:
                    results.append(f"✓ Found {count} URLs\n")
                    total_found += count
                    
                    for item in data[1:6]:
                        if isinstance(item, list) and item:
                            url = item[0]
                            results.append(f"  → {url}")
                            all_urls.append(url)
                else:
                    results.append("✗ No URLs")
        except Exception as e:
            results.append(f"✗ Error: {e}")
    
    results.append(f"\n{'='*70}")
    results.append(f"TOTAL: {total_found} URLs found")
    results.append(f"{'='*70}")
    
    if total_found > 0:
        results.append("\n✓ SUCCESS! Wayback is working.")
        results.append("\nGo to Dork Search and try:")
        results.append("  Query: site:.com.tr")
        results.append("  Engine: Wayback Machine")
    
    return '<html><head><title>Wayback Test</title><style>body{font-family:monospace;background:#1e1e1e;color:#00ff00;padding:20px;}pre{white-space:pre-wrap;}</style></head><body><pre>' + '\n'.join(results) + '</pre></body></html>'


@app.route('/debug/test-search')
@login_required
def debug_test_search():
    """Search engine test with template"""
    results = {
        'engines_tested': [],
        'working_engines': [],
        'failed_engines': [],
        'sample_results': {},
        'logs': []
    }
    
    try:
        from dork_engine_improved import DuckDuckGoAPIDork, PublicAPISearcher
        
        results['logs'].append('✓ Imported dork_engine_improved')
        
        # Test Wayback
        results['logs'].append('\n=== Wayback Machine ===')
        try:
            wayback = PublicAPISearcher()
            urls = wayback.search_wayback('*.com.tr/*', 20)
            
            if urls:
                results['working_engines'].append('Wayback Machine')
                results['sample_results']['Wayback Machine'] = urls[:3]
                results['logs'].append(f'✓ Found {len(urls)} URLs')
            else:
                results['failed_engines'].append('Wayback Machine')
                results['logs'].append('✗ No URLs')
                
            results['engines_tested'].append('Wayback Machine')
        except Exception as e:
            results['failed_engines'].append('Wayback Machine')
            results['logs'].append(f'✗ Error: {e}')
        
    except ImportError as e:
        results['logs'].append(f'✗ Import Error: {e}')
    
    return render_template('debug_search.html', results=results)


@app.route('/debug/test-wayback-turkish')
@login_required
def debug_test_wayback_turkish():
    """Test Turkish sites via Wayback"""
    results = {
        'tested_domains': [],
        'successful_domains': [],
        'total_urls_found': 0,
        'sample_urls': [],
        'logs': []
    }
    
    try:
        from dork_engine_improved import PublicAPISearcher
        
        wayback = PublicAPISearcher()
        
        patterns = [
            ('*.com.tr/*', 'Commercial'),
            ('*.org.tr/*', 'Organizations'),
        ]
        
        for pattern, desc in patterns:
            results['logs'].append(f'\n{desc}: {pattern}')
            results['tested_domains'].append(desc)
            
            try:
                urls = wayback.search_wayback(pattern, 15)
                
                if urls:
                    results['successful_domains'].append(desc)
                    results['total_urls_found'] += len(urls)
                    results['sample_urls'].extend(urls[:3])
                    results['logs'].append(f'✓ Found {len(urls)}')
                else:
                    results['logs'].append('✗ No URLs')
            except Exception as e:
                results['logs'].append(f'✗ Error: {e}')
        
        results['logs'].append(f'\nTotal: {results["total_urls_found"]} URLs')
        
    except ImportError as e:
        results['logs'].append(f'✗ Import: {e}')
    
    return render_template('debug_wayback.html', results=results)

# ============================================================================
# END DEBUG ENDPOINTS
# ============================================================================

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

# Health check
@app.route('/health')
def health():
    return jsonify({'status': 'healthy', 'version': '1.9.0.3'}), 200

# Run
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port, debug=True, allow_unsafe_werkzeug=True)
