"""
SQL Scanner - Main SQL Injection Testing Engine
"""

import time
import requests
import random
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from payloads import get_all_payloads
from detector import VulnerabilityDetector
from config import (
    USER_AGENTS, RATE_LIMIT_DELAY, REQUEST_TIMEOUT, Colors
)
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class SQLScanner:
    def __init__(self):
        self.detector = VulnerabilityDetector()
        self.vulnerabilities = []
        self.payloads = get_all_payloads('both')
    
    def _get_random_headers(self):
        """Generate random headers for WAF bypass"""
        return {
            'User-Agent': random.choice(USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'X-Forwarded-For': f'{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}',
            'X-Originating-IP': f'{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}',
            'X-Remote-IP': f'{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}',
            'X-Remote-Addr': f'{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}'
        }
    
    def _inject_payload(self, url, param, payload):
        """Inject payload into specific parameter"""
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        
        # Inject payload into the parameter
        if param in params:
            params[param] = [payload]
        
        # Rebuild URL
        new_query = urlencode(params, doseq=True)
        injected_url = urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            new_query,
            parsed.fragment
        ))
        
        return injected_url
    
    def _make_request(self, url):
        """Make HTTP request with error handling"""
        try:
            time.sleep(RATE_LIMIT_DELAY)
            start_time = time.time()
            
            response = requests.get(
                url,
                headers=self._get_random_headers(),
                timeout=REQUEST_TIMEOUT,
                allow_redirects=True,
                verify=False
            )
            
            elapsed_time = time.time() - start_time
            return response, elapsed_time
            
        except requests.exceptions.Timeout:
            return None, REQUEST_TIMEOUT
        except requests.exceptions.RequestException as e:
            print(f"{Colors.WARNING}[-] Request failed: {str(e)}{Colors.ENDC}")
            return None, 0
    
    def test_error_based(self, url, param):
        """Test for error-based SQL injection"""
        print(f"{Colors.OKCYAN}[*] Testing error-based injection on parameter: {param}{Colors.ENDC}")
        
        for payload in self.payloads['error'][:15]:  # Test first 15 payloads
            injected_url = self._inject_payload(url, param, payload)
            response, _ = self._make_request(injected_url)
            
            if response:
                vulnerable, db_type, evidence, attack_type = self.detector.analyze_response(
                    response, payload, 'error'
                )
                
                if vulnerable:
                    vuln_info = {
                        'url': url,
                        'parameter': param,
                        'payload': payload,
                        'db_type': db_type,
                        'attack_type': attack_type,
                        'evidence': evidence
                    }
                    self.vulnerabilities.append(vuln_info)
                    self.detector.print_vulnerability(url, payload, db_type, evidence, attack_type, param)
                    return True
        
        return False
    
    def test_boolean_based(self, url, param):
        """Test for boolean-based blind SQL injection"""
        print(f"{Colors.OKCYAN}[*] Testing boolean-based injection on parameter: {param}{Colors.ENDC}")
        
        # Get baseline response
        baseline_response, _ = self._make_request(url)
        if not baseline_response:
            return False
        
        for true_payload, false_payload in self.payloads['boolean'][:5]:  # Test first 5 pairs
            # Test TRUE condition
            true_url = self._inject_payload(url, param, true_payload)
            true_response, _ = self._make_request(true_url)
            
            if not true_response:
                continue
            
            # Test FALSE condition
            false_url = self._inject_payload(url, param, false_payload)
            false_response, _ = self._make_request(false_url)
            
            if not false_response:
                continue
            
            # Analyze responses
            vulnerable, attack_type, evidence = self.detector.detect_boolean_based(
                true_response, false_response, baseline_response
            )
            
            if vulnerable:
                vuln_info = {
                    'url': url,
                    'parameter': param,
                    'payload': f"TRUE: {true_payload} | FALSE: {false_payload}",
                    'db_type': 'MySQL/PostgreSQL',
                    'attack_type': attack_type,
                    'evidence': evidence
                }
                self.vulnerabilities.append(vuln_info)
                self.detector.print_vulnerability(
                    url, f"TRUE: {true_payload} | FALSE: {false_payload}", 
                    'MySQL/PostgreSQL', evidence, attack_type, param
                )
                return True
        
        return False
    
    def test_time_based(self, url, param):
        """Test for time-based blind SQL injection"""
        print(f"{Colors.OKCYAN}[*] Testing time-based injection on parameter: {param}{Colors.ENDC}")
        
        # Get baseline response time
        _, baseline_time = self._make_request(url)
        
        for payload in self.payloads['time'][:8]:  # Test first 8 payloads
            injected_url = self._inject_payload(url, param, payload)
            response, response_time = self._make_request(injected_url)
            
            if response:
                vulnerable, db_type, evidence, attack_type = self.detector.analyze_response(
                    response, payload, 'time',
                    response_time=response_time,
                    baseline_time=baseline_time
                )
                
                if vulnerable:
                    vuln_info = {
                        'url': url,
                        'parameter': param,
                        'payload': payload,
                        'db_type': db_type,
                        'attack_type': attack_type,
                        'evidence': evidence
                    }
                    self.vulnerabilities.append(vuln_info)
                    self.detector.print_vulnerability(url, payload, db_type, evidence, attack_type, param)
                    return True
        
        return False
    
    def test_union_based(self, url, param):
        """Test for UNION-based SQL injection"""
        print(f"{Colors.OKCYAN}[*] Testing UNION-based injection on parameter: {param}{Colors.ENDC}")
        
        # Get baseline response
        baseline_response, _ = self._make_request(url)
        if not baseline_response:
            return False
        
        for payload in self.payloads['union'][:10]:  # Test first 10 payloads
            injected_url = self._inject_payload(url, param, payload)
            response, _ = self._make_request(injected_url)
            
            if response:
                vulnerable, db_type, evidence, attack_type = self.detector.analyze_response(
                    response, payload, 'union',
                    baseline_response=baseline_response
                )
                
                if vulnerable:
                    vuln_info = {
                        'url': url,
                        'parameter': param,
                        'payload': payload,
                        'db_type': db_type,
                        'attack_type': attack_type,
                        'evidence': evidence
                    }
                    self.vulnerabilities.append(vuln_info)
                    self.detector.print_vulnerability(url, payload, db_type, evidence, attack_type, param)
                    return True
        
        return False
    
    def scan_url(self, url):
        """Scan a single URL for SQL injection vulnerabilities"""
        print(f"\n{Colors.HEADER}{'='*80}{Colors.ENDC}")
        print(f"{Colors.HEADER}[*] Scanning URL: {url}{Colors.ENDC}")
        print(f"{Colors.HEADER}{'='*80}{Colors.ENDC}")
        
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        
        if not params:
            print(f"{Colors.WARNING}[-] No parameters found in URL{Colors.ENDC}")
            return
        
        for param in params.keys():
            print(f"\n{Colors.OKBLUE}[*] Testing parameter: {param}{Colors.ENDC}")
            
            # Test different injection types
            # Error-based (fastest, most reliable)
            if self.test_error_based(url, param):
                continue  # Skip other tests if already found vulnerable
            
            # Boolean-based (slower but reliable)
            if self.test_boolean_based(url, param):
                continue
            
            # UNION-based
            if self.test_union_based(url, param):
                continue
            
            # Time-based (slowest, last resort)
            if self.test_time_based(url, param):
                continue
            
            print(f"{Colors.OKGREEN}[+] Parameter '{param}' appears safe{Colors.ENDC}")
    
    def scan_multiple_urls(self, urls):
        """Scan multiple URLs"""
        print(f"\n{Colors.HEADER}{'='*80}{Colors.ENDC}")
        print(f"{Colors.HEADER}[*] Starting SQL Injection scan on {len(urls)} URLs{Colors.ENDC}")
        print(f"{Colors.HEADER}{'='*80}{Colors.ENDC}")
        
        for i, url in enumerate(urls, 1):
            print(f"\n{Colors.OKCYAN}[*] Progress: {i}/{len(urls)}{Colors.ENDC}")
            self.scan_url(url)
        
        return self.vulnerabilities
