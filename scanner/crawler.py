"""
NOA SQL Scanner - URL Crawler & Subdomain Discovery (Enhanced)
"""

import re
import time
import requests
import dns.resolver
from urllib.parse import urljoin, urlparse, parse_qs, urlencode
from bs4 import BeautifulSoup
from collections import deque
import random
import tldextract

try:
    from .config import (
        SUBDOMAIN_WORDLIST, USER_AGENTS, MAX_URLS, 
        MAX_CRAWL_DEPTH, RATE_LIMIT_DELAY, REQUEST_TIMEOUT, Colors
    )
except ImportError:
    from config import (
        SUBDOMAIN_WORDLIST, USER_AGENTS, MAX_URLS, 
        MAX_CRAWL_DEPTH, RATE_LIMIT_DELAY, REQUEST_TIMEOUT, Colors
    )

class Crawler:
    def __init__(self, target_url):
        self.target_url = target_url
        self.domain = urlparse(target_url).netloc
        self.base_domain = self._extract_base_domain(self.domain)
        self.visited_urls = set()
        self.urls_with_params = []
        self.subdomains = set()
        
    def _extract_base_domain(self, domain):
        """Extract base domain from subdomain using tldextract"""
        try:
            ext = tldextract.extract(domain)
            if ext.domain and ext.suffix:
                base = f"{ext.domain}.{ext.suffix}"
                print(f"{Colors.OKBLUE}[*] Base domain: {base}{Colors.ENDC}")
                return base
            return domain
        except Exception as e:
            print(f"{Colors.WARNING}[-] Error extracting base domain: {e}{Colors.ENDC}")
            # Fallback
            parts = domain.split('.')
            if len(parts) >= 2:
                return '.'.join(parts[-2:])
            return domain
    
    def _get_random_headers(self):
        """Generate random headers for WAF bypass"""
        return {
            'User-Agent': random.choice(USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
            'Referer': self.target_url,
            'X-Forwarded-For': f'{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}'
        }
    
    def discover_subdomains_dns(self):
        """Discover subdomains via DNS brute-force"""
        print(f"{Colors.OKCYAN}[*] Starting DNS subdomain enumeration...{Colors.ENDC}")
        found_subdomains = set()
        
        for subdomain in SUBDOMAIN_WORDLIST:
            try:
                full_domain = f"{subdomain}.{self.base_domain}"
                answers = dns.resolver.resolve(full_domain, 'A')
                
                # Verify it's not the same as base domain
                if full_domain != self.base_domain:
                    found_subdomains.add(full_domain)
                    print(f"{Colors.OKGREEN}[+] Found subdomain (DNS): {full_domain}{Colors.ENDC}")
                    
            except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.NoNameservers, dns.resolver.Timeout):
                pass
            except Exception as e:
                pass
        
        self.subdomains.update(found_subdomains)
        return found_subdomains
    
    def discover_subdomains_crt(self):
        """Discover subdomains via Certificate Transparency logs"""
        print(f"{Colors.OKCYAN}[*] Checking Certificate Transparency logs...{Colors.ENDC}")
        found_subdomains = set()
        
        try:
            url = f"https://crt.sh/?q=%.{self.base_domain}&output=json"
            response = requests.get(url, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                print(f"{Colors.OKBLUE}[*] CT logs returned {len(data)} certificates{Colors.ENDC}")
                
                for entry in data:
                    name = entry.get('name_value', '')
                    # Handle wildcard and multiple domains
                    domains = name.split('\n')
                    
                    for domain in domains:
                        domain = domain.strip().replace('*.', '').lower()
                        
                        # Verify it's a valid subdomain
                        if domain.endswith(self.base_domain) and domain != self.base_domain:
                            # Check if domain is valid (no special chars)
                            if re.match(r'^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?(\.[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?)*$', domain):
                                if domain not in found_subdomains:
                                    found_subdomains.add(domain)
                                    print(f"{Colors.OKGREEN}[+] Found subdomain (CT): {domain}{Colors.ENDC}")
                                    
        except Exception as e:
            print(f"{Colors.WARNING}[-] Certificate Transparency check failed: {str(e)}{Colors.ENDC}")
        
        self.subdomains.update(found_subdomains)
        return found_subdomains
    
    def discover_subdomains_virustotal(self):
        """Discover subdomains via VirusTotal (passive)"""
        print(f"{Colors.OKCYAN}[*] Checking VirusTotal for subdomains...{Colors.ENDC}")
        found_subdomains = set()
        
        try:
            # VirusTotal public API (no key needed for basic search)
            url = f"https://www.virustotal.com/ui/domains/{self.base_domain}/subdomains?limit=40"
            
            headers = {
                'User-Agent': random.choice(USER_AGENTS),
                'Accept': 'application/json'
            }
            
            response = requests.get(url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                subdomains_data = data.get('data', [])
                
                for item in subdomains_data:
                    subdomain = item.get('id', '').lower()
                    if subdomain and subdomain != self.base_domain:
                        found_subdomains.add(subdomain)
                        print(f"{Colors.OKGREEN}[+] Found subdomain (VT): {subdomain}{Colors.ENDC}")
                        
        except Exception as e:
            print(f"{Colors.WARNING}[-] VirusTotal check failed: {str(e)}{Colors.ENDC}")
        
        self.subdomains.update(found_subdomains)
        return found_subdomains
    
    def discover_all_subdomains(self):
        """Discover subdomains using all methods"""
        all_found = set()
        
        # 1. Certificate Transparency (en güvenilir)
        print(f"\n{Colors.HEADER}[*] Method 1: Certificate Transparency{Colors.ENDC}")
        crt_subs = self.discover_subdomains_crt()
        all_found.update(crt_subs)
        time.sleep(2)
        
        # 2. DNS Brute-force
        print(f"\n{Colors.HEADER}[*] Method 2: DNS Brute-force{Colors.ENDC}")
        dns_subs = self.discover_subdomains_dns()
        all_found.update(dns_subs)
        time.sleep(2)
        
        # 3. VirusTotal
        print(f"\n{Colors.HEADER}[*] Method 3: VirusTotal{Colors.ENDC}")
        vt_subs = self.discover_subdomains_virustotal()
        all_found.update(vt_subs)
        
        # Verify all subdomains are reachable
        print(f"\n{Colors.HEADER}[*] Verifying subdomains...{Colors.ENDC}")
        verified_subdomains = set()
        
        for subdomain in all_found:
            try:
                # Quick HTTP check
                for scheme in ['https', 'http']:
                    test_url = f"{scheme}://{subdomain}"
                    try:
                        response = requests.head(
                            test_url,
                            headers=self._get_random_headers(),
                            timeout=5,
                            allow_redirects=True,
                            verify=False
                        )
                        verified_subdomains.add(subdomain)
                        print(f"{Colors.OKGREEN}[+] Verified: {subdomain} ({scheme}){Colors.ENDC}")
                        break
                    except:
                        continue
            except:
                pass
        
        print(f"\n{Colors.OKBLUE}[*] Total subdomains found: {len(all_found)}{Colors.ENDC}")
        print(f"{Colors.OKBLUE}[*] Verified & reachable: {len(verified_subdomains)}{Colors.ENDC}")
        
        # Show all unique subdomains
        if verified_subdomains:
            print(f"\n{Colors.HEADER}[*] Verified Subdomains:{Colors.ENDC}")
            for sub in sorted(verified_subdomains):
                print(f"  - {sub}")
        
        self.subdomains = verified_subdomains
        return verified_subdomains
    
    def extract_links(self, html_content, base_url):
        """Extract all links from HTML content"""
        links = set()
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract from <a> tags
            for tag in soup.find_all('a', href=True):
                link = urljoin(base_url, tag['href'])
                links.add(link)
            
            # Extract from <form> tags
            for form in soup.find_all('form', action=True):
                link = urljoin(base_url, form['action'])
                links.add(link)
                
        except Exception as e:
            print(f"{Colors.WARNING}[-] Error parsing HTML: {str(e)}{Colors.ENDC}")
        
        return links
    
    def has_parameters(self, url):
        """Check if URL has GET parameters"""
        parsed = urlparse(url)
        return bool(parse_qs(parsed.query))
    
    def crawl(self, start_url, max_depth=MAX_CRAWL_DEPTH):
        """Crawl website and collect URLs with parameters"""
        print(f"{Colors.OKCYAN}[*] Starting crawl from: {start_url}{Colors.ENDC}")
        
        queue = deque([(start_url, 0)])
        domain = urlparse(start_url).netloc
        
        while queue and len(self.visited_urls) < MAX_URLS:
            current_url, depth = queue.popleft()
            
            if current_url in self.visited_urls or depth > max_depth:
                continue
            
            # Only crawl same domain
            if urlparse(current_url).netloc != domain:
                continue
            
            try:
                time.sleep(RATE_LIMIT_DELAY)
                
                response = requests.get(
                    current_url,
                    headers=self._get_random_headers(),
                    timeout=REQUEST_TIMEOUT,
                    allow_redirects=True,
                    verify=False
                )
                
                self.visited_urls.add(current_url)
                
                # If URL has parameters, add to testing list
                if self.has_parameters(current_url):
                    if current_url not in self.urls_with_params:
                        self.urls_with_params.append(current_url)
                        print(f"{Colors.OKGREEN}[+] Found URL with params: {current_url}{Colors.ENDC}")
                
                # Extract and queue new links
                if 'text/html' in response.headers.get('Content-Type', ''):
                    links = self.extract_links(response.text, current_url)
                    for link in links:
                        if link not in self.visited_urls:
                            queue.append((link, depth + 1))
                
                print(f"{Colors.OKBLUE}[*] Crawled: {len(self.visited_urls)}/{MAX_URLS} URLs (Found {len(self.urls_with_params)} with params){Colors.ENDC}", end='\r')
                
            except requests.exceptions.RequestException:
                pass
            except Exception as e:
                pass
        
        print(f"\n{Colors.OKBLUE}[*] Crawling complete. Found {len(self.urls_with_params)} URLs with parameters{Colors.ENDC}")
        return self.urls_with_params
    
    def run_full_discovery(self):
        """Run complete subdomain discovery and crawling"""
        all_urls = []
        
        # Discover subdomains
        subdomains = self.discover_all_subdomains()
        
        # Add main domain to list
        all_domains = [self.domain]
        all_domains.extend(list(subdomains))
        
        # Remove duplicates and sort
        all_domains = sorted(list(set(all_domains)))
        
        print(f"\n{Colors.HEADER}{'='*60}{Colors.ENDC}")
        print(f"{Colors.HEADER}[*] Will scan {len(all_domains)} domains{Colors.ENDC}")
        print(f"{Colors.HEADER}{'='*60}{Colors.ENDC}")
        
        # Crawl each domain
        for idx, domain in enumerate(all_domains[:15], 1):  # Max 15 domain
            # Try both http and https
            for scheme in ['https', 'http']:
                base_url = f"{scheme}://{domain}"
                
                print(f"\n{Colors.HEADER}{'='*60}{Colors.ENDC}")
                print(f"{Colors.HEADER}[*] [{idx}/{min(len(all_domains), 15)}] Crawling: {base_url}{Colors.ENDC}")
                print(f"{Colors.HEADER}{'='*60}{Colors.ENDC}")
                
                try:
                    urls = self.crawl(base_url)
                    all_urls.extend(urls)
                    
                    if urls:
                        break  # If found URLs, don't try other scheme
                        
                except Exception as e:
                    print(f"{Colors.WARNING}[-] Error crawling {base_url}: {e}{Colors.ENDC}")
                    continue
            
            if len(all_urls) >= MAX_URLS:
                break
        
        # Remove duplicates
        all_urls = list(set(all_urls))
        
        print(f"\n{Colors.HEADER}{'='*60}{Colors.ENDC}")
        print(f"{Colors.OKGREEN}[+] Total unique URLs with parameters: {len(all_urls)}{Colors.ENDC}")
        print(f"{Colors.HEADER}{'='*60}{Colors.ENDC}")
        
        return all_urls[:MAX_URLS]
