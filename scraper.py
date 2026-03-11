#!/usr/bin/env python3
"""
Kronängs IF Calendar Scraper - Improved Version
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
    response.encoding = 'iso-8859-1'
    return response.text

def parse_calendar(html):
    """Parse the calendar HTML and extract activities."""
    soup = BeautifulSoup(html, 'html.parser')
    activities = []
    
    # Find all calendar day rows
    day_rows = soup.find_all('tr', class_=['dag', 'son', 'idag', 'innanidag'])
    
    for day_row in day_rows:
        # Extract date
        date_cell = day_row.find('td', style=re.compile('padding-left'))
        if not date_cell:
            continue
            
        day_b = date_cell.find('b')
        if not day_b:
            continue
        day_text = day_b.text.strip()
        
        # Get weekday
        weekday_cell = day_row.find('td', width='5%')
        weekday = weekday_cell.text.strip() if weekday_cell else ""
        
        # Find activity table
        activity_table = day_row.find('table', border=0, cellspacing=0, cellpadding=0)
        if not activity_table:
            continue
        
        # Each row in the activity table is ONE activity
        for activity_tr in activity_table.find_all('tr'):
            activity = parse_activity_row(activity_tr, day_text, weekday)
            if activity:
                activities.append(activity)
    
    return activities

def parse_activity_row(row, day, weekday):
    """Parse a single activity row - each <tr> is one activity."""
    tds = row.find_all('td', recursive=False)
    if len(tds) < 2:
        return None
    
    # First TD has time info
    time_td = tds[0]
    time_text = time_td.get_text(strip=True)
    
    # Find time in format HH:MM or HH:MM - HH:MM
    time_match = re.search(r'(\d{1,2}:\d{2})', time_text)
    time_str = time_match.group(1) if time_match else ""
    
    # Second TD has team, type, description
    content_td = tds[1]
    
    # Get team from first link with ID
    team_link = content_td.find('a', href=re.compile(r'ID=\d+'))
    team = None
    team_id = None
    if team_link:
        href = team_link.get('href', '')
        match = re.search(r'ID=(\d+)', href)
        if match:
            team_id = match.group(1)
            team = TEAM_IDS.get(team_id, team_link.text.strip())
    
    # Find activity type from calBox class
    activity_type = None
    for cal_box in content_td.find_all('div', class_=re.compile(r'calBox\d')):
        for class_name in cal_box.get('class', []):
            if class_name in ACTIVITY_TYPES:
                activity_type = ACTIVITY_TYPES[class_name]
                break
    
    # Find description from kal class links (skip the first team link)
    description = None
    location = None
    kal_links = content_td.find_all('a', class_='kal')
    
    for link in kal_links:
        text = link.get_text(strip=True)
        # Skip if it's just "(..)" or empty
        if not text or text == '(..)':
            continue
            
        # Split on comma - usually "Description, Location"
        if ',' in text:
            parts = text.split(',', 1)
            description = parts[0].strip()
            location = parts[1].strip()
        else:
            description = text
            # Try to extract location
            if "hemma" in text.lower():
                location = "Kronängs Arena"
            elif "borta" in text.lower():
                match = re.search(r'borta[,\s]+(.+)', text, re.I)
                if match:
                    location = match.group(1).strip()
        
        break  # Only take first valid kal link
    
    # Check for hidden popup text (more detailed description)
    popup_div = content_td.find('div', class_='calAkt1')
    if popup_div:
        popup_text = popup_div.get_text(strip=True)
        if popup_text and len(popup_text) > len(description or ''):
            # Use popup text but clean it up
            description = popup_text[:200]  # Limit length
    
    # Only return if we have team and some content
    if team and (description or activity_type):
        return {
            "day": day,
            "weekday": weekday,
            "time": time_str,
            "team": team,
            "team_id": team_id,
            "type": activity_type or "Övrigt",
            "description": description or "",
            "location": location or ""
        }
    
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
            print("\nFirst 3 activities:")
            for i, act in enumerate(activities[:3]):
                print(f"\n{i+1}. {act['team']} - {act['description'][:50]}...")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    main()
