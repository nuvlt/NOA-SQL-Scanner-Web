"""
NOA SQL Scanner Web - Dork Search Engine (Enhanced)
Google & Yandex integration with fallbacks
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
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,tr;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0',
            'Referer': 'https://www.google.com/'
        }

class GoogleDork(DorkEngine):
    def __init__(self):
        super().__init__()
        self.base_url = "https://www.google.com/search"
    
    def search(self, dork, max_results=50):
        """
        Search Google with dork - Enhanced with better parsing
        """
        urls = []
        num_pages = min((max_results // 10) + 1, 5)
        
        print(f"[*] Searching Google for: {dork}")
        
        for page in range(num_pages):
            try:
                params = {
                    'q': dork,
                    'start': page * 10,
                    'num': 10,
                    'hl': 'en',
                    'filter': 0,
                    'safe': 'off'
                }
                
                print(f"[*] Page {page + 1}/{num_pages}...")
                
                response = self.session.get(
                    self.base_url,
                    params=params,
                    headers=self.get_headers(),
                    timeout=20,
                    allow_redirects=True
                )
                
                print(f"[*] Response: {response.status_code}")
                
                if response.status_code == 429:
                    print(f"[!] Rate limited by Google")
                    break
                
                if response.status_code == 200:
                    # Extract all URLs from the page
                    found_urls = self._extract_urls_from_google(response.text)
                    
                    for url in found_urls:
                        if url not in urls:
                            urls.append(url)
                            print(f"[+] Found: {url}")
                    
                    print(f"[*] Found {len(found_urls)} URLs on page {page + 1}")
                    
                    if len(found_urls) == 0 and page > 0:
                        print("[*] No more results")
                        break
                    
                    # Rate limiting
                    time.sleep(random.uniform(5, 8))
                    
                    if len(urls) >= max_results:
                        break
                        
            except Exception as e:
                print(f"[-] Error on page {page + 1}: {e}")
                continue
        
        print(f"[*] Total: {len(urls)} URLs from Google")
        return urls[:max_results]
    
    def _extract_urls_from_google(self, html):
        """Extract URLs from Google search results"""
        urls = []
        soup = BeautifulSoup(html, 'html.parser')
        
        # Multiple extraction strategies
        
        # Strategy 1: Standard result divs
        for div in soup.find_all('div', {'class': 'g'}):
            link = div.find('a', href=True)
            if link:
                href = link['href']
                if self._is_valid_url(href):
                    urls.append(href)
        
        # Strategy 2: All links with /url?q=
        for link in soup.find_all('a', href=True):
            href = link['href']
            if '/url?q=' in href:
                # Extract actual URL from Google redirect
                actual_url = href.split('/url?q=')[1].split('&')[0]
                if self._is_valid_url(actual_url):
                    urls.append(actual_url)
        
        # Strategy 3: Direct http/https links
        for link in soup.find_all('a', href=re.compile(r'^https?://')):
            href = link['href']
            if self._is_valid_url(href):
                urls.append(href)
        
        return list(set(urls))
    
    def _is_valid_url(self, url):
        """Check if URL is valid for testing"""
        if not url.startswith('http'):
            return False
        
        # Exclude Google/Yandex/common sites
        exclude = ['google.com', 'youtube.com', 'facebook.com', 'twitter.com', 
                   'instagram.com', 'linkedin.com', 'yandex', 'gstatic']
        
        for domain in exclude:
            if domain in url.lower():
                return False
        
        # Must have query parameters
        if '?' not in url:
            return False
        
        return True


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
                    'lr': 11508  # Turkey
                }
                
                print(f"[*] Page {page + 1}/{num_pages}...")
                
                response = self.session.get(
                    self.base_url,
                    params=params,
                    headers=self.get_headers(),
                    timeout=20
                )
                
                print(f"[*] Response: {response.status_code}")
                
                if response.status_code == 200:
                    found_urls = self._extract_urls_from_yandex(response.text)
                    
                    for url in found_urls:
                        if url not in urls:
                            urls.append(url)
                            print(f"[+] Found: {url}")
                    
                    print(f"[*] Found {len(found_urls)} URLs on page {page + 1}")
                    
                    if len(found_urls) == 0:
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
    
    def _extract_urls_from_yandex(self, html):
        """Extract URLs from Yandex search results"""
        urls = []
        soup = BeautifulSoup(html, 'html.parser')
        
        # Multiple extraction strategies
        
        # Strategy 1: Organic results
        for item in soup.find_all('li', {'class': re.compile(r'serp-item')}):
            link = item.find('a', {'class': re.compile(r'Link.*organic')})
            if not link:
                link = item.find('a', href=re.compile(r'^https?://'))
            
            if link and link.get('href'):
                href = link['href']
                if self._is_valid_url(href):
                    urls.append(href)
        
        # Strategy 2: All external links
        for link in soup.find_all('a', href=re.compile(r'^https?://')):
            href = link['href']
            if self._is_valid_url(href):
                urls.append(href)
        
        return list(set(urls))
    
    def _is_valid_url(self, url):
        """Check if URL is valid for testing"""
        if not url.startswith('http'):
            return False
        
        # Exclude common sites
        exclude = ['google.com', 'youtube.com', 'facebook.com', 'twitter.com', 
                   'instagram.com', 'linkedin.com', 'yandex', 'gstatic']
        
        for domain in exclude:
            if domain in url.lower():
                return False
        
        # Must have query parameters
        if '?' not in url:
            return False
        
        return True


# Alternative: DuckDuckGo (no rate limiting!)
class DuckDuckGoDork(DorkEngine):
    def __init__(self):
        super().__init__()
        self.base_url = "https://html.duckduckgo.com/html/"
    
    def search(self, dork, max_results=50):
        """
        Search DuckDuckGo - No rate limiting!
        """
        urls = []
        num_pages = min((max_results // 30) + 1, 5)
        
        print(f"[*] Searching DuckDuckGo for: {dork}")
        
        for page in range(num_pages):
            try:
                data = {
                    'q': dork,
                    's': page * 30,
                    'dc': page * 30,
                    'v': 'l',
                    'o': 'json',
                    'api': '/d.js'
                }
                
                print(f"[*] Page {page + 1}/{num_pages}...")
                
                response = self.session.post(
                    self.base_url,
                    data=data,
                    headers=self.get_headers(),
                    timeout=20
                )
                
                print(f"[*] Response: {response.status_code}")
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Extract links
                    found_urls = []
                    for result in soup.find_all('a', {'class': 'result__url'}):
                        href = result.get('href')
                        if href and href.startswith('http') and '?' in href:
                            if 'duckduckgo' not in href and href not in urls:
                                urls.append(href)
                                found_urls.append(href)
                                print(f"[+] Found: {href}")
                    
                    print(f"[*] Found {len(found_urls)} URLs on page {page + 1}")
                    
                    if len(found_urls) == 0:
                        break
                    
                    time.sleep(random.uniform(2, 4))
                    
                    if len(urls) >= max_results:
                        break
                    
            except Exception as e:
                print(f"[-] Error on page {page + 1}: {e}")
                continue
        
        print(f"[*] Total: {len(urls)} URLs from DuckDuckGo")
        return urls[:max_results]


# Demo URLs - Guaranteed vulnerable sites for testing
DEMO_URLS = [
    'http://testphp.vulnweb.com/artists.php?artist=1',
    'http://testphp.vulnweb.com/listproducts.php?cat=1',
    'http://testphp.vulnweb.com/showimage.php?file=./pictures/1.jpg',
    'http://demo.testfire.net/bank/login.aspx?id=1',
    'http://testaspnet.vulnweb.com/showthread.aspx?id=1',
]

# Enhanced Turkish dorks
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
    'site:.tr inurl:"index.php?id="',
    'site:.tr inurl:"gallery.php?id="',
    'site:.tr inurl:"ilan.php?id="',
]

# Global dorks
SQL_DORKS_GLOBAL = [
    'inurl:".php?id=" intext:"mysql_"',
    'inurl:".php?catid=" intext:"error"',
    'inurl:"product.php?id="',
    'inurl:"news.php?id="',
    'inurl:"item.php?id="',
    'inurl:"page.php?id="',
    'inurl:"gallery.php?id="',
    'inurl:"index.php?id="',
    'inurl:".asp?id="',
    'inurl:".aspx?id="',
]

SQL_DORKS = SQL_DORKS_TR + SQL_DORKS_GLOBAL
