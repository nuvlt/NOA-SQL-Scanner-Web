"""
NOA SQL Scanner - Report Generation
"""

from datetime import datetime
from config import Colors

class Reporter:
    def __init__(self, target_url):
        self.target_url = target_url
        self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def generate_txt_report(self, vulnerabilities, output_file="sqli_report.txt"):
        """Generate detailed TXT report"""
        
        report_content = f"""
{'='*80}
NOA SQL SCANNER - VULNERABILITY SCAN REPORT
{'='*80}

Target URL: {self.target_url}
Scan Date: {self.timestamp}
Total Vulnerabilities Found: {len(vulnerabilities)}
Scanner Version: 1.9.0.3
Created by: Nüvit Onur Altaş

{'='*80}

"""
        
        if not vulnerabilities:
            report_content += """
✓ No SQL injection vulnerabilities detected.

Note: This does not guarantee the application is completely secure.
Additional manual testing is recommended.
"""
        else:
            for i, vuln in enumerate(vulnerabilities, 1):
                report_content += f"""
{'='*80}
VULNERABILITY #{i}
{'='*80}

[!] Severity: HIGH
[!] Type: SQL Injection - {vuln['attack_type']}

URL: {vuln['url']}
Parameter: {vuln['parameter']}
Database Type: {vuln['db_type']}
Attack Type: {vuln['attack_type']}

Payload Used:
{vuln['payload']}

Evidence:
{vuln['evidence'][:500]}

Recommendation:
- Use parameterized queries (prepared statements)
- Implement input validation and sanitization
- Apply principle of least privilege for database accounts
- Use Web Application Firewall (WAF)
- Regular security audits and penetration testing

"""
        
        report_content += f"""
{'='*80}
SCAN SUMMARY
{'='*80}

Total URLs Scanned: Multiple URLs processed
Vulnerabilities Detected: {len(vulnerabilities)}

Vulnerability Breakdown:
"""
        
        # Count by attack type
        attack_types = {}
        db_types = {}
        
        for vuln in vulnerabilities:
            attack_type = vuln['attack_type']
            db_type = vuln['db_type']
            
            attack_types[attack_type] = attack_types.get(attack_type, 0) + 1
            db_types[db_type] = db_types.get(db_type, 0) + 1
        
        for attack_type, count in attack_types.items():
            report_content += f"  - {attack_type}: {count}\n"
        
        report_content += f"\nDatabase Types Identified:\n"
        for db_type, count in db_types.items():
            report_content += f"  - {db_type}: {count}\n"
        
        report_content += f"""

{'='*80}
DISCLAIMER
{'='*80}

This scan was performed for authorized security testing purposes only.
Unauthorized testing of systems you do not own is illegal.

The scanner may produce false positives. Manual verification is recommended.
Always test findings in a controlled environment before reporting.

NOA SQL Scanner v1.9.0.3
Created by Nüvit Onur Altaş
https://github.com/yourusername/NOA-SQL-Scanner

{'='*80}
END OF REPORT
{'='*80}
"""
        
        # Write to file
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report_content)
            
            print(f"\n{Colors.OKGREEN}[+] Report saved to: {output_file}{Colors.ENDC}")
            return True
            
        except Exception as e:
            print(f"{Colors.FAIL}[-] Error saving report: {str(e)}{Colors.ENDC}")
            return False
    
    def print_summary(self, vulnerabilities, total_urls_scanned):
        """Print scan summary to console"""
        print(f"\n{Colors.HEADER}{'='*80}{Colors.ENDC}")
        print(f"{Colors.HEADER}SCAN COMPLETED{Colors.ENDC}")
        print(f"{Colors.HEADER}{'='*80}{Colors.ENDC}")
        print(f"{Colors.OKBLUE}Target: {self.target_url}{Colors.ENDC}")
        print(f"{Colors.OKBLUE}URLs Scanned: {total_urls_scanned}{Colors.ENDC}")
        print(f"{Colors.OKBLUE}Scan Time: {self.timestamp}{Colors.ENDC}")
        
        if vulnerabilities:
            print(f"{Colors.FAIL}Vulnerabilities Found: {len(vulnerabilities)}{Colors.ENDC}")
            print(f"\n{Colors.WARNING}⚠️  VULNERABILITIES DETECTED! ⚠️{Colors.ENDC}")
            
            # Group by attack type
            attack_types = {}
            for vuln in vulnerabilities:
                attack_type = vuln['attack_type']
                if attack_type not in attack_types:
                    attack_types[attack_type] = []
                attack_types[attack_type].append(vuln)
            
            print(f"\n{Colors.OKBLUE}Breakdown by Attack Type:{Colors.ENDC}")
            for attack_type, vulns in attack_types.items():
                print(f"{Colors.OKGREEN}  - {attack_type}: {len(vulns)} vulnerability(ies){Colors.ENDC}")
        else:
            print(f"{Colors.OKGREEN}Vulnerabilities Found: 0{Colors.ENDC}")
            print(f"\n{Colors.OKGREEN}✓ No SQL injection vulnerabilities detected{Colors.ENDC}")
        
        print(f"{Colors.HEADER}{'='*80}{Colors.ENDC}\n")
