#!/usr/bin/env python3
"""
Kronängs IF Calendar Scraper v5
"""
import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import date, datetime
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

SWEDISH_MONTHS = {
    "JANUARI": 1, "FEBRUARI": 2, "MARS": 3, "APRIL": 4,
    "MAJ": 5, "JUNI": 6, "JULI": 7, "AUGUSTI": 8,
    "SEPTEMBER": 9, "OKTOBER": 10, "NOVEMBER": 11, "DECEMBER": 12,
}


def fetch_calendar():
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(CALENDAR_URL, headers=headers, timeout=30)
    response.raise_for_status()
    response.encoding = 'iso-8859-1'
    return response.text


def parse_month_year(soup):
    """Extract month and year from the calendar header (e.g. 'MARS 2026')."""
    header = soup.find('b', style=re.compile(r'font-size'))
    if header:
        parts = header.get_text(strip=True).upper().split()
        if len(parts) == 2:
            month = SWEDISH_MONTHS.get(parts[0], datetime.now().month)
            year = int(parts[1]) if parts[1].isdigit() else datetime.now().year
            return month, year
    return datetime.now().month, datetime.now().year


def parse_calendar(html):
    soup = BeautifulSoup(html, 'html.parser')
    month, year = parse_month_year(soup)
    activities = []

    for day_row in soup.find_all('tr', class_=['dag', 'son', 'idag', 'innanidag']):
        # HTML has unclosed <td> tags — BS4 nests them.
        # Only 2 top-level TDs: [empty, date+everything nested inside].
        tds = day_row.find_all('td', recursive=False)

        day_num = ""
        weekday = ""

        for td in tds:
            style = td.get('style', '')
            if 'padding-left' in style:
                b = td.find('b')
                if b:
                    day_num = b.text.strip()
                font = td.find('font')
                if font:
                    wday = font.get_text(strip=True)
                    if wday and len(wday) <= 4 and wday.isalpha():
                        weekday = wday

        if not day_num:
            continue

        # Build ISO date string for this day
        try:
            iso_date = date(year, month, int(day_num)).isoformat()
        except ValueError:
            iso_date = ""

        inner_table = day_row.find('table', {'border': '0', 'cellspacing': '0', 'cellpadding': '0'})
        if not inner_table:
            continue

        # recursive=True needed — malformed HTML nests all <tr> inside each other
        for act_row in inner_table.find_all('tr'):
            activity = parse_activity(act_row, day_num, weekday, iso_date)
            if activity:
                activities.append(activity)

    return month, year, activities


def parse_activity(row, day, weekday, iso_date):
    # Each activity row has 2 top-level cells:
    #   cells[0]: time + calBox (activity type)
    #   cells[1]: team link + description/location
    cells = row.find_all('td', recursive=False)
    if len(cells) < 2:
        return None

    # Time
    time_cell = cells[0]
    span = time_cell.find('span')
    time_text = span.get_text(strip=True) if span else time_cell.get_text(strip=True)
    time_match = re.search(r'(\d{1,2}:\d{2})', time_text)
    time_str = time_match.group(1) if time_match else ""

    # Activity type
    act_type = "Övrigt"
    calbox = time_cell.find('div', class_=re.compile(r'calBox[123]'))
    if calbox:
        for c in calbox.get('class', []):
            if c in ACTIVITY_TYPES:
                act_type = ACTIVITY_TYPES[c]
                break

    # Team
    content = cells[1]
    team = None
    team_id = None

    for link in content.find_all('a', href=re.compile(r'ID=')):
        href = link.get('href', '')
        match = re.search(r'ID=(\d+)', href)
        if match and match.group(1):
            team_id = match.group(1)
            team = TEAM_IDS.get(team_id, link.text.strip())
        else:
            team = link.text.strip()
        break

    if not team:
        return None

    # Description and location
    description = ""
    location = ""
    kal_link = content.find('a', class_='kal')
    if kal_link:
        text = kal_link.get_text(strip=True)
        if text and text != '(..)':
            if ',' in text:
                parts = text.split(',', 1)
                description = parts[0].strip()
                location = parts[1].strip()
            else:
                description = text

    if not location and description:
        if 'hemma' in description.lower():
            location = "Kronängs Arena"
        elif 'borta' in description.lower():
            m = re.search(r'borta[,\s]+(.+)', description, re.I)
            if m:
                location = m.group(1).strip()

    return {
        "date": iso_date,   # "YYYY-MM-DD" — used by JS for past/future check
        "day": day,
        "weekday": weekday,
        "time": time_str,
        "team": team,
        "team_id": team_id,
        "type": act_type,
        "description": description,
        "location": location,
    }


def save_data(activities, month, year):
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "last_updated": datetime.now().isoformat(),
        "source": CALENDAR_URL,
        "month": month,
        "year": year,
        "activity_count": len(activities),
        "activities": activities
    }
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(activities)} activities")


def main():
    print("Fetching Kronängs IF calendar...")
    html = fetch_calendar()
    month, year, activities = parse_calendar(html)
    print(f"Calendar month: {month}/{year}")
    save_data(activities, month, year)
    print(f"Done! Found {len(activities)} activities")

if __name__ == "__main__":
    main()
