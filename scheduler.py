from script import run_stock_job
import time
import csv
import schedule 
from datetime import datetime

def job():
    print("Starting scheduled job to fetch tickers at: ", datetime.now())

#schedule the job every minute
schedule.every().minute.do(job)
schedule.every().minute.do(run_stock_job)

# for every hour => schedule.every().hour.do(run_stock_job)
#for every day at 9:00 am => schedule.every().day.at("09:00").do(run_stock_job)

while True:
    schedule.run_pending()
    time.sleep(1)