#!/usr/bin/env python3
"""
Kronängs IF Calendar Scraper v3 - Fixed parsing
"""
import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime
from pathlib import Path

CALENDAR_URL = "https://www.kronangsif.se/kalender/ajaxKalender.asp?ID=38276"
OUTPUT_FILE = Path(__file__).parent / "data" / "calendar.json"

TEAM_IDS = {
    "38937": "Herr", "52695": "Dam", "38381": "Utvecklingslag",
    "224798": "P2009-2010", "260562": "P2011", "281528": "P2012",
    "324307": "P2013", "324331": "P2014", "56158": "P 2015",
    "414417": "P2016", "320864": "F2008-2010", "281521": "F2011-2012",
    "374981": "F2013/2014", "520574": "F2015-2016",
    "481208": "Fotbollsskolan födda 2017", "520555": "Fotbollsskolan födda 2018",
    "584817": "Fotbollsskolan födda 2020", "181941": "Klubbstuga",
    "430796": "VEO kamera",
}

ACTIVITY_TYPES = {
    "calBox1": "Träning", "calBox2": "Match", "calBox3": "Övrigt"
}

def fetch_calendar():
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(CALENDAR_URL, headers=headers, timeout=30)
    response.raise_for_status()
    response.encoding = 'iso-8859-1'
    return response.text

def parse_calendar(html):
    soup = BeautifulSoup(html, 'html.parser')
    activities = []
    
    for day_row in soup.find_all('tr', class_=['dag', 'son', 'idag', 'innanidag']):
        tds = day_row.find_all('td', recursive=False)
        
        day_num = ""
        weekday = ""
        
        # Extract day number and weekday
        for td in tds:
            style = td.get('style', '')
            if 'padding-left' in style:
                b = td.find('b')
                if b:
                    day_num = b.text.strip()
            
            width = td.get('width', '')
            if width == '5%':
                text = td.get_text(strip=True)
                if text and len(text) <= 4 and text.isalpha():
                    weekday = text
        
        # Find the inner activity table
        inner_table = day_row.find('table', {'border': '0', 'cellspacing': '0', 'cellpadding': '0'})
        if not inner_table:
            continue
        
        for act_row in inner_table.find_all('tr', recursive=False):
            activity = parse_activity(act_row, day_num, weekday)
            if activity:
                activities.append(activity)
    
    return activities

def parse_activity(row, day, weekday):
    cells = row.find_all('td', recursive=False)
    if len(cells) < 3:
        return None
    
    # Time is in the second cell (index 1)
    time_cell = cells[1]
    time_text = time_cell.get_text(strip=True)
    time_match = re.search(r'(\d{1,2}:\d{2})', time_text)
    time_str = time_match.group(1) if time_match else ""
    
    # Content is in the third cell (index 2)
    content = cells[2]
    
    # Get team
    team = None
    team_id = None
    for link in content.find_all('a', href=re.compile(r'ID=\d+')):
        href = link.get('href', '')
        match = re.search(r'ID=(\d+)', href)
        if match:
            team_id = match.group(1)
            team = TEAM_IDS.get(team_id, link.text.strip())
            break
    
    if not team:
        return None
    
    # Get activity type
    act_type = "Övrigt"
    for div in content.find_all('div', class_=re.compile(r'calBox[123]')):
        classes = div.get('class', [])
        for c in classes:
            if c in ACTIVITY_TYPES:
                act_type = ACTIVITY_TYPES[c]
                break
    
    # Get description and location
    description = ""
    location = ""
    
    for link in content.find_all('a', class_='kal'):
        text = link.get_text(strip=True)
        if not text or text == '(..)':
            continue
        
        if ',' in text:
            parts = text.split(',', 1)
            description = parts[0].strip()
            location = parts[1].strip()
        else:
            description = text
        
        break
    
    # Extract location from description if not set
    if not location and description:
        if 'hemma' in description.lower():
            location = "Kronängs Arena"
        elif 'borta' in description.lower():
            match = re.search(r'borta[,\s]+(.+)', description, re.I)
            if match:
                location = match.group(1).strip()
    
    return {
        "day": day,
        "weekday": weekday,
        "time": time_str,
        "team": team,
        "team_id": team_id,
        "type": act_type,
        "description": description,
        "location": location
    }

def save_data(activities):
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "last_updated": datetime.now().isoformat(),
        "source": CALENDAR_URL,
        "activity_count": len(activities),
        "activities": activities
    }
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(activities)} activities")

def main():
    print("Fetching Kronängs IF calendar...")
    html = fetch_calendar()
    activities = parse_calendar(html)
    save_data(activities)
    print(f"Done! Found {len(activities)} activities")

if __name__ == "__main__":
    main()
