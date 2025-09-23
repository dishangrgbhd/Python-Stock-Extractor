import requests
import csv
import os
import time
from dotenv import load_dotenv

load_dotenv()

LIMIT = 1000
POLYGON_API_KEY = os.getenv("POLYGON_API_KEY")
output_csv = 'tickers.csv'
# Polygon API rate limit: 5 requests per minute for free tier
REQUEST_DELAY = 12  # seconds between requests (60/5 = 12)

def fetch_tickers():
    """Fetch all tickers from Polygon API with pagination and rate limiting"""
    url = f"https://api.polygon.io/v3/reference/tickers?market=stocks&active=true&order=asc&limit={LIMIT}&sort=ticker&apiKey={POLYGON_API_KEY}"
    
    all_tickers = []
    page_count = 0
    
    try:
        while url:
            page_count += 1
            print(f"Fetching page {page_count}...")
            
            response = requests.get(url)
            
            # Handle rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 60))
                print(f"Rate limited. Waiting {retry_after} seconds...")
                time.sleep(retry_after)
                continue  # Retry the same request
            
            response.raise_for_status()
            data = response.json()
            
            if "results" in data:
                all_tickers.extend(data["results"])
                print(f"Added {len(data['results'])} tickers (total: {len(all_tickers)})")
            
            # Get next URL for pagination
            url = data.get('next_url')
            if url:
                url += f"&apiKey={POLYGON_API_KEY}"
                print(f"Next URL: {url}")
                time.sleep(REQUEST_DELAY)  # Respect rate limits
            
    except requests.exceptions.RequestException as e:
        print(f"HTTP request failed: {e}")
        return None
    except ValueError as e:
        print(f"JSON parsing failed: {e}")
        return None
    except KeyboardInterrupt:
        print("Operation cancelled by user")
        return all_tickers  # Return what we've collected so far
    
    return all_tickers

def write_tickers_to_csv(tickers, filename):
    """Write tickers data to CSV file"""
    if not tickers:
        print("No tickers to write")
        return False
    
    fieldnames = list(tickers[0].keys())
    
    try:
        with open(filename, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for ticker in tickers:
                row = {key: ticker.get(key, '') for key in fieldnames}
                writer.writerow(row)
        
        print(f'Successfully wrote {len(tickers)} rows to {filename}')
        return True
        
    except IOError as e:
        print(f"File writing error: {e}")
        return False

def main():
    print("Fetching tickers from Polygon API...")
    print(f"Using rate limit delay: {REQUEST_DELAY} seconds between requests")
    
    tickers = fetch_tickers()
    
    if tickers:
        print(f"Retrieved {len(tickers)} tickers total")
        success = write_tickers_to_csv(tickers, output_csv)
        if success:
            print("Operation completed successfully")
        else:
            print("Operation completed with errors")
    else:
        print("Failed to fetch tickers")

if __name__ == "__main__":
    main()