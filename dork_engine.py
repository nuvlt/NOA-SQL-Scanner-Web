"""
NOA SQL Scanner Web - Dork Search Engine
Google & Yandex integration
"""

import requests
from bs4 import BeautifulSoup
import time
import random
from urllib.parse import quote_plus, urljoin

class DorkEngine:
    def __init__(self):
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
        ]
    
    def get_headers(self):
        return {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }

class GoogleDork(DorkEngine):
    def __init__(self):
        super().__init__()
        self.base_url = "https://www.google.com/search"
    
    def search(self, dork, max_results=50):
        """
        Search Google with dork
        Returns list of URLs
        """
        urls = []
        num_pages = (max_results // 10) + 1
        
        for page in range(num_pages):
            try:
                params = {
                    'q': dork,
                    'start': page * 10,
                    'num': 10
                }
                
                response = requests.get(
                    self.base_url,
                    params=params,
                    headers=self.get_headers(),
                    timeout=10
                )
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Extract URLs from search results
                    for result in soup.find_all('div', class_='g'):
                        link = result.find('a')
                        if link and link.get('href'):
                            url = link['href']
                            if url.startswith('http') and '?' in url:
                                urls.append(url)
                
                # Rate limiting
                time.sleep(random.uniform(2, 5))
                
                if len(urls) >= max_results:
                    break
                    
            except Exception as e:
                print(f"Error in Google search: {e}")
                continue
        
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
        num_pages = (max_results // 10) + 1
        
        for page in range(num_pages):
            try:
                params = {
                    'text': dork,
                    'p': page
                }
                
                response = requests.get(
                    self.base_url,
                    params=params,
                    headers=self.get_headers(),
                    timeout=10
                )
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Extract URLs from Yandex results
                    for result in soup.find_all('li', class_='serp-item'):
                        link = result.find('a')
                        if link and link.get('href'):
                            url = link['href']
                            if url.startswith('http') and '?' in url:
                                urls.append(url)
                
                # Rate limiting
                time.sleep(random.uniform(2, 5))
                
                if len(urls) >= max_results:
                    break
                    
            except Exception as e:
                print(f"Error in Yandex search: {e}")
                continue
        
        return urls[:max_results]

# Predefined SQL injection dorks
SQL_DORKS = [
    'inurl:".php?id=" intext:"mysql_fetch"',
    'inurl:".php?catid=" intext:"mysql_fetch"',
    'inurl:".php?pid=" intext:"mysql_fetch"',
    'inurl:"product.php?id="',
    'inurl:"news.php?id="',
    'inurl:"item.php?id="',
    'inurl:"page.php?id="',
    'inurl:"gallery.php?id="',
    'inurl:"index.php?id="',
    'inurl:".php?id=" site:.com',
    'inurl:".asp?id=" site:.com',
    'inurl:".aspx?id=" site:.com',
]
