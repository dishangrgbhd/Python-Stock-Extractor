import requests
import os
from dotenv import load_dotenv
load_dotenv()
import snowflake.connector
from datetime import datetime
import time
POLYGON_API_KEY = os.getenv("POLYGON_API_KEY")

LIMIT = 1000
DS = '2025-10-22'

def safe_request(url, max_retries=5, base_wait=15):
    retries = 0

    while retries < max_retries:
        response = requests.get(url)

        if response.status_code == 200:
            return response.json()

        # For Rate limit hit
        elif response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", base_wait))
            print(f"Rate limit hit (429). Waiting {retry_after} seconds before retry...")
            time.sleep(retry_after)

        elif response.status_code >= 500:
            wait_time = base_wait * (2 ** retries)
            print(f"Server error {response.status_code}. Retrying in {wait_time} sec...")
            time.sleep(wait_time)

        else:
            response.raise_for_status()

        retries += 1

    raise Exception(f"Failed after {max_retries} retries. Last status: {response.status_code}")


def run_stock_job():
    DS = datetime.now().strftime('%Y-%m-%d')
    url = f'https://api.polygon.io/v3/reference/tickers?market=stocks&active=true&order=asc&limit={LIMIT}&sort=ticker&apiKey={POLYGON_API_KEY}'
    tickers = []

    data = safe_request(url)
    for ticker in data.get('results', []):
        ticker['ds'] = DS
        tickers.append(ticker)

    # Fetch next pages
    while 'next_url' in data and data['next_url']:
        next_url = data['next_url'] + f'&apiKey={POLYGON_API_KEY}'
        print(f"Requesting next page: {next_url}")

        # rate limit for free tier of polygon: 5 requests per minute so 60/5=12 seconds wait
        time.sleep(12)

        data = safe_request(next_url)

        for ticker in data.get('results', []):
            ticker['ds'] = DS
            tickers.append(ticker)

        print(f"Collected {len(tickers)} tickers so far...")

    # Example ticker for schema reference
    example_ticker = {
        'ticker': 'ZWS',
        'name': 'Zurn Elkay Water Solutions Corporation',
        'market': 'stocks',
        'locale': 'us',
        'primary_exchange': 'XNYS',
        'type': 'CS',
        'active': True,
        'currency_name': 'usd',
        'cik': '0001439288',
        'composite_figi': 'BBG000H8R0N8',
        'share_class_figi': 'BBG001T36GB5',
        'last_updated_utc': '2025-09-11T06:11:10.586204443Z',
        'ds': '2025-09-25'
    }

    fieldnames = list(example_ticker.keys())

    load_to_snowflake(tickers, fieldnames)
    print(f"Loaded {len(tickers)} rows to Snowflake.")

def load_to_snowflake(rows, fieldnames):
    # Build connection kwargs from environment variables
    connect_kwargs = {
        'user': os.getenv('SNOWFLAKE_USER'),
        'password': os.getenv('SNOWFLAKE_PASSWORD'),
    }
    account = os.getenv('SNOWFLAKE_ACCOUNT')
    if account:
        connect_kwargs['account'] = account

    warehouse = os.getenv('SNOWFLAKE_WAREHOUSE')
    database = os.getenv('SNOWFLAKE_DATABASE')
    schema = os.getenv('SNOWFLAKE_SCHEMA')
    role = os.getenv('SNOWFLAKE_ROLE')
    if warehouse:
        connect_kwargs['warehouse'] = warehouse
    if database:
        connect_kwargs['database'] = database
    if schema:
        connect_kwargs['schema'] = schema
    if role:
        connect_kwargs['role'] = role

    print(connect_kwargs)
    conn = snowflake.connector.connect( 
        user=connect_kwargs['user'],
        password=connect_kwargs['password'],
        account=connect_kwargs['account'],
        database=connect_kwargs['database'],
        schema=connect_kwargs['schema'],
        role=connect_kwargs['role'],
        session_parameters={
        "CLIENT_TELEMETRY_ENABLED": False,
        }
    )
    try:
        cs = conn.cursor()
        try:
            table_name = os.getenv('SNOWFLAKE_TABLE', 'stock_tickers')

            # Define typed schema based on example_ticker
            type_overrides = {
                'ticker': 'VARCHAR',
                'name': 'VARCHAR',
                'market': 'VARCHAR',
                'locale': 'VARCHAR',
                'primary_exchange': 'VARCHAR',
                'type': 'VARCHAR',
                'active': 'BOOLEAN',
                'currency_name': 'VARCHAR',
                'cik': 'VARCHAR',
                'composite_figi': 'VARCHAR',
                'share_class_figi': 'VARCHAR',
                'last_updated_utc': 'TIMESTAMP_NTZ',
                'ds': 'VARCHAR'
            }
            columns_sql_parts = []
            for col in fieldnames:
                col_type = type_overrides.get(col, 'VARCHAR')
                columns_sql_parts.append(f'"{col.upper()}" {col_type}')

            create_table_sql = f'CREATE TABLE IF NOT EXISTS {table_name} ( ' + ', '.join(columns_sql_parts) + ' )'
            cs.execute(create_table_sql)

            column_list = ', '.join([f'"{c.upper()}"' for c in fieldnames])
            placeholders = ', '.join([f'%({c})s' for c in fieldnames])
            insert_sql = f'INSERT INTO {table_name} ( {column_list} ) VALUES ( {placeholders} )'

            # Conform rows to fieldnames
            transformed = []
            for t in rows:
                row = {}
                for k in fieldnames:
                    row[k] = t.get(k, None)
                print(row)
                transformed.append(row)

            if transformed:
                cs.executemany(insert_sql, transformed)
        finally:
            cs.close()
    finally:
        conn.close()


if __name__ == '__main__':
    run_stock_job()
