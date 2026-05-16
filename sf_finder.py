import xml.etree.ElementTree as ET
import urllib.request
import argparse
import sys
import os
import re

def find_latest_sf_files(project, folder_prefix=""):
    url = f"https://sourceforge.net/projects/{project}/rss"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            xml_data = response.read()
    except Exception as e:
        print(f"Error fetching RSS feed: {e}", file=sys.stderr)
        return []

    root = ET.fromstring(xml_data)
    items = []
    for item in root.findall('./channel/item'):
        title = item.find('title').text
        if title.startswith('/' + folder_prefix.lstrip('/')):
            items.append({
                'title': title,
                'link': item.find('link').text,
                'date': item.find('pubDate').text
            })
    
    if not items:
        return []

    # Find the newest item that looks like a zip/part
    # Pattern to group split files: "Name.zip.001", "Name.zip.002" -> Base is "Name.zip"
    valid_pattern = re.compile(r'(.+\.(zip|img|7z|tar|gz))(\.\d+)?$')
    
    newest_item = None
    for item in items:
        match = valid_pattern.search(item['title'])
        if match:
            newest_item = item
            break
            
    if not newest_item:
        return []
        
    base_match = valid_pattern.search(newest_item['title'])
    base_name = base_match.group(1) # e.g. "/.../Super Flasher.zip"
    
    # Collect all parts with the same base_name
    parts = []
    for item in items:
        match = valid_pattern.search(item['title'])
        if match and match.group(1) == base_name:
            parts.append({
                'title': item['title'],
                'link': item['link']
            })
            
    # Sort parts by title (so .001 comes before .002)
    parts.sort(key=lambda x: x['title'])
    
    return [p['link'] for p in parts]

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Find latest zip file(s) on SourceForge")
    parser.add_argument("-p", "--project", required=True, help="SourceForge project name")
    parser.add_argument("-f", "--folder", default="", help="Folder prefix to filter")
    parser.add_argument("--url-only", action="store_true")
    
    args = parser.parse_args()
    links = find_latest_sf_files(args.project, args.folder)
    
    if links:
        output = " ".join(links)
        if args.url_only:
            print(output)
            if os.getenv('GITHUB_OUTPUT'):
                with open(os.getenv('GITHUB_OUTPUT'), 'a') as f:
                    f.write(f"ota_url={output}\n")
        else:
            print(f"Found {len(links)} parts:")
            for l in links:
                print(l)
    else:
        print("No file found.", file=sys.stderr)
        sys.exit(1)
