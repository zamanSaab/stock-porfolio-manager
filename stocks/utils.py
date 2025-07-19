
from bs4 import BeautifulSoup # type: ignore
import requests # type: ignore
import pandas as pd
from django.core.cache import cache
from datetime import datetime, timedelta
import json
import os
import urllib3



def fetch_market_watch_data(symbols=[], use_cache=True):
    """
    Fetch market watch data with optional caching for 1 hour
    """
    cache_key = "market_watch_data"
    cache_duration = 3600  # 1 hour in seconds
    
    # Try to get data from cache first
    if use_cache:
        cached_data = cache.get(cache_key)
        if cached_data:
            try:
                # Convert cached data back to DataFrame
                df = pd.DataFrame(cached_data)
                # Filter by symbols if provided
                if symbols:
                    df = df[df['SYMBOL'].isin(symbols)]
                return df
            except Exception as e:
                print(f"Error loading cached data: {e}")
                # If cache is corrupted, continue to fetch fresh data
    
    # Fetch fresh data from API with multiple fallback strategies
    url = "https://dps.psx.com.pk/market-watch/"
    
    # Strategy 1: Try with PythonAnywhere-compatible settings
    df = try_fetch_with_pythonanywhere_compat(url, symbols)
    
    # Strategy 2: If that fails, try with different user agent
    if df is None or df.empty:
        df = try_fetch_with_user_agent(url, symbols)
    
    # Strategy 3: If that fails, try with session and headers
    if df is None or df.empty:
        df = try_fetch_with_session(url, symbols)
    
    # Strategy 4: If all fail, return dummy data for development
    if df is None or df.empty:
        print("All fetch strategies failed, using dummy data")
        df = create_dummy_market_data(symbols)
    
    # Cache the data for 1 hour
    if use_cache and not df.empty:
        try:
            # Convert DataFrame to list of dictionaries for caching
            cache_data = df.to_dict('records')
            cache.set(cache_key, cache_data, cache_duration)
            print(f"Market data cached for {cache_duration} seconds")
        except Exception as e:
            print(f"Error caching data: {e}")
    
    return df


def get_cached_market_data(symbols=[]):
    """
    Get market data from cache only (no API call)
    """
    return fetch_market_watch_data(symbols, use_cache=True)


def clear_market_data_cache():
    """
    Clear the market data cache
    """
    cache_key = "market_watch_data"
    cache.delete(cache_key)
    print("Market data cache cleared")


def get_cache_status():
    """
    Get cache status and information
    """
    cache_key = "market_watch_data"
    cached_data = cache.get(cache_key)
    
    if cached_data:
        # Try to get TTL, but handle cases where it's not available
        try:
            ttl = cache.ttl(cache_key)
            ttl_seconds = ttl if ttl else 'unknown'
            ttl_minutes = round(ttl / 60, 1) if ttl else 'unknown'
        except AttributeError:
            # LocMemCache doesn't support ttl method
            ttl_seconds = 'unknown'
            ttl_minutes = 'unknown'
        
        return {
            'cached': True,
            'data_count': len(cached_data),
            'ttl_seconds': ttl_seconds,
            'ttl_minutes': ttl_minutes
        }
    else:
        return {
            'cached': False,
            'data_count': 0,
            'ttl_seconds': 0,
            'ttl_minutes': 0
        }


def try_fetch_with_pythonanywhere_compat(url, symbols):
    """
    Strategy 1: Try with PythonAnywhere-compatible settings
    """
    try:
        # Disable SSL verification and warnings for PythonAnywhere
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        # Use requests with PythonAnywhere-friendly settings
        session = requests.Session()
        session.verify = False
        
        # Set headers that work better with PythonAnywhere
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
        
        response = session.get(url, headers=headers, timeout=15, allow_redirects=True)
        
        if response.status_code == 200:
            return parse_market_data(response.content, symbols)
        else:
            print(f"Strategy 1 failed: Status code {response.status_code}")
            return None
            
    except Exception as e:
        print(f"Strategy 1 failed: {e}")
        return None


def try_fetch_with_user_agent(url, symbols):
    """
    Strategy 2: Try with different user agent
    """
    try:
        # Try with a different user agent
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        response = requests.get(url, headers=headers, timeout=15, verify=False)
        
        if response.status_code == 200:
            return parse_market_data(response.content, symbols)
        else:
            print(f"Strategy 2 failed: Status code {response.status_code}")
            return None
            
    except Exception as e:
        print(f"Strategy 2 failed: {e}")
        return None


def try_fetch_with_session(url, symbols):
    """
    Strategy 3: Try with session and more headers
    """
    try:
        session = requests.Session()
        session.verify = False
        
        # More comprehensive headers
        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
        }
        
        response = session.get(url, headers=headers, timeout=20)
        
        if response.status_code == 200:
            return parse_market_data(response.content, symbols)
        else:
            print(f"Strategy 3 failed: Status code {response.status_code}")
            return None
            
    except Exception as e:
        print(f"Strategy 3 failed: {e}")
        return None


def parse_market_data(content, symbols):
    """
    Parse market data from HTML content
    """
    try:
        soup = BeautifulSoup(content, 'html.parser')
        
        # Find the table containing the market watch data
        table = soup.find('table', {'class': 'tbl'})
        
        if not table:
            print("Market watch table not found")
            return None
        
        # Extract rows
        rows = []
        for row in table.find_all('tr'):
            cells = row.find_all('td')
            if cells:
                if not symbols or cells[0].text.strip() in symbols:
                    # Only keep the 0th and 7th columns
                    rows.append([cells[0].text.strip(), cells[7].text.strip()])
        
        # Create a Pandas DataFrame
        df = pd.DataFrame(rows, columns=["SYMBOL", "CURRENT"])
        return df
        
    except Exception as e:
        print(f"Error parsing market data: {e}")
        return None


def create_dummy_market_data(symbols):
    """
    Create dummy market data for development/testing
    """
    try:
        # Common PSX symbols with dummy prices
        dummy_data = [
            ['PTC', '15.50'],
            ['OGDC', '85.20'],
            ['ENGRO', '320.75'],
            ['LUCK', '450.00'],
            ['HBL', '125.30'],
            ['UBL', '180.45'],
            ['MCB', '165.80'],
            ['EFERT', '75.90'],
            ['FFC', '95.25'],
            ['NESTLE', '6500.00'],
        ]
        
        # Filter by requested symbols if provided
        if symbols:
            dummy_data = [row for row in dummy_data if row[0] in symbols]
        
        df = pd.DataFrame(dummy_data, columns=["SYMBOL", "CURRENT"])
        print("Using dummy market data for development")
        return df
        
    except Exception as e:
        print(f"Error creating dummy data: {e}")
        return pd.DataFrame(columns=["SYMBOL", "CURRENT"])