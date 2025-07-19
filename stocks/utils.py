
from bs4 import BeautifulSoup # type: ignore
import requests # type: ignore
import pandas as pd
from django.core.cache import cache
from datetime import datetime, timedelta
import json
import os
import urllib3



def fetch_market_watch_data(symbols=[]):
    url = "https://dps.psx.com.pk/market-watch/"
    
    # Send a GET request to the website
    response = requests.get(url)
    
    # Check if the request was successful
    if response.status_code != 200:
        return None
    
    # Parse the HTML content using BeautifulSoup
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Find the table containing the market watch data
    table = soup.find('table', {'class': 'tbl'})  # Adjust the class name if necessary
    
    if not table:
        return None
    
    # # Extract headers
    # headers = [header.text.strip() for header in table.find_all('th')]
    
    # Extract rows
    rows = []
    for row in table.find_all('tr'):
        cells = row.find_all('td')
        if cells:
            if not symbols or cells[0].text.strip() in symbols:
                # rows.append([cell.text.strip() for cell in cells])
                # Only keep the 0th and 7th columns
                rows.append([cells[0].text.strip(), cells[7].text.strip()])
    
    # import pdb; pdb.set_trace()
    # Create a Pandas DataFrame
    # df = pd.DataFrame(rows, columns=headers)
    df = pd.DataFrame(rows, columns=["SYMBOL", "CURRENT"])

    
    return df

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