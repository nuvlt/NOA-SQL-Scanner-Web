"""
NOA SQL Scanner Web - Dork Search Engine
Google & Yandex integration
"""

import requests
from bs4 import BeautifulSoup
import time
import random
from urllib.parse import quote_plus

class DorkEngine:
    def __init__(self):
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        ]
    
    def get_headers(self):
        return {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        }

class GoogleDork(DorkEngine):
    def __init__(self):
        super().__init__()
        self.base_url = "https://www.google.com/search"
    
    def search(self, dork, max_results=50):
        """
        Search Google with dork - Enhanced for better results
        """
        urls = []
        num_pages = min((max_results // 10) + 1, 5)  # Max 5 page
        
        print(f"[*] Searching Google for: {dork}")
        
        for page in range(num_pages):
            try:
                params = {
                    'q': dork,
                    'start': page * 10,
                    'num': 10,
                    'hl': 'en',
                    'filter': 0  # Don't filter similar results
                }
                
                print(f"[*] Page {page + 1}/{num_pages}...")
                
                response = requests.get(
                    self.base_url,
                    params=params,
                    headers=self.get_headers(),
                    timeout=20,
                    allow_redirects=True
                )
                
                print(f"[*] Response: {response.status_code}")
                
                if response.status_code == 429:
                    print(f"[!] Rate limited by Google after {page + 1} pages")
                    print(f"[*] Collected {len(urls)} URLs before rate limit")
                    break
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Multiple selector strategies
                    found_in_page = 0
                    
                    # Strategy 1: Standard Google results
                    for result in soup.select('div.g'):
                        link_tag = result.select_one('a')
                        if link_tag and link_tag.get('href'):
                            href = link_tag['href']
                            if href.startswith('http') and '?' in href and 'google.com' not in href:
                                if href not in urls:
                                    urls.append(href)
                                    found_in_page += 1
                                    print(f"[+] Found: {href}")
                    
                    # Strategy 2: Alternative layout
                    if found_in_page == 0:
                        for link in soup.select('a[href^="http"]'):
                            href = link.get('href', '')
                            if '?' in href and 'google.com' not in href and 'gstatic' not in href:
                                if href not in urls:
                                    urls.append(href)
                                    found_in_page += 1
                                    print(f"[+] Found: {href}")
                    
                    print(f"[*] Found {found_in_page} URLs on page {page + 1}")
                    
                    if found_in_page == 0 and page > 0:
                        print("[*] No more results, stopping")
                        break
                    
                    # Rate limiting
                    time.sleep(random.uniform(4, 7))
                    
                    if len(urls) >= max_results:
                        break
                        
            except Exception as e:
                print(f"[-] Error on page {page + 1}: {e}")
                continue
        
        print(f"[*] Total: {len(urls)} URLs from Google")
        return urls[:max_results]


class YandexDork(DorkEngine):
    def __init__(self):
        super().__init__()
        self.base_url = "https://yandex.com/search/"
    
    def search(self, dork, max_results=50):
        """
        Search Yandex with dork - Enhanced
        """
        urls = []
        num_pages = min((max_results // 10) + 1, 5)
        
        print(f"[*] Searching Yandex for: {dork}")
        
        for page in range(num_pages):
            try:
                params = {
                    'text': dork,
                    'p': page,
                    'lr': 21  # Turkey region
                }
                
                print(f"[*] Page {page + 1}/{num_pages}...")
                
                response = requests.get(
                    self.base_url,
                    params=params,
                    headers=self.get_headers(),
                    timeout=20
                )
                
                print(f"[*] Response: {response.status_code}")
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    found_in_page = 0
                    
                    # Yandex result selectors
                    for result in soup.select('li.serp-item'):
                        link = result.select_one('a.link, a.organic__url')
                        if link and link.get('href'):
                            href = link['href']
                            if href.startswith('http') and '?' in href and 'yandex' not in href:
                                if href not in urls:
                                    urls.append(href)
                                    found_in_page += 1
                                    print(f"[+] Found: {href}")
                    
                    print(f"[*] Found {found_in_page} URLs on page {page + 1}")
                    
                    if found_in_page == 0:
                        print("[*] No more results")
                        break
                    
                    # Rate limiting
                    time.sleep(random.uniform(4, 7))
                    
                    if len(urls) >= max_results:
                        break
                    
            except Exception as e:
                print(f"[-] Error on page {page + 1}: {e}")
                continue
        
        print(f"[*] Total: {len(urls)} URLs from Yandex")
        return urls[:max_results]

class YandexDork(DorkEngine):
    def __init__(self):
        super().__init__()
        self.base_url = "https://yandex.com/search/"
    
    def search(self, dork, max_results=50):
        """
        Search Yandex with dork
        Returns list of URLs
        """
        urls = []
        num_pages = min((max_results // 10) + 1, 3)
        
        print(f"[*] Searching Yandex for: {dork}")
        
        for page in range(num_pages):
            try:
                params = {
                    'text': dork,
                    'p': page,
                    'lr': 21  # Language region
                }
                
                print(f"[*] Fetching page {page + 1}...")
                
                response = requests.get(
                    self.base_url,
                    params=params,
                    headers=self.get_headers(),
                    timeout=15
                )
                
                print(f"[*] Response status: {response.status_code}")
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Yandex selectors
                    results = soup.select('li.serp-item a.link')
                    
                    for link in results:
                        href = link.get('href', '')
                        if href.startswith('http') and '?' in href and 'yandex' not in href:
                            if href not in urls:
                                urls.append(href)
                                print(f"[+] Found: {href}")
                    
                    # Rate limiting
                    time.sleep(random.uniform(3, 6))
                    
                    if len(urls) >= max_results:
                        break
                    
            except Exception as e:
                print(f"[-] Error in Yandex search: {e}")
                continue
        
        print(f"[*] Total URLs found: {len(urls)}")
        return urls[:max_results]

# Demo URLs - Google engellerse kullan
DEMO_URLS = [
    'http://testphp.vulnweb.com/artists.php?artist=1',
    'http://testphp.vulnweb.com/listproducts.php?cat=1',
    'http://testphp.vulnweb.com/showimage.php?file=1',
    'http://demo.testfire.net/bank/login.aspx?id=1',
]

# Predefined SQL injection dorks
SQL_DORKS = [
    'inurl:".php?id="',
    'inurl:".php?catid="',
    'inurl:".php?pid="',
    'inurl:"product.php?id="',
    'inurl:"news.php?id="',
    'inurl:"item.php?id="',
    'inurl:"page.php?id="',
    'inurl:"gallery.php?id="',
    'inurl:"index.php?id="',
    'inurl:".asp?id="',
    'inurl:".aspx?id="',
]

# TR-specific SQL Dorks (en sona ekle)
SQL_DORKS_TR = [
    'site:.tr inurl:".php?id="',
    'site:.tr inurl:"urun.php?id="',
    'site:.tr inurl:"haber.php?id="',
    'site:.tr inurl:"detay.php?id="',
    'site:.tr inurl:"kategori.php?id="',
    'site:.tr inurl:"sayfa.php?id="',
    'site:.com.tr inurl:".php?id="',
    'site:.com.tr inurl:"product.php?id="',
    'site:.com.tr inurl:"news.php?id="',
    'site:.com.tr inurl:"page.php?id="',
    'site:.gov.tr inurl:".php?id="',
    'site:.edu.tr inurl:".php?id="',
]

# Combine all dorks
SQL_DORKS = SQL_DORKS + SQL_DORKS_TR
