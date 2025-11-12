"""
NOA SQL Scanner Web - Scanner API Wrapper (Updated with detailed logging)
"""

import threading
import uuid
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'scanner'))

from crawler import Crawler
from scanner import SQLScanner
from reporter import Reporter

class ScannerAPI:
    def __init__(self, socketio=None, database=None):
        self.socketio = socketio
        self.database = database
        self.active_scans = {}
        self.scan_threads = {}
    
    def _emit_log(self, scan_id, message, level='info'):
        """Emit log message via WebSocket"""
        if self.socketio:
            self.socketio.emit('scan_log', {
                'scan_id': scan_id,
                'message': message,
                'level': level,
                'timestamp': datetime.now().isoformat()
            }, room=f'scan_{scan_id}')
    
    def start_scan(self, target_url, enable_subdomains=False, enable_deep=False):
        """Start a new scan in background thread"""
        scan_id = str(uuid.uuid4())
        
        scan_info = {
            'scan_id': scan_id,
            'target_url': target_url,
            'status': 'running',
            'started_at': datetime.now().isoformat(),
            'enable_subdomains': enable_subdomains,
            'enable_deep': enable_deep,
            'progress': 0,
            'urls_found': 0,
            'urls_scanned': 0,
            'vulnerabilities': [],
            'discovered_subdomains': []
        }
        
        self.active_scans[scan_id] = scan_info
        
        # Save initial scan info to database
        if self.database:
            self.database.save_scan(scan_info)
        
        # Start scan in thread
        thread = threading.Thread(
            target=self._run_scan,
            args=(scan_id, target_url, enable_subdomains, enable_deep)
        )
        thread.daemon = True
        thread.start()
        
        self.scan_threads[scan_id] = thread
        
        return scan_id
    
    def _run_scan(self, scan_id, target_url, enable_subdomains, enable_deep):
        """Run the actual scan"""
        try:
            self._emit_progress(scan_id, 'Initializing scanner...', 5)
            self._emit_log(scan_id, f'Starting scan for: {target_url}', 'info')
            
            # Initialize crawler
            crawler = Crawler(target_url)
            
            # Discover URLs
            if enable_subdomains:
                self._emit_progress(scan_id, 'Discovering subdomains...', 10)
                self._emit_log(scan_id, 'Starting subdomain discovery (DNS + CT + VirusTotal)', 'info')
                
                # Capture subdomain discoveries
                subdomains = crawler.discover_all_subdomains()
                
                # Store subdomains
                self.active_scans[scan_id]['discovered_subdomains'] = list(subdomains)
                
                # Emit each subdomain
                for subdomain in subdomains:
                    self._emit_log(scan_id, f'✓ Found subdomain: {subdomain}', 'success')
                
                self._emit_log(scan_id, f'Total subdomains found: {len(subdomains)}', 'info')
                self._emit_progress(scan_id, f'Found {len(subdomains)} subdomains', 20)
                
                # Now crawl
                self._emit_log(scan_id, 'Starting full discovery crawl...', 'info')
                urls_to_scan = crawler.run_full_discovery()
            else:
                self._emit_progress(scan_id, 'Crawling target...', 10)
                self._emit_log(scan_id, 'Starting URL crawl...', 'info')
                urls_to_scan = crawler.crawl(target_url)
            
            self.active_scans[scan_id]['urls_found'] = len(urls_to_scan)
            self._emit_progress(scan_id, f'Found {len(urls_to_scan)} URLs with parameters', 30)
            self._emit_log(scan_id, f'✓ Crawling complete: {len(urls_to_scan)} URLs with parameters', 'success')
            
            if not urls_to_scan:
                self._emit_progress(scan_id, 'No URLs with parameters found', 100)
                self._emit_log(scan_id, '⚠ No testable URLs found', 'warning')
                self.active_scans[scan_id]['status'] = 'completed'
                self._save_to_db(scan_id)
                return
            
            # Initialize scanner
            scanner = SQLScanner()
            
            # Scan URLs
            self._emit_log(scan_id, f'Starting SQL injection testing on {len(urls_to_scan)} URLs...', 'info')
            total_urls = len(urls_to_scan)
            
            for idx, url in enumerate(urls_to_scan, 1):
                if self.active_scans[scan_id]['status'] == 'stopped':
                    self._emit_log(scan_id, 'Scan stopped by user', 'warning')
                    break
                
                progress = 30 + int((idx / total_urls) * 60)
                self._emit_progress(scan_id, f'Testing {idx}/{total_urls}', progress)
                self._emit_log(scan_id, f'Testing: {url}', 'info')
                
                scanner.scan_url(url)
                self.active_scans[scan_id]['urls_scanned'] = idx
                
                # Update vulnerabilities
                self.active_scans[scan_id]['vulnerabilities'] = scanner.vulnerabilities
                
                if scanner.vulnerabilities and len(scanner.vulnerabilities) > len(self.active_scans[scan_id].get('vulnerabilities', [])):
                    vuln = scanner.vulnerabilities[-1]
                    self._emit_vulnerability(scan_id, vuln)
                    self._emit_log(scan_id, f'🚨 VULNERABILITY FOUND: {vuln["attack_type"]} on {vuln["parameter"]}', 'danger')
            
            # Generate report
            self._emit_progress(scan_id, 'Generating report...', 95)
            self._emit_log(scan_id, 'Generating final report...', 'info')
            
            reporter = Reporter(target_url)
            os.makedirs('reports', exist_ok=True)
            report_file = f'reports/scan_{scan_id}.txt'
            reporter.generate_txt_report(scanner.vulnerabilities, report_file)
            
            # Complete
            self.active_scans[scan_id]['status'] = 'completed'
            self.active_scans[scan_id]['completed_at'] = datetime.now().isoformat()
            self.active_scans[scan_id]['report_file'] = report_file
            self._emit_progress(scan_id, 'Scan completed!', 100)
            self._emit_log(scan_id, f'✓ Scan complete! Found {len(scanner.vulnerabilities)} vulnerabilities', 'success')
            
            # Save final state to database
            self._save_to_db(scan_id)
            
        except Exception as e:
            self.active_scans[scan_id]['status'] = 'error'
            self.active_scans[scan_id]['error'] = str(e)
            self._emit_progress(scan_id, f'Error: {str(e)}', 100)
            self._emit_log(scan_id, f'❌ Fatal error: {str(e)}', 'danger')
            self._save_to_db(scan_id)
    
    def _save_to_db(self, scan_id):
        """Save scan results to database"""
        if self.database and scan_id in self.active_scans:
            self.database.save_scan(self.active_scans[scan_id])
    
    def stop_scan(self, scan_id):
        """Stop a running scan"""
        if scan_id in self.active_scans:
            self.active_scans[scan_id]['status'] = 'stopped'
            self._emit_progress(scan_id, 'Scan stopped by user', 100)
            self._emit_log(scan_id, 'Scan stopped by user', 'warning')
            self._save_to_db(scan_id)
    
    def get_scan_status(self, scan_id):
        """Get current status of a scan"""
        # First check active scans
        if scan_id in self.active_scans:
            return self.active_scans[scan_id]
        
        # Then check database
        if self.database:
            return self.database.get_scan_info(scan_id)
        
        return None
    
    def _emit_progress(self, scan_id, message, progress):
        """Emit progress update via WebSocket"""
        self.active_scans[scan_id]['progress'] = progress
        if self.socketio:
            self.socketio.emit('scan_progress', {
                'scan_id': scan_id,
                'message': message,
                'progress': progress
            }, room=f'scan_{scan_id}')
    
    def _emit_vulnerability(self, scan_id, vulnerability):
        """Emit vulnerability found via WebSocket"""
        if self.socketio:
            self.socketio.emit('vulnerability_found', {
                'scan_id': scan_id,
                'vulnerability': vulnerability
            }, room=f'scan_{scan_id}')
