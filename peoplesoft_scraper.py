"""
peoplesoft_scraper.py

A script designed to scrape or fetch live schedule data (Time, Room, Professor)
from a standard PeopleSoft university endpoint.

This is intended to be run periodically via AWS Lambda + EventBridge.
"""

import os
import httpx
import asyncio

PEOPLESOFT_URL = os.getenv("PEOPLESOFT_URL", "https://cmsweb.cms.csueastbay.edu/psc/EBPRD/EMPLOYEE/SA/c/COMMUNITY_ACCESS.CLASS_SEARCH.GBL")

async def fetch_schedule_data():
    """
    Dummy implementation of PeopleSoft schedule collection.
    In a real implementation, this would use Playwright or specialized
    HTTP requests with proper session cookies to parse the PeopleSoft DOM/API.
    """
    print(f"📡 Initiating connection to PeopleSoft at {PEOPLESOFT_URL}...")
    
    # Simulate network delay and parsing
    await asyncio.sleep(2)
    
    scraped_data = [
        {"course_id": "CS 321", "section": "01", "time": "MoWe 10:00AM - 11:15AM", "room": "VBT 124", "professor": "Dr. Smith"},
        {"course_id": "CS 401", "section": "02", "time": "TuTh 2:00PM - 3:15PM", "room": "SF 311", "professor": "Dr. Jones"}
    ]
    
    print(f"✅ Successfully scraped {len(scraped_data)} class sections.")
    return scraped_data

def lambda_handler(event, context):
    """
    AWS Lambda entry point.
    """
    print("Lambda triggered by EventBridge. Starting schedule collection.")
    results = asyncio.run(fetch_schedule_data())
    # Typically, you would save this to the Postgres DB here.
    return {
        "statusCode": 200,
        "body": f"Successfully synced {len(results)} sections."
    }

if __name__ == "__main__":
    asyncio.run(fetch_schedule_data())
