"""
NOA SQL Scanner - URL Crawler & Subdomain Discovery
"""

import re
import time
import requests
import dns.resolver
from urllib.parse import urljoin, urlparse, parse_qs, urlencode
from bs4 import BeautifulSoup
from collections import deque
import random
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
        """Extract base domain from subdomain"""
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
                dns.resolver.resolve(full_domain, 'A')
                found_subdomains.add(full_domain)
                print(f"{Colors.OKGREEN}[+] Found subdomain: {full_domain}{Colors.ENDC}")
            except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.NoNameservers):
                pass
            except Exception:
                pass
        
        self.subdomains.update(found_subdomains)
        return found_subdomains
    
    def discover_subdomains_crt(self):
        """Discover subdomains via Certificate Transparency logs"""
        print(f"{Colors.OKCYAN}[*] Checking Certificate Transparency logs...{Colors.ENDC}")
        found_subdomains = set()
        
        try:
            url = f"https://crt.sh/?q=%.{self.base_domain}&output=json"
            response = requests.get(url, timeout=REQUEST_TIMEOUT)
            
            if response.status_code == 200:
                data = response.json()
                for entry in data:
                    name = entry.get('name_value', '')
                    # Handle wildcard and multiple domains
                    domains = name.split('\n')
                    for domain in domains:
                        domain = domain.strip().replace('*.', '')
                        if domain.endswith(self.base_domain) and domain != self.base_domain:
                            found_subdomains.add(domain)
                            print(f"{Colors.OKGREEN}[+] Found subdomain (crt.sh): {domain}{Colors.ENDC}")
        except Exception as e:
            print(f"{Colors.WARNING}[-] Certificate Transparency check failed: {str(e)}{Colors.ENDC}")
        
        self.subdomains.update(found_subdomains)
        return found_subdomains
    
    def discover_all_subdomains(self):
        """Discover subdomains using all methods"""
        # DNS brute-force
        dns_subs = self.discover_subdomains_dns()
        time.sleep(1)
        
        # Certificate Transparency
        crt_subs = self.discover_subdomains_crt()
        
        all_subdomains = dns_subs.union(crt_subs)
        print(f"{Colors.OKBLUE}[*] Total subdomains found: {len(all_subdomains)}{Colors.ENDC}")
        
        return all_subdomains
    
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
        
        queue = deque([(start_url, 0)])  # (url, depth)
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
                    self.urls_with_params.append(current_url)
                    print(f"{Colors.OKGREEN}[+] Found URL with params: {current_url}{Colors.ENDC}")
                
                # Extract and queue new links
                if 'text/html' in response.headers.get('Content-Type', ''):
                    links = self.extract_links(response.text, current_url)
                    for link in links:
                        if link not in self.visited_urls:
                            queue.append((link, depth + 1))
                
                print(f"{Colors.OKBLUE}[*] Crawled: {len(self.visited_urls)}/{MAX_URLS} URLs{Colors.ENDC}", end='\r')
                
            except requests.exceptions.RequestException:
                pass
            except Exception as e:
                print(f"{Colors.WARNING}[-] Error crawling {current_url}: {str(e)}{Colors.ENDC}")
        
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
        
        # Crawl each domain
        for domain in all_domains[:10]:  # Limit to first 10 domains to avoid too much crawling
            base_url = f"https://{domain}"
            print(f"\n{Colors.HEADER}{'='*60}{Colors.ENDC}")
            print(f"{Colors.HEADER}[*] Crawling domain: {domain}{Colors.ENDC}")
            print(f"{Colors.HEADER}{'='*60}{Colors.ENDC}")
            
            urls = self.crawl(base_url)
            all_urls.extend(urls)
            
            if len(all_urls) >= MAX_URLS:
                break
        
        return all_urls
