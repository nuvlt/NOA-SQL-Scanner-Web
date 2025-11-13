"""
NOA SQL Scanner - Enhanced Dork Engine
Multiple fallback strategies for reliable results
"""

import requests
from bs4 import BeautifulSoup
import time
import random
from urllib.parse import quote_plus, urljoin
import re

class DorkEngine:
    def __init__(self):
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        ]
        self.session = requests.Session()
    
    def get_headers(self):
        return {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,tr;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }


class GoogleCSE(DorkEngine):
    """Google Custom Search Engine - Daha güvenilir"""
    def __init__(self, api_key=None, cx=None):
        super().__init__()
        self.api_key = api_key
        self.cx = cx  # Custom Search Engine ID
        self.base_url = "https://www.googleapis.com/customsearch/v1"
    
    def search(self, query, max_results=50):
        """Google CSE API kullanarak arama"""
        if not self.api_key or not self.cx:
            print("[!] Google CSE API key/CX not configured")
            return []
        
        urls = []
        num_pages = min((max_results // 10) + 1, 10)
        
        print(f"[*] Searching via Google CSE: {query}")
        
        for page in range(num_pages):
            try:
                params = {
                    'key': self.api_key,
                    'cx': self.cx,
                    'q': query,
                    'start': page * 10 + 1,
                    'num': 10
                }
                
                response = requests.get(self.base_url, params=params, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    items = data.get('items', [])
                    
                    for item in items:
                        url = item.get('link')
                        if url and self._is_valid_url(url):
                            urls.append(url)
                            print(f"[+] Found: {url}")
                    
                    if not items:
                        break
                    
                    time.sleep(1)
                else:
                    print(f"[!] API Error: {response.status_code}")
                    break
                    
            except Exception as e:
                print(f"[-] Error: {e}")
                break
        
        print(f"[*] Total: {len(urls)} URLs from Google CSE")
        return urls[:max_results]
    
    def _is_valid_url(self, url):
        if not url.startswith('http'):
            return False
        exclude = ['google.com', 'youtube.com', 'facebook.com']
        for domain in exclude:
            if domain in url.lower():
                return False
        return '?' in url


class DuckDuckGoHTMLDork(DorkEngine):
    """DuckDuckGo HTML - Rate limit yok!"""
    def __init__(self):
        super().__init__()
        self.base_url = "https://html.duckduckgo.com/html/"
    
    def search(self, query, max_results=50):
        urls = []
        
        print(f"[*] Searching DuckDuckGo HTML: {query}")
        
        try:
            # DuckDuckGo HTML POST request
            data = {
                'q': query,
                'b': '',
                'kl': 'wt-wt'
            }
            
            response = self.session.post(
                self.base_url,
                data=data,
                headers=self.get_headers(),
                timeout=15
            )
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # DuckDuckGo HTML result extraction
                for result in soup.find_all('a', {'class': 'result__a'}):
                    href = result.get('href')
                    if href and self._is_valid_url(href):
                        urls.append(href)
                        print(f"[+] Found: {href}")
                
                # Alternative: Extract from result snippets
                if not urls:
                    for result in soup.find_all('div', {'class': 'result'}):
                        link = result.find('a', href=True)
                        if link:
                            href = link['href']
                            if self._is_valid_url(href):
                                urls.append(href)
                                print(f"[+] Found: {href}")
                
                print(f"[*] Found {len(urls)} URLs from DuckDuckGo")
            else:
                print(f"[!] HTTP {response.status_code}")
                
        except Exception as e:
            print(f"[-] DuckDuckGo error: {e}")
        
        return urls[:max_results]
    
    def _is_valid_url(self, url):
        if not url.startswith('http'):
            return False
        exclude = ['duckduckgo', 'google.com', 'youtube.com']
        for domain in exclude:
            if domain in url.lower():
                return False
        return '?' in url


class BingDork(DorkEngine):
    """Bing Search - Genellikle daha az sıkı"""
    def __init__(self):
        super().__init__()
        self.base_url = "https://www.bing.com/search"
    
    def search(self, query, max_results=50):
        urls = []
        num_pages = min((max_results // 10) + 1, 5)
        
        print(f"[*] Searching Bing: {query}")
        
        for page in range(num_pages):
            try:
                params = {
                    'q': query,
                    'first': page * 10 + 1,
                    'FORM': 'PERE'
                }
                
                headers = self.get_headers()
                headers['Referer'] = 'https://www.bing.com/'
                
                response = self.session.get(
                    self.base_url,
                    params=params,
                    headers=headers,
                    timeout=15
                )
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Bing result extraction
                    for result in soup.find_all('li', {'class': 'b_algo'}):
                        link = result.find('a', href=True)
                        if link:
                            href = link['href']
                            if self._is_valid_url(href):
                                urls.append(href)
                                print(f"[+] Found: {href}")
                    
                    if not urls:
                        break
                    
                    time.sleep(random.uniform(3, 6))
                else:
                    print(f"[!] HTTP {response.status_code}")
                    break
                    
            except Exception as e:
                print(f"[-] Bing error: {e}")
                break
        
        print(f"[*] Total: {len(urls)} URLs from Bing")
        return urls[:max_results]
    
    def _is_valid_url(self, url):
        if not url.startswith('http'):
            return False
        exclude = ['bing.com', 'microsoft.com', 'youtube.com']
        for domain in exclude:
            if domain in url.lower():
                return False
        return '?' in url


class SerpAPIDork(DorkEngine):
    """SerpAPI - En güvenilir (ücretli ama free tier var)"""
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


# Multi-engine orchestrator
class MultiEngineDork:
    """Tüm engine'leri deneyip en iyi sonucu döner"""
    def __init__(self, serpapi_key=None, google_cse_key=None, google_cx=None):
        self.engines = []
        
        # Öncelik sırasına göre ekle
        if serpapi_key:
            self.engines.append(('SerpAPI', SerpAPIDork(serpapi_key)))
        
        if google_cse_key and google_cx:
            self.engines.append(('GoogleCSE', GoogleCSE(google_cse_key, google_cx)))
        
        # Free engines
        self.engines.append(('DuckDuckGo', DuckDuckGoHTMLDork()))
        self.engines.append(('Bing', BingDork()))
    
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
                continue
            
            # Small delay between engines
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
    'http://demo.testfire.net/bank/login.aspx?id=1',
    'http://testaspnet.vulnweb.com/showthread.aspx?id=1',
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
