#!/usr/bin/env python3
"""
Kronängs IF Calendar Scraper
Fetches calendar data from SportAdmin and outputs JSON.
"""

import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime
from pathlib import Path

# Configuration
CALENDAR_URL = "https://www.kronangsif.se/kalender/ajaxKalender.asp?ID=38276"
OUTPUT_FILE = Path(__file__).parent / "data" / "calendar.json"

# Team mappings from the HTML
TEAM_IDS = {
    "38937": "Herr",
    "52695": "Dam", 
    "38381": "Utvecklingslag",
    "224798": "P2009-2010",
    "260562": "P2011",
    "281528": "P2012",
    "324307": "P2013",
    "324331": "P2014",
    "56158": "P 2015",
    "414417": "P2016",
    "320864": "F2008-2010",
    "281521": "F2011-2012",
    "374981": "F2013/2014",
    "520574": "F2015-2016",
    "481208": "Fotbollsskolan födda 2017",
    "520555": "Fotbollsskolan födda 2018",
    "584817": "Fotbollsskolan födda 2020",
    "181941": "Klubbstuga",
    "430796": "VEO kamera",
}

# Activity type mapping from CSS classes
ACTIVITY_TYPES = {
    "calBox1": "Träning",
    "calBox2": "Match", 
    "calBox3": "Övrigt"
}

def fetch_calendar():
    """Fetch the calendar HTML from the endpoint."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    response = requests.get(CALENDAR_URL, headers=headers, timeout=30)
    response.raise_for_status()
    # The page uses ISO-8859-1 encoding
    response.encoding = 'iso-8859-1'
    return response.text

def parse_calendar(html):
    """Parse the calendar HTML and extract activities."""
    soup = BeautifulSoup(html, 'html.parser')
    activities = []
    
    # Find all calendar rows (days)
    days = soup.find_all('tr', class_=['dag', 'son', 'idag', 'innanidag'])
    
    current_month_year = None
    
    # Try to extract month/year from the page
    month_header = soup.find('b', string=re.compile(r'^(JANUARI|FEBRUARI|MARS|APRIL|MAJ|JUNI|JULI|AUGUSTI|SEPTEMBER|OKTOBER|NOVEMBER|DECEMBER)\s+\d{4}$', re.I))
    if month_header:
        current_month_year = month_header.text.strip()
    
    for day_row in days:
        # Extract date from the row
        date_cell = day_row.find('td', class_='mCal', style=re.compile('padding-left'))
        if not date_cell:
            continue
            
        day_num = date_cell.find('b')
        if not day_num:
            continue
        day_text = day_num.text.strip()
        
        # Get weekday
        weekday_cell = day_row.find('td', class_='mCal', width='5%')
        weekday = weekday_cell.text.strip() if weekday_cell else ""
        
        # Find all activities in this day
        activity_table = day_row.find('table', border=0, cellspacing=0, cellpadding=0)
        if not activity_table:
            continue
            
        for activity_row in activity_table.find_all('tr'):
            activity = parse_activity(activity_row, day_text, weekday, current_month_year)
            if activity:
                activities.append(activity)
    
    return activities

def parse_activity(row, day, weekday, month_year):
    """Parse a single activity row."""
    activity = {
        "day": day,
        "weekday": weekday,
        "time": None,
        "team": None,
        "team_id": None,
        "type": None,
        "description": None,
        "location": None,
        "raw_text": None
    }
    
    # Find time
    time_match = re.search(r'(\d{1,2}:\d{2})', row.text)
    if time_match:
        activity["time"] = time_match.group(1)
    
    # Find team from link
    team_link = row.find('a', href=re.compile(r'ID=\d+'))
    if team_link:
        href = team_link.get('href', '')
        team_id_match = re.search(r'ID=(\d+)', href)
        if team_id_match:
            team_id = team_id_match.group(1)
            activity["team_id"] = team_id
            activity["team"] = TEAM_IDS.get(team_id, team_link.text.strip())
    
    # Find activity type from calBox class
    for cal_box in row.find_all('div', class_=re.compile(r'calBox\d')):
        for class_name in cal_box.get('class', []):
            if class_name in ACTIVITY_TYPES:
                activity["type"] = ACTIVITY_TYPES[class_name]
                break
    
    # Find description/location from the kal class links
    kal_links = row.find_all('a', class_='kal')
    for link in kal_links:
        text = link.text.strip()
        if text and text != activity["team"]:
            # Usually format is "Description, Location"
            parts = text.split(',')
            if len(parts) >= 2:
                activity["description"] = parts[0].strip()
                activity["location"] = parts[-1].strip()
            else:
                activity["description"] = text
                # Check if it's a match (contains "hemma" or "borta")
                if "hemma" in text.lower():
                    activity["location"] = "Kronängs Arena"
                elif "borta" in text.lower():
                    # Extract location after comma
                    match = re.search(r'borta,\s*(.+)', text, re.I)
                    if match:
                        activity["location"] = match.group(1).strip()
            break
    
    # Only return if we have meaningful data
    if activity["team"] and (activity["description"] or activity["type"]):
        return activity
    
    return None

def save_data(activities):
    """Save activities to JSON file."""
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    data = {
        "last_updated": datetime.now().isoformat(),
        "source": CALENDAR_URL,
        "activity_count": len(activities),
        "activities": activities
    }
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"Saved {len(activities)} activities to {OUTPUT_FILE}")

def main():
    print("Fetching Kronängs IF calendar...")
    try:
        html = fetch_calendar()
        activities = parse_calendar(html)
        save_data(activities)
        print(f"Success! Found {len(activities)} activities.")
        
        # Print sample
        if activities:
            print("\nSample activity:")
            print(json.dumps(activities[0], ensure_ascii=False, indent=2))
            
    except Exception as e:
        print(f"Error: {e}")
        raise

if __name__ == "__main__":
    main()
