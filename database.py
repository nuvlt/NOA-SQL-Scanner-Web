"""
NOA SQL Scanner Web - Database Module (Updated with thread safety)
"""

import sqlite3
import json
from datetime import datetime
import os
import threading

class Database:
    def __init__(self, db_path='noa_scanner.db'):
        self.db_path = db_path
        self.lock = threading.Lock()  # Thread-safe yapmak için
        self.init_database()
    
    def get_connection(self):
        """Get database connection with timeout"""
        conn = sqlite3.connect(self.db_path, timeout=30.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        # WAL mode for better concurrency
        conn.execute('PRAGMA journal_mode=WAL')
        return conn
    
    def init_database(self):
        """Initialize database tables"""
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Scans table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS scans (
                    scan_id TEXT PRIMARY KEY,
                    target_url TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    status TEXT NOT NULL,
                    enable_subdomains INTEGER,
                    enable_deep INTEGER,
                    urls_found INTEGER,
                    urls_scanned INTEGER,
                    vulnerabilities_count INTEGER,
                    report_file TEXT
                )
            ''')
            
            # Vulnerabilities table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS vulnerabilities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scan_id TEXT NOT NULL,
                    url TEXT NOT NULL,
                    parameter TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    db_type TEXT NOT NULL,
                    attack_type TEXT NOT NULL,
                    evidence TEXT,
                    found_at TEXT NOT NULL,
                    FOREIGN KEY (scan_id) REFERENCES scans(scan_id)
                )
            ''')
            
            # Dork results table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS dork_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    dork_query TEXT NOT NULL,
                    search_engine TEXT NOT NULL,
                    found_urls TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            ''')
            
            conn.commit()
            conn.close()
    
    def save_scan(self, scan_info):
        """Save scan information with thread safety"""
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            try:
                # Check if scan already exists
                cursor.execute('SELECT scan_id FROM scans WHERE scan_id = ?', (scan_info['scan_id'],))
                exists = cursor.fetchone()
                
                if exists:
                    # Update existing scan
                    cursor.execute('''
                        UPDATE scans SET 
                        completed_at = ?,
                        status = ?,
                        urls_found = ?,
                        urls_scanned = ?,
                        vulnerabilities_count = ?,
                        report_file = ?
                        WHERE scan_id = ?
                    ''', (
                        scan_info.get('completed_at'),
                        scan_info['status'],
                        scan_info.get('urls_found', 0),
                        scan_info.get('urls_scanned', 0),
                        len(scan_info.get('vulnerabilities', [])),
                        scan_info.get('report_file'),
                        scan_info['scan_id']
                    ))
                else:
                    # Insert new scan
                    cursor.execute('''
                        INSERT INTO scans VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        scan_info['scan_id'],
                        scan_info['target_url'],
                        scan_info['started_at'],
                        scan_info.get('completed_at'),
                        scan_info['status'],
                        1 if scan_info.get('enable_subdomains') else 0,
                        1 if scan_info.get('enable_deep') else 0,
                        scan_info.get('urls_found', 0),
                        scan_info.get('urls_scanned', 0),
                        len(scan_info.get('vulnerabilities', [])),
                        scan_info.get('report_file')
                    ))
                
                # Delete old vulnerabilities for this scan
                cursor.execute('DELETE FROM vulnerabilities WHERE scan_id = ?', (scan_info['scan_id'],))
                
                # Save vulnerabilities
                for vuln in scan_info.get('vulnerabilities', []):
                    cursor.execute('''
                        INSERT INTO vulnerabilities 
                        (scan_id, url, parameter, payload, db_type, attack_type, evidence, found_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        scan_info['scan_id'],
                        vuln['url'],
                        vuln['parameter'],
                        vuln['payload'],
                        vuln['db_type'],
                        vuln['attack_type'],
                        vuln['evidence'],
                        datetime.now().isoformat()
                    ))
                
                conn.commit()
            except Exception as e:
                conn.rollback()
                print(f"[!] Database error in save_scan: {e}")
                raise
            finally:
                conn.close()
    
    def save_dork_results(self, dork_query, search_engine, urls):
        """Save dork search results with thread safety"""
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            try:
                cursor.execute('''
                    INSERT INTO dork_results (dork_query, search_engine, found_urls, created_at)
                    VALUES (?, ?, ?, ?)
                ''', (
                    dork_query,
                    search_engine,
                    json.dumps(urls),
                    datetime.now().isoformat()
                ))
                
                dork_id = cursor.lastrowid
                conn.commit()
                return dork_id
            except Exception as e:
                conn.rollback()
                print(f"[!] Database error in save_dork_results: {e}")
                raise
            finally:
                conn.close()
    
    # Diğer fonksiyonlar aynı kalacak, sadece get_connection kullanacaklar
    
    def get_scan_info(self, scan_id):
        """Get scan information"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM scans WHERE scan_id = ?', (scan_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None
    
    def get_recent_scans(self, limit=10):
        """Get recent scans"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM scans 
            ORDER BY started_at DESC 
            LIMIT ?
        ''', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_all_scans(self):
        """Get all scans"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM scans ORDER BY started_at DESC')
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_vulnerabilities(self, scan_id):
        """Get vulnerabilities for a scan"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM vulnerabilities 
            WHERE scan_id = ?
            ORDER BY found_at DESC
        ''', (scan_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_statistics(self):
        """Get overall statistics"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Total scans
        cursor.execute('SELECT COUNT(*) as count FROM scans')
        total_scans = cursor.fetchone()['count']
        
        # Total vulnerabilities
        cursor.execute('SELECT COUNT(*) as count FROM vulnerabilities')
        total_vulns = cursor.fetchone()['count']
        
        # Scans by status
        cursor.execute('''
            SELECT status, COUNT(*) as count 
            FROM scans 
            GROUP BY status
        ''')
        status_counts = {row['status']: row['count'] for row in cursor.fetchall()}
        
        # Vulnerabilities by type
        cursor.execute('''
            SELECT attack_type, COUNT(*) as count 
            FROM vulnerabilities 
            GROUP BY attack_type
        ''')
        vuln_types = {row['attack_type']: row['count'] for row in cursor.fetchall()}
        
        conn.close()
        
        return {
            'total_scans': total_scans,
            'total_vulnerabilities': total_vulns,
            'status_counts': status_counts,
            'vulnerability_types': vuln_types
        }
    
    def get_scan_details(self, scan_id):
        """Get detailed scan information"""
        scan_info = self.get_scan_info(scan_id)
        if scan_info:
            scan_info['vulnerabilities'] = self.get_vulnerabilities(scan_id)
        return scan_info
    
    def get_scan_status(self, scan_id):
        """Get scan status for API"""
        return self.get_scan_info(scan_id)
