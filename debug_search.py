#!/usr/bin/env python3
"""
Debug script to diagnose why search engines aren't returning results
"""

import requests
from bs4 import BeautifulSoup
import sys

def test_basic_connectivity():
    """Test if we can reach the internet"""
    print("\n[1] Testing basic internet connectivity...")
    
    test_sites = [
        "https://www.google.com",
        "https://duckduckgo.com",
        "https://www.bing.com",
        "https://api.duckduckgo.com",
    ]
    
    for site in test_sites:
        try:
            response = requests.get(site, timeout=10)
            print(f"  [✓] {site}: HTTP {response.status_code}")
        except Exception as e:
            print(f"  [✗] {site}: ERROR - {e}")
            return False
    
    return True


def test_duckduckgo_api():
    """Test DuckDuckGo Instant Answer API"""
    print("\n[2] Testing DuckDuckGo API...")
    
    try:
        url = "https://api.duckduckgo.com/"
        params = {
            'q': 'site:github.com php',
            'format': 'json',
        }
        
        response = requests.get(url, params=params, timeout=15)
        print(f"  Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"  Response keys: {list(data.keys())}")
            
            related = data.get('RelatedTopics', [])
            print(f"  RelatedTopics count: {len(related)}")
            
            if related:
                print(f"  [✓] API working! Sample result:")
                for item in related[:3]:
                    if isinstance(item, dict) and 'FirstURL' in item:
                        print(f"    - {item['FirstURL']}")
                return True
            else:
                print(f"  [!] API responded but no results")
                print(f"  [!] This is normal - DDG API has limited results")
        else:
            print(f"  [✗] API returned HTTP {response.status_code}")
        
        return False
        
    except Exception as e:
        print(f"  [✗] Error: {e}")
        return False


def test_brave_search():
    """Test Brave Search HTML"""
    print("\n[3] Testing Brave Search...")
    
    try:
        url = "https://search.brave.com/search"
        params = {'q': 'site:github.com'}
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=15)
        print(f"  Status: {response.status_code}")
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Try to find any links
            links = soup.find_all('a', href=True)
            external_links = [a['href'] for a in links if a['href'].startswith('http') and 'brave.com' not in a['href']]
            
            print(f"  Total links found: {len(links)}")
            print(f"  External links: {len(external_links)}")
            
            if external_links:
                print(f"  [✓] Found some links! Sample:")
                for link in external_links[:3]:
                    print(f"    - {link}")
                return True
            else:
                print(f"  [!] No external links found")
                print(f"  [!] Brave might be showing CAPTCHA or blocking")
                
                # Check for CAPTCHA
                if 'captcha' in response.text.lower():
                    print(f"  [!] CAPTCHA detected in response")
        else:
            print(f"  [✗] HTTP {response.status_code}")
        
        return False
        
    except Exception as e:
        print(f"  [✗] Error: {e}")
        return False


def test_wayback_machine():
    """Test Wayback Machine CDX API"""
    print("\n[4] Testing Wayback Machine CDX API...")
    
    try:
        url = "http://web.archive.org/cdx/search/cdx"
        params = {
            'url': '*.github.com/*',
            'matchType': 'domain',
            'output': 'json',
            'fl': 'original',
            'collapse': 'urlkey',
            'limit': 10
        }
        
        response = requests.get(url, params=params, timeout=30)
        print(f"  Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"  Results count: {len(data)}")
            
            if len(data) > 1:
                print(f"  [✓] Wayback working! Sample URLs:")
                for item in data[1:4]:  # Skip header
                    if isinstance(item, list) and len(item) > 0:
                        print(f"    - {item[0]}")
                return True
            else:
                print(f"  [!] No archived URLs found")
        else:
            print(f"  [✗] HTTP {response.status_code}")
        
        return False
        
    except Exception as e:
        print(f"  [✗] Error: {e}")
        return False


def test_with_actual_dork():
    """Test with a real SQL dork query"""
    print("\n[5] Testing with actual SQL injection dork...")
    
    test_queries = [
        ("DuckDuckGo API", "https://api.duckduckgo.com/", {
            'q': 'inurl:product.php',
            'format': 'json'
        }),
        ("Wayback", "http://web.archive.org/cdx/search/cdx", {
            'url': '*.edu/*id=*',
            'matchType': 'domain',
            'output': 'json',
            'fl': 'original',
            'limit': 20
        })
    ]
    
    for name, url, params in test_queries:
        print(f"\n  Testing {name}...")
        try:
            response = requests.get(url, params=params, timeout=30)
            
            if response.status_code == 200:
                if name == "DuckDuckGo API":
                    data = response.json()
                    results = data.get('RelatedTopics', [])
                    print(f"    Results: {len(results)}")
                    
                elif name == "Wayback":
                    data = response.json()
                    print(f"    Archived URLs: {len(data) - 1}")
                    
                    # Show sample
                    urls_with_params = []
                    for item in data[1:]:
                        if isinstance(item, list) and len(item) > 0:
                            url = item[0]
                            if '?' in url and 'id=' in url:
                                urls_with_params.append(url)
                    
                    if urls_with_params:
                        print(f"    [✓] Found {len(urls_with_params)} URLs with id parameter!")
                        print(f"    Sample:")
                        for u in urls_with_params[:3]:
                            print(f"      - {u}")
                        return True
                    
            else:
                print(f"    HTTP {response.status_code}")
                
        except Exception as e:
            print(f"    Error: {e}")
    
    return False


def main():
    print("""
╔═══════════════════════════════════════════════════════╗
║         Search Engine Diagnostics                     ║
║         Finding why you're getting no results         ║
╚═══════════════════════════════════════════════════════╝
    """)
    
    results = {}
    
    # Run all tests
    results['Internet'] = test_basic_connectivity()
    results['DuckDuckGo API'] = test_duckduckgo_api()
    results['Brave Search'] = test_brave_search()
    results['Wayback Machine'] = test_wayback_machine()
    results['Actual Dork'] = test_with_actual_dork()
    
    # Summary
    print("\n" + "="*70)
    print("DIAGNOSTIC SUMMARY")
    print("="*70)
    
    for test, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{test:20s}: {status}")
    
    # Recommendations
    print("\n" + "="*70)
    print("RECOMMENDATIONS")
    print("="*70)
    
    passing = sum(1 for v in results.values() if v)
    total = len(results)
    
    if passing == 0:
        print("\n[!] CRITICAL: No search methods working!")
        print("\nPossible causes:")
        print("  1. No internet connection")
        print("  2. Firewall/proxy blocking all search engines")
        print("  3. Your IP is banned by search engines")
        print("\nSolutions:")
        print("  • Check your internet connection")
        print("  • Try from a different network/VPN")
        print("  • Use SERPAPI (paid but guaranteed to work)")
        
    elif passing < 3:
        print(f"\n[!] LIMITED: Only {passing}/{total} methods working")
        print("\nWorking methods should be enough, but:")
        print("  • Consider adding SERPAPI_KEY for better results")
        print("  • Try VPN if some engines are blocked")
        print("  • Wayback Machine is most reliable (no blocking)")
        
    else:
        print(f"\n[✓] GOOD: {passing}/{total} methods working!")
        print("\nYour setup should work. If dork_engine still fails:")
        print("  • Make sure you're using dork_engine_improved.py")
        print("  • Check import statements in app.py")
        print("  • Run: python test_dork.py")
    
    # Show which engine to prioritize
    print("\n[!] Recommended engine priority:")
    if results.get('Wayback Machine'):
        print("  1. Wayback Machine (best for historical URLs)")
    if results.get('DuckDuckGo API'):
        print("  2. DuckDuckGo API (no rate limit)")
    if results.get('Brave Search'):
        print("  3. Brave Search (no captcha usually)")
    
    print("\n" + "="*70)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[!] Diagnostics interrupted")
        sys.exit(0)
    except Exception as e:
        print(f"\n[✗] Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
