"""
NOA SQL Scanner - Vulnerability Detection Logic
"""

import re
import time
from config import ERROR_PATTERNS, TIME_BASED_THRESHOLD, Colors

class VulnerabilityDetector:
    def __init__(self):
        self.mysql_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in ERROR_PATTERNS['mysql']]
        self.postgresql_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in ERROR_PATTERNS['postgresql']]
    
    def detect_error_based(self, response_text, payload):
        """
        Detect SQL injection via error messages
        
        Returns: (vulnerable, db_type, matched_pattern, attack_type)
        """
        # Check MySQL errors
        for pattern in self.mysql_patterns:
            if pattern.search(response_text):
                match = pattern.search(response_text).group(0)
                return (True, 'MySQL', match, 'Error-Based')
        
        # Check PostgreSQL errors
        for pattern in self.postgresql_patterns:
            if pattern.search(response_text):
                match = pattern.search(response_text).group(0)
                return (True, 'PostgreSQL', match, 'Error-Based')
        
        return (False, None, None, None)
    
    def detect_boolean_based(self, response_true, response_false, baseline_response):
        """
        Detect SQL injection via boolean-based blind technique
        
        Compares response lengths and content differences
        """
        # Get response lengths
        len_true = len(response_true.text)
        len_false = len(response_false.text)
        len_baseline = len(baseline_response.text)
        
        # Check if true and false responses are different
        # but true response is similar to baseline
        if len_true != len_false:
            # True response should be similar to baseline
            true_diff = abs(len_true - len_baseline)
            false_diff = abs(len_false - len_baseline)
            
            # If true is closer to baseline than false, likely vulnerable
            if true_diff < false_diff and false_diff > 50:
                return (True, 'Boolean-Based', f"Length difference: True={len_true}, False={len_false}")
        
        # Check for content differences
        if response_true.status_code == 200 and response_false.status_code != 200:
            return (True, 'Boolean-Based', f"Status code difference: True=200, False={response_false.status_code}")
        
        return (False, None, None)
    
    def detect_time_based(self, response_time, baseline_time):
        """
        Detect SQL injection via time-based blind technique
        
        Checks if response time is significantly longer than baseline
        """
        time_diff = response_time - baseline_time
        
        # If response took longer than threshold, likely vulnerable
        if time_diff >= TIME_BASED_THRESHOLD:
            return (True, 'Time-Based', f"Delay detected: {time_diff:.2f} seconds")
        
        return (False, None, None)
    
    def detect_union_based(self, response_text, baseline_text, payload):
        """
        Detect SQL injection via UNION-based technique
        
        Looks for additional data in response that wasn't in baseline
        """
        # Check if response is significantly different from baseline
        len_diff = abs(len(response_text) - len(baseline_text))
        
        # UNION queries often return more data
        if len_diff > 100:
            # Check for common UNION success indicators
            union_indicators = [
                r'NULL',
                r'\d+\s*,\s*\d+',  # Numbers like "1, 2, 3"
                r'version\(\)',
                r'database\(\)',
                r'current_database',
            ]
            
            for indicator in union_indicators:
                if re.search(indicator, response_text, re.IGNORECASE):
                    return (True, 'UNION-Based', f"UNION indicator found: {indicator}")
        
        return (False, None, None)
    
    def analyze_response(self, response, payload, attack_type, baseline_response=None, response_time=None, baseline_time=None):
        """
        Analyze HTTP response for SQL injection vulnerability
        
        Returns: (vulnerable, db_type, evidence, attack_type)
        """
        if attack_type == 'error':
            return self.detect_error_based(response.text, payload)
        
        elif attack_type == 'boolean' and baseline_response:
            return self.detect_boolean_based(response, baseline_response[1], baseline_response[0])
        
        elif attack_type == 'time' and response_time and baseline_time:
            result = self.detect_time_based(response_time, baseline_time)
            if result[0]:
                return (True, 'MySQL/PostgreSQL', result[2], result[1])
            return (False, None, None, None)
        
        elif attack_type == 'union' and baseline_response:
            result = self.detect_union_based(response.text, baseline_response.text, payload)
            if result[0]:
                return (True, 'MySQL/PostgreSQL', result[2], result[1])
            return (False, None, None, None)
        
        return (False, None, None, None)
    
    def print_vulnerability(self, url, payload, db_type, evidence, attack_type, param_name=None):
        """Print vulnerability finding in real-time"""
        print(f"\n{Colors.FAIL}{'='*80}{Colors.ENDC}")
        print(f"{Colors.FAIL}🚨 SQL INJECTION VULNERABILITY DETECTED! 🚨{Colors.ENDC}")
        print(f"{Colors.FAIL}{'='*80}{Colors.ENDC}")
        print(f"{Colors.OKGREEN}[+] URL: {url}{Colors.ENDC}")
        if param_name:
            print(f"{Colors.OKGREEN}[+] Parameter: {param_name}{Colors.ENDC}")
        print(f"{Colors.OKGREEN}[+] Payload: {payload}{Colors.ENDC}")
        print(f"{Colors.OKGREEN}[+] Database: {db_type}{Colors.ENDC}")
        print(f"{Colors.OKGREEN}[+] Attack Type: {attack_type}{Colors.ENDC}")
        print(f"{Colors.OKGREEN}[+] Evidence: {evidence[:200]}...{Colors.ENDC}")
        print(f"{Colors.FAIL}{'='*80}{Colors.ENDC}\n")
