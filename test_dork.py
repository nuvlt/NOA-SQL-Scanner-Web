#!/usr/bin/env python3
"""
Standalone Dork Search Tester
Test dork engines without running the full app
"""

import sys
import os

# Import the new dork engine
try:
    from dork_engine_improved import (
        MultiEngineDork,
        DuckDuckGoAPIDork,
        BraveDork,
        StartpageDork,
        PublicAPISearcher,
        DEMO_URLS
    )
    print("[✓] Successfully imported dork_engine_improved")
except ImportError as e:
    print(f"[✗] Import error: {e}")
    print("[!] Make sure dork_engine_improved.py is in the same directory")
    sys.exit(1)


def test_single_engine(engine_name, engine_class, query):
    """Test a single search engine"""
    print(f"\n{'='*70}")
    print(f"Testing: {engine_name}")
    print(f"{'='*70}")
    
    try:
        engine = engine_class()
        results = engine.search(query, max_results=20)
        
        if results:
            print(f"\n[✓] SUCCESS: Found {len(results)} URLs")
            print("\nFirst 5 results:")
            for i, url in enumerate(results[:5], 1):
                print(f"  {i}. {url}")
            return True
        else:
            print(f"\n[✗] FAILED: No results found")
            return False
            
    except Exception as e:
        print(f"\n[✗] ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_multi_engine(query):
    """Test multi-engine search"""
    print(f"\n{'='*70}")
    print(f"Testing: Multi-Engine Search")
    print(f"{'='*70}")
    
    try:
        # Get API keys from environment
        serpapi_key = os.environ.get('SERPAPI_KEY')
        
        searcher = MultiEngineDork(serpapi_key=serpapi_key)
        results = searcher.search(query, max_results=50)
        
        if results:
            print(f"\n[✓] SUCCESS: Found {len(results)} total URLs")
            print("\nFirst 10 results:")
            for i, url in enumerate(results[:10], 1):
                print(f"  {i}. {url}")
            return True
        else:
            print(f"\n[✗] FAILED: No results from any engine")
            return False
            
    except Exception as e:
        print(f"\n[✗] ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_wayback_specific():
    """Test Wayback Machine with Turkish sites"""
    print(f"\n{'='*70}")
    print(f"Testing: Wayback Machine (Turkish sites)")
    print(f"{'='*70}")
    
    try:
        searcher = PublicAPISearcher()
        
        # Test with Turkish domain
        results = searcher.search_wayback("*.edu.tr/*id=*", max_results=30)
        
        if results:
            print(f"\n[✓] SUCCESS: Found {len(results)} URLs from Wayback")
            print("\nFirst 5 results:")
            for i, url in enumerate(results[:5], 1):
                print(f"  {i}. {url}")
            return True
        else:
            print(f"\n[✗] No results (this is normal if domain has no archive)")
            return False
            
    except Exception as e:
        print(f"\n[✗] ERROR: {e}")
        return False


def main():
    print("""
╔═══════════════════════════════════════════════════════╗
║         NOA Dork Engine Test Suite                   ║
║         Testing all search methods                    ║
╚═══════════════════════════════════════════════════════╝
    """)
    
    # Test queries
    test_queries = [
        'inurl:".php?id="',
        'site:.tr inurl:"haber.php"',
        'inurl:"product.php?id="'
    ]
    
    results_summary = {}
    
    # Choose a query
    print("Select test query:")
    for i, q in enumerate(test_queries, 1):
        print(f"  {i}. {q}")
    
    choice = input("\nEnter number (1-3) or press Enter for default [1]: ").strip()
    
    if choice and choice.isdigit() and 1 <= int(choice) <= len(test_queries):
        query = test_queries[int(choice) - 1]
    else:
        query = test_queries[0]
    
    print(f"\n[*] Using query: {query}")
    
    # Test individual engines
    print("\n" + "="*70)
    print("PHASE 1: Testing Individual Engines")
    print("="*70)
    
    engines_to_test = [
        ("DuckDuckGo API", DuckDuckGoAPIDork),
        ("Brave Search", BraveDork),
        ("Startpage", StartpageDork),
    ]
    
    for name, engine_class in engines_to_test:
        success = test_single_engine(name, engine_class, query)
        results_summary[name] = "✓ Working" if success else "✗ Failed"
        print("\nPress Enter to continue...")
        input()
    
    # Test Wayback Machine
    print("\n" + "="*70)
    print("PHASE 2: Testing Wayback Machine")
    print("="*70)
    wayback_success = test_wayback_specific()
    results_summary["Wayback Machine"] = "✓ Working" if wayback_success else "✗ Failed"
    
    print("\nPress Enter to continue...")
    input()
    
    # Test multi-engine
    print("\n" + "="*70)
    print("PHASE 3: Testing Multi-Engine (Combined)")
    print("="*70)
    multi_success = test_multi_engine(query)
    results_summary["Multi-Engine"] = "✓ Working" if multi_success else "✗ Failed"
    
    # Final summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    for engine, status in results_summary.items():
        print(f"{engine:25s}: {status}")
    
    # Recommendations
    print("\n" + "="*70)
    print("RECOMMENDATIONS")
    print("="*70)
    
    working_engines = [name for name, status in results_summary.items() if "✓" in status]
    
    if working_engines:
        print(f"[✓] {len(working_engines)} engine(s) working!")
        print("\nWorking engines:")
        for engine in working_engines:
            print(f"  • {engine}")
        print("\n[!] Use Multi-Engine for best results")
    else:
        print("[✗] No engines working!")
        print("\n[!] Possible issues:")
        print("  1. Internet connection problem")
        print("  2. All search engines are blocking requests")
        print("  3. Firewall/proxy blocking")
        print("\n[!] Solution: Add SERPAPI_KEY to environment")
        print("  export SERPAPI_KEY=your_key_here")
    
    # Show demo URLs
    print("\n[*] Demo URLs (always available for testing):")
    for url in DEMO_URLS[:3]:
        print(f"  • {url}")
    
    print("\n" + "="*70)
    print("Test complete!")
    print("="*70)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[!] Test interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n[✗] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
