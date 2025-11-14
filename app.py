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
from dork_engine_improved import MultiEngineDork, SQL_DORKS, DEMO_URLS
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
        search_engine = request.form.get('engine', 'multi')
        max_results = int(request.form.get('max_results', 50))
        
        if max_results > Config.DORK_MAX_RESULTS:
            max_results = Config.DORK_MAX_RESULTS
        
        all_urls = []
        errors = []
        
        try:
            # Import the new multi-engine
            from dork_engine_improved import (
                MultiEngineDork, DuckDuckGoHTMLDork, BingDork, 
                DEMO_URLS
            )
            
            # Option 1: Multi-engine (recommended)
            if search_engine == 'multi':
                flash('Using multi-engine search (DuckDuckGo + Bing)...', 'info')
                
                # Get API keys from environment if available
                serpapi_key = os.environ.get('SERPAPI_KEY')
                google_cse_key = os.environ.get('GOOGLE_CSE_KEY')
                google_cx = os.environ.get('GOOGLE_CX')
                
                searcher = MultiEngineDork(
                    serpapi_key=serpapi_key,
                    google_cse_key=google_cse_key,
                    google_cx=google_cx
                )
                all_urls = searcher.search(dork_query, max_results)
            
            # Option 2: DuckDuckGo only
            elif search_engine == 'duckduckgo':
                flash('Searching DuckDuckGo...', 'info')
                ddg = DuckDuckGoHTMLDork()
                all_urls = ddg.search(dork_query, max_results)
            
            # Option 3: Bing only
            elif search_engine == 'bing':
                flash('Searching Bing...', 'info')
                bing = BingDork()
                all_urls = bing.search(dork_query, max_results)
            
            # Option 4: Original engines (fallback)
            else:
                flash('Using original search engines...', 'info')
                
                # Try Google first
                try:
                    from dork_engine import GoogleDork
                    google = GoogleDork()
                    urls = google.search(dork_query, max_results)
                    all_urls.extend(urls)
                    if urls:
                        flash(f'Google: Found {len(urls)} URLs', 'success')
                except Exception as e:
                    errors.append(f'Google error: {str(e)}')
                
                # Try Yandex
                if len(all_urls) < 10:
                    try:
                        from dork_engine import YandexDork
                        yandex = YandexDork()
                        urls = yandex.search(dork_query, max_results)
                        all_urls.extend(urls)
                        if urls:
                            flash(f'Yandex: Found {len(urls)} URLs', 'success')
                    except Exception as e:
                        errors.append(f'Yandex error: {str(e)}')
            
            # Remove duplicates
            all_urls = list(set(all_urls))
            
            # Show results or demo URLs
            if all_urls:
                flash(f'Found {len(all_urls)} unique URLs!', 'success')
                
                # Save to database
                dork_id = db.save_dork_results(dork_query, search_engine, all_urls)
            else:
                flash('No results found. Showing demo vulnerable URLs for testing.', 'warning')
                all_urls = DEMO_URLS
            
            # Show any errors
            if errors:
                for error in errors:
                    flash(error, 'warning')
            
            return render_template('dork_results.html', 
                                 urls=all_urls, 
                                 dork_query=dork_query, 
                                 errors=errors)
        
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

@app.route('/debug/test-search')
@login_required
def debug_test_search():
    """Debug endpoint to test search engines"""
    import sys
    from io import StringIO
    
    # Capture output
    old_stdout = sys.stdout
    sys.stdout = StringIO()
    
    results = {
        'engines_tested': [],
        'working_engines': [],
        'failed_engines': [],
        'sample_results': {},
        'logs': []
    }
    
    try:
        from dork_engine_improved import (
            DuckDuckGoAPIDork,
            BraveDork,
            StartpageDork,
            PublicAPISearcher,
            MultiEngineDork
        )
        
        results['logs'].append('✓ Successfully imported dork_engine_improved')
        
        # Test query
        test_query = 'site:.edu inurl:".php?id="'
        
        # Test 1: DuckDuckGo API
        results['logs'].append('\n=== Testing DuckDuckGo API ===')
        try:
            ddg = DuckDuckGoAPIDork()
            urls = ddg.search(test_query, max_results=10)
            
            if urls:
                results['working_engines'].append('DuckDuckGo API')
                results['sample_results']['DuckDuckGo API'] = urls[:3]
                results['logs'].append(f'✓ DuckDuckGo API: Found {len(urls)} URLs')
            else:
                results['failed_engines'].append('DuckDuckGo API')
                results['logs'].append('✗ DuckDuckGo API: No results')
                
            results['engines_tested'].append('DuckDuckGo API')
        except Exception as e:
            results['failed_engines'].append('DuckDuckGo API')
            results['logs'].append(f'✗ DuckDuckGo API Error: {str(e)}')
        
        # Test 2: Brave Search
        results['logs'].append('\n=== Testing Brave Search ===')
        try:
            brave = BraveDork()
            urls = brave.search(test_query, max_results=10)
            
            if urls:
                results['working_engines'].append('Brave')
                results['sample_results']['Brave'] = urls[:3]
                results['logs'].append(f'✓ Brave: Found {len(urls)} URLs')
            else:
                results['failed_engines'].append('Brave')
                results['logs'].append('✗ Brave: No results')
                
            results['engines_tested'].append('Brave')
        except Exception as e:
            results['failed_engines'].append('Brave')
            results['logs'].append(f'✗ Brave Error: {str(e)}')
        
        # Test 3: Wayback Machine
        results['logs'].append('\n=== Testing Wayback Machine ===')
        try:
            wayback = PublicAPISearcher()
            urls = wayback.search_wayback('*.edu.tr/*id=*', max_results=20)
            
            if urls:
                results['working_engines'].append('Wayback Machine')
                results['sample_results']['Wayback Machine'] = urls[:3]
                results['logs'].append(f'✓ Wayback: Found {len(urls)} URLs')
            else:
                results['failed_engines'].append('Wayback Machine')
                results['logs'].append('✗ Wayback: No results')
                
            results['engines_tested'].append('Wayback Machine')
        except Exception as e:
            results['failed_engines'].append('Wayback Machine')
            results['logs'].append(f'✗ Wayback Error: {str(e)}')
        
        # Test 4: Multi-Engine
        results['logs'].append('\n=== Testing Multi-Engine ===')
        try:
            multi = MultiEngineDork()
            urls = multi.search(test_query, max_results=20)
            
            if urls:
                results['working_engines'].append('Multi-Engine')
                results['sample_results']['Multi-Engine'] = urls[:5]
                results['logs'].append(f'✓ Multi-Engine: Found {len(urls)} total URLs')
            else:
                results['failed_engines'].append('Multi-Engine')
                results['logs'].append('✗ Multi-Engine: No results from any source')
                
            results['engines_tested'].append('Multi-Engine')
        except Exception as e:
            results['failed_engines'].append('Multi-Engine')
            results['logs'].append(f'✗ Multi-Engine Error: {str(e)}')
        
    except ImportError as e:
        results['logs'].append(f'✗ Import Error: {str(e)}')
        results['logs'].append('Make sure dork_engine_improved.py is deployed')
    except Exception as e:
        results['logs'].append(f'✗ Fatal Error: {str(e)}')
        import traceback
        results['logs'].append(traceback.format_exc())
    
    # Restore stdout
    output = sys.stdout.getvalue()
    sys.stdout = old_stdout
    
    if output:
        results['console_output'] = output
    
    return render_template('debug_search.html', results=results)


@app.route('/debug/test-wayback-turkish')
@login_required
def debug_test_wayback_turkish():
    """Test Wayback Machine specifically for Turkish sites"""
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
        
        # Test different Turkish domains
        turkish_domains = [
            ('*.edu.tr/*id=*', 'Turkish Educational'),
            ('*.gov.tr/*id=*', 'Turkish Government'),
            ('*.com.tr/*php?id=*', 'Turkish Commercial'),
            ('*.tr/*haber.php*', 'Turkish News Sites'),
        ]
        
        for pattern, description in turkish_domains:
            results['logs'].append(f'\nTesting: {description}')
            results['logs'].append(f'Pattern: {pattern}')
            results['tested_domains'].append(description)
            
            try:
                urls = wayback.search_wayback(pattern, max_results=15)
                
                if urls:
                    results['successful_domains'].append(description)
                    results['total_urls_found'] += len(urls)
                    results['sample_urls'].extend(urls[:3])
                    results['logs'].append(f'✓ Found {len(urls)} archived URLs')
                else:
                    results['logs'].append('✗ No archived URLs found')
                    
            except Exception as e:
                results['logs'].append(f'✗ Error: {str(e)}')
        
        # Summary
        results['logs'].append('\n=== SUMMARY ===')
        results['logs'].append(f'Tested: {len(results["tested_domains"])} domain patterns')
        results['logs'].append(f'Successful: {len(results["successful_domains"])} patterns')
        results['logs'].append(f'Total URLs: {results["total_urls_found"]}')
        
    except ImportError as e:
        results['logs'].append(f'✗ Import Error: {str(e)}')
    except Exception as e:
        results['logs'].append(f'✗ Fatal Error: {str(e)}')
        import traceback
        results['logs'].append(traceback.format_exc())
    
    return render_template('debug_wayback.html', results=results)


@app.route('/debug/simple-test')
@login_required
def debug_simple_test():
    """Simplest possible test"""
    import requests
    
    results = []
    
    # Test 1: Basic connectivity
    results.append("=== Test 1: Basic Connectivity ===")
    try:
        r = requests.get('https://www.google.com', timeout=10)
        results.append(f"✓ Google: {r.status_code}")
    except Exception as e:
        results.append(f"✗ Google: {e}")
    
    try:
        r = requests.get('https://api.duckduckgo.com/', timeout=10)
        results.append(f"✓ DuckDuckGo API: {r.status_code}")
    except Exception as e:
        results.append(f"✗ DuckDuckGo API: {e}")
    
    # Test 2: Wayback Machine
    results.append("\n=== Test 2: Wayback Machine ===")
    try:
        r = requests.get(
            'http://web.archive.org/cdx/search/cdx',
            params={
                'url': '*.github.com/*',
                'limit': 5,
                'output': 'json'
            },
            timeout=30
        )
        results.append(f"✓ Wayback: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            results.append(f"  Results: {len(data)} items")
    except Exception as e:
        results.append(f"✗ Wayback: {e}")
    
    # Test 3: Import test
    results.append("\n=== Test 3: Module Import ===")
    try:
        from dork_engine_improved import MultiEngineDork
        results.append("✓ dork_engine_improved imported successfully")
    except ImportError as e:
        results.append(f"✗ Import failed: {e}")
    
    # Test 4: Demo URLs
    results.append("\n=== Test 4: Demo URLs ===")
    try:
        from dork_engine_improved import DEMO_URLS
        results.append(f"✓ Demo URLs available: {len(DEMO_URLS)}")
        for url in DEMO_URLS[:3]:
            results.append(f"  - {url}")
    except Exception as e:
        results.append(f"✗ Demo URLs error: {e}")
    
    return '<html><body><pre>' + '\n'.join(results) + '</pre></body></html>'
