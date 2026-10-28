#!/usr/bin/env python3
"""Scheduled best-effort import of publicly displayed events from pirna.de.
If layout changes or the site cannot be reached, fail safely and keep old events.json.
"""
import json,re,hashlib,datetime,time
from pathlib import Path
from urllib.parse import urljoin,urlparse,parse_qs,urlencode,urlunparse
from bs4 import BeautifulSoup
import requests
BASE='https://www.pirna.de/pirna-erleben/veranstaltungen/veranstaltungskalender/'
MONTHS={'januar':1,'februar':2,'märz':3,'maerz':3,'april':4,'mai':5,'juni':6,'juli':7,'august':8,'september':9,'oktober':10,'november':11,'dezember':12}
S=requests.Session();S.headers.update({'User-Agent':'PirnaSmart student prototype event calendar updater (polite fetch; contact via repository)'})
def get(url):
 r=S.get(url,timeout=25);r.raise_for_status();return BeautifulSoup(r.text,'html.parser')
def parse_detail(url):
 soup=get(url)
 title=soup.find('h1');title=title.get_text(' ',strip=True) if title else ''
 text=soup.get_text(' ',strip=True)
 # Official detail pages contain "Zeitpunkt Mittwoch 28.10.2026, 17:00 - 18:30".
 m=re.search(r'Zeitpunkt\s+(?:[A-Za-zÄÖÜäöüß]+\s+)?(\d{1,2})\.(\d{1,2})\.(\d{4})\s*,\s*(\d{1,2}):(\d{2})',text,re.I)
 if not m:return None
 day,month,year,hour,minute=map(int,m.groups())
 try: dt=datetime.datetime(year,month,day,hour,minute)
 except ValueError:return None
 # Exclude events whose start is well in the past, but include multi-day events if their details expose only start.
 if dt < datetime.datetime.now()-datetime.timedelta(days=1):return None
 location=re.search(r'Location\s+(.{1,180}?)\s+(?:Um die Karte|Weitere Infos|Stadtinfo|Impressum)',text,re.I)
 addr=location.group(1).strip() if location else 'Pirna · Veranstaltungsort im Kalender prüfen'
 addr=re.sub(r'\s+',' ',addr)[:170]
 desc='Weitere Informationen im offiziellen Veranstaltungskalender'
 return {'name':title[:170],'date':dt.isoformat(timespec='seconds'),'dateLabel':dt.strftime('%d.%m. · %H:%M'),'addr':addr,'desc':desc,'url':url}
def run():
 # First page + page links; link paths are official detail routes.
 listing=get(BASE)
 pages=[BASE]
 for a in listing.select('a[href]'):
  href=urljoin(BASE,a.get('href',''))
  if urlparse(href).netloc=='www.pirna.de' and ('tx_' in href or 'page=' in href) and 'veranstaltungskalender' in href and href not in pages:
   pages.append(href)
 pages=pages[:10]
 urls=[]
 for i,p in enumerate(pages):
  try:
   page=listing if i==0 else get(p)
   for a in page.select('a[href]'):
    u=urljoin(BASE,a['href'])
    if re.search(r'/veranstaltung/detail/[^/]+/\d+/',u) and u not in urls:urls.append(u)
  except requests.RequestException as e:print('Seite nicht erreichbar',e)
  time.sleep(.3)
 events=[]
 for url in urls[:110]:
  try:
   e=parse_detail(url)
   if e:events.append(e)
  except Exception as exc:print('Einzeltermin fehlgeschlagen',url,exc)
  time.sleep(.25)
 if len(events)<2:raise RuntimeError('Keine ausreichenden verifizierbaren Termine: behalte bestehende events.json')
 events.sort(key=lambda x:x['date'])
 output={'updated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source':BASE,'events':events}
 Path('events.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print('Aktualisiert:',len(events),'Veranstaltungen')
if __name__=='__main__':run()
