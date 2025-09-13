import requests
import os
import csv
from dotenv import load_dotenv
load_dotenv()

API_KEY = os.getenv("POLYGON_API_KEY")
LIMIT = 1000
url= f"https://api.polygon.io/v3/reference/tickers?market=stocks&active=true&order=asc&limit={LIMIT}&sort=ticker&apiKey={API_KEY}"
response = requests.get(url)
tickers = []

data = response.json()
for ticker in data['results']:
    tickers.append(ticker)

while 'next_url' in data:
    print("Requesting more data",data['next_url'])
    response = requests.get(data['next_url']+ f"&apiKey={API_KEY}")
    data = response.json()
    if 'results' not in data:
        print("No results in response:", data)
        break
    for ticker in data['results']:
        tickers.append(ticker)

example_ticker = {'ticker': 'AAAA', 
                  'name': 'Amplius Aggressive Asset Allocation ETF', 
                  'market': 'stocks', 
                  'locale': 'us', 
                  'primary_exchange': 'BATS', 
                  'type': 'ETF',
                  'active': True,
                  'currency_name': 'usd',
                  'composite_figi': 'BBG01W275XX6',
                  'share_class_figi': 'BBG01W275ZB5',
                  'last_updated_utc': '2025-09-13T06:11:08.182782211Z'} 

fieldnames = list(example_ticker.keys())
output_csv = "tickers.csv"
with open(output_csv, mode="w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    for t in tickers:
        row = {key: t.get(key, "") for key in fieldnames}
        writer.writerow(row)
print(f"Wrote {len(tickers)} records to {output_csv}") 