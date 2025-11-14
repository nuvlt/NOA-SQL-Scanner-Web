"""
NOA SQL Scanner - Working Dork Engine
Uses multiple proven methods to get results
"""

import requests
from bs4 import BeautifulSoup
import time
import random
from urllib.parse import quote_plus, unquote
import re
import json

class DorkEngine:
    def __init__(self):
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0',
        ]
        self.session = requests.Session()
        # Disable SSL verification for some sites
        self.session.verify = False
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    def get_realistic_headers(self, referer=None):
        """Generate very realistic browser headers"""
        headers = {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,tr;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none' if not referer else 'same-origin',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
        }
        
        if referer:
            headers['Referer'] = referer
        
        return headers


class DuckDuckGoAPIDork(DorkEngine):
    """DuckDuckGo Instant Answer API - Çalışır garantili!"""
    def __init__(self):
        super().__init__()
        self.base_url = "https://api.duckduckgo.com/"
    
    def search(self, query, max_results=50):
        urls = []
        
        print(f"[*] Searching DuckDuckGo API: {query}")
        
        try:
            params = {
                'q': query,
                'format': 'json',
                'no_html': '1',
                'skip_disambig': '1'
            }
            
            response = self.session.get(
                self.base_url,
                params=params,
                headers=self.get_realistic_headers(),
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Extract URLs from RelatedTopics
                for topic in data.get('RelatedTopics', []):
                    if isinstance(topic, dict) and 'FirstURL' in topic:
                        url = topic['FirstURL']
                        if self._is_valid_url(url):
                            urls.append(url)
                            print(f"[+] Found: {url}")
                    elif isinstance(topic, dict) and 'Topics' in topic:
                        for subtopic in topic['Topics']:
                            if 'FirstURL' in subtopic:
                                url = subtopic['FirstURL']
                                if self._is_valid_url(url):
                                    urls.append(url)
                                    print(f"[+] Found: {url}")
                
                # Also check AbstractURL
                if data.get('AbstractURL'):
                    url = data['AbstractURL']
                    if self._is_valid_url(url):
                        urls.append(url)
                        print(f"[+] Found: {url}")
                
                print(f"[*] Found {len(urls)} URLs from DuckDuckGo API")
            else:
                print(f"[!] HTTP {response.status_code}")
                
        except Exception as e:
            print(f"[-] DuckDuckGo API error: {e}")
        
        return urls[:max_results]
    
    def _is_valid_url(self, url):
        if not url or not url.startswith('http'):
            return False
        exclude = ['duckduckgo', 'google.com', 'youtube.com', 'wikipedia.org']
        for domain in exclude:
            if domain in url.lower():
                return False
        return '?' in url


class BraveDork(DorkEngine):
    """Brave Search - Rate limit çok düşük"""
    def __init__(self):
        super().__init__()
        self.base_url = "https://search.brave.com/search"
    
    def search(self, query, max_results=50):
        urls = []
        num_pages = min((max_results // 20) + 1, 3)
        
        print(f"[*] Searching Brave: {query}")
        
        for page in range(num_pages):
            try:
                params = {
                    'q': query,
                    'offset': page * 20,
                    'source': 'web'
                }
                
                headers = self.get_realistic_headers('https://search.brave.com/')
                
                response = self.session.get(
                    self.base_url,
                    params=params,
                    headers=headers,
                    timeout=15
                )
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Brave uses specific result classes
                    found_any = False
                    
                    # Strategy 1: snippet-url class
                    for result in soup.find_all('a', {'class': 'result-header'}):
                        href = result.get('href')
                        if href and self._is_valid_url(href):
                            urls.append(href)
                            found_any = True
                            print(f"[+] Found: {href}")
                    
                    # Strategy 2: All external links
                    if not found_any:
                        for link in soup.find_all('a', href=True):
                            href = link['href']
                            if href.startswith('http') and self._is_valid_url(href):
                                urls.append(href)
                                found_any = True
                                print(f"[+] Found: {href}")
                    
                    if not found_any:
                        print(f"[*] No results on page {page + 1}")
                        break
                    
                    print(f"[*] Page {page + 1}: Found {len([u for u in urls if u])} URLs so far")
                    time.sleep(random.uniform(3, 5))
                else:
                    print(f"[!] HTTP {response.status_code}")
                    break
                    
            except Exception as e:
                print(f"[-] Brave error: {e}")
                break
        
        urls = list(set(urls))
        print(f"[*] Total: {len(urls)} URLs from Brave")
        return urls[:max_results]
    
    def _is_valid_url(self, url):
        if not url.startswith('http'):
            return False
        exclude = ['brave.com', 'google.com', 'youtube.com']
        for domain in exclude:
            if domain in url.lower():
                return False
        return '?' in url


class StartpageDork(DorkEngine):
    """Startpage - Google sonuçları anonim olarak"""
    def __init__(self):
        super().__init__()
        self.base_url = "https://www.startpage.com/sp/search"
    
    def search(self, query, max_results=50):
        urls = []
        num_pages = min((max_results // 10) + 1, 5)
        
        print(f"[*] Searching Startpage: {query}")
        
        for page in range(num_pages):
            try:
                params = {
                    'query': query,
                    'page': page + 1,
                    'cat': 'web',
                    'language': 'english'
                }
                
                headers = self.get_realistic_headers('https://www.startpage.com/')
                
                response = self.session.get(
                    self.base_url,
                    params=params,
                    headers=headers,
                    timeout=15
                )
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    found_any = False
                    
                    # Extract from result URLs
                    for result in soup.find_all('a', {'class': 'w-gl__result-url'}):
                        href = result.get('href')
                        if href and self._is_valid_url(href):
                            urls.append(href)
                            found_any = True
                            print(f"[+] Found: {href}")
                    
                    # Alternative: h3 > a links
                    if not found_any:
                        for result in soup.select('h3 a'):
                            href = result.get('href')
                            if href and self._is_valid_url(href):
                                urls.append(href)
                                found_any = True
                                print(f"[+] Found: {href}")
                    
                    if not found_any:
                        break
                    
                    time.sleep(random.uniform(4, 6))
                else:
                    print(f"[!] HTTP {response.status_code}")
                    break
                    
            except Exception as e:
                print(f"[-] Startpage error: {e}")
                break
        
        urls = list(set(urls))
        print(f"[*] Total: {len(urls)} URLs from Startpage")
        return urls[:max_results]
    
    def _is_valid_url(self, url):
        if not url.startswith('http'):
            return False
        exclude = ['startpage.com', 'google.com', 'youtube.com']
        for domain in exclude:
            if domain in url.lower():
                return False
        return '?' in url


class PublicAPISearcher(DorkEngine):
    """Common Crawl and Wayback Machine for archived URLs"""
    def __init__(self):
        super().__init__()
    
    def search_wayback(self, domain_pattern, max_results=50):
        """Search Wayback Machine CDX API"""
        urls = []
        
        print(f"[*] Searching Wayback Machine for: {domain_pattern}")
        
        try:
            # Wayback CDX API
            cdx_url = "http://web.archive.org/cdx/search/cdx"
            params = {
                'url': domain_pattern,
                'matchType': 'domain',
                'output': 'json',
                'fl': 'original',
                'collapse': 'urlkey',
                'limit': max_results
            }
            
            response = requests.get(cdx_url, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                for item in data[1:]:  # Skip header
                    if isinstance(item, list) and len(item) > 0:
                        url = item[0]
                        if '?' in url and url.startswith('http'):
                            urls.append(url)
                            print(f"[+] Found (Wayback): {url}")
                
                print(f"[*] Found {len(urls)} URLs from Wayback Machine")
            
        except Exception as e:
            print(f"[-] Wayback error: {e}")
        
        return urls[:max_results]
    
    def search(self, query, max_results=50):
        """Parse query and search Wayback"""
        # Extract domain from dork query
        domain_match = re.search(r'site:([^\s]+)', query)
        if domain_match:
            domain = domain_match.group(1)
            return self.search_wayback(f"*.{domain}/*", max_results)
        return []


class SerpAPIDork(DorkEngine):
    """SerpAPI - En güvenilir (API key gerekli)"""
    def __init__(self, api_key=None):
        super().__init__()
        self.api_key = api_key
        self.base_url = "https://serpapi.com/search"
    
    def search(self, query, max_results=50):
        if not self.api_key:
            print("[!] SerpAPI key not configured")
            return []
        
        urls = []
        num_pages = min((max_results // 10) + 1, 10)
        
        print(f"[*] Searching via SerpAPI: {query}")
        
        for page in range(num_pages):
            try:
                params = {
                    'api_key': self.api_key,
                    'engine': 'google',
                    'q': query,
                    'start': page * 10,
                    'num': 10
                }
                
                response = requests.get(self.base_url, params=params, timeout=15)
                
                if response.status_code == 200:
                    data = response.json()
                    results = data.get('organic_results', [])
                    
                    for result in results:
                        url = result.get('link')
                        if url and self._is_valid_url(url):
                            urls.append(url)
                            print(f"[+] Found: {url}")
                    
                    if not results:
                        break
                    
                    time.sleep(1)
                else:
                    print(f"[!] SerpAPI Error: {response.status_code}")
                    break
                    
            except Exception as e:
                print(f"[-] Error: {e}")
                break
        
        print(f"[*] Total: {len(urls)} URLs from SerpAPI")
        return urls[:max_results]
    
    def _is_valid_url(self, url):
        if not url.startswith('http'):
            return False
        exclude = ['google.com', 'youtube.com']
        for domain in exclude:
            if domain in url.lower():
                return False
        return '?' in url


# Multi-engine orchestrator - UPDATED with working engines
class MultiEngineDork:
    """Tries multiple search engines until we get results"""
    def __init__(self, serpapi_key=None, google_cse_key=None, google_cx=None):
        self.engines = []
        
        # Priority order: API services first
        if serpapi_key:
            self.engines.append(('SerpAPI', SerpAPIDork(serpapi_key)))
        
        # Free but working engines
        self.engines.append(('DuckDuckGo_API', DuckDuckGoAPIDork()))
        self.engines.append(('Brave', BraveDork()))
        self.engines.append(('Startpage', StartpageDork()))
        self.engines.append(('Wayback_Machine', PublicAPISearcher()))
    
    def search(self, query, max_results=50):
        all_urls = []
        
        print(f"\n[*] Multi-engine search for: {query}")
        print(f"[*] Will try {len(self.engines)} search engines\n")
        
        for name, engine in self.engines:
            print(f"\n{'='*60}")
            print(f"[*] Trying: {name}")
            print(f"{'='*60}")
            
            try:
                urls = engine.search(query, max_results)
                
                if urls:
                    all_urls.extend(urls)
                    print(f"[+] {name}: Found {len(urls)} URLs")
                    
                    # If we got enough results, stop
                    if len(all_urls) >= max_results:
                        print(f"[*] Reached target of {max_results} URLs")
                        break
                else:
                    print(f"[-] {name}: No results")
                    
            except Exception as e:
                print(f"[-] {name} failed: {e}")
                import traceback
                traceback.print_exc()
                continue
            
            # Delay between engines
            time.sleep(2)
        
        # Remove duplicates
        all_urls = list(set(all_urls))
        
        print(f"\n{'='*60}")
        print(f"[+] TOTAL UNIQUE URLs: {len(all_urls)}")
        print(f"{'='*60}\n")
        
        return all_urls[:max_results]


# Demo URLs - Always available as fallback
DEMO_URLS = [
    'http://testphp.vulnweb.com/artists.php?artist=1',
    'http://testphp.vulnweb.com/listproducts.php?cat=1',
    'http://testphp.vulnweb.com/showimage.php?file=./pictures/1.jpg',
    'http://testphp.vulnweb.com/AJAX/artists.php?artist=1',
    'http://testphp.vulnweb.com/login.php',
    'http://demo.testfire.net/bank/login.aspx?id=1',
    'http://testaspnet.vulnweb.com/showthread.aspx?id=1',
    'http://testaspnet.vulnweb.com/showforum.aspx?id=0',
]

# Predefined dorks
SQL_DORKS = [
    'site:.tr inurl:".php?id="',
    'site:.tr inurl:"urun.php?id="',
    'site:.tr inurl:"haber.php?id="',
    'site:.com.tr inurl:".php?id="',
    'inurl:".php?id=" intext:"mysql"',
    'inurl:"product.php?id="',
    'inurl:"news.php?id="',
    'inurl:"page.php?id="',
]
