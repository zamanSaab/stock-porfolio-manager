
from bs4 import BeautifulSoup # type: ignore
import requests # type: ignore
import pandas as pd



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