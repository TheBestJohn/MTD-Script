import os
from dotenv import load_dotenv
import requests
from math import log, tan, cos, pi
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed

load_dotenv()

def load_regions_from_env():
    regions_str = os.getenv("REGIONS", "")
    regions = {}
    if regions_str:
        for region in regions_str.split(";"):
            if region.strip():
                parts = region.split(":")
                if len(parts) == 2:
                    name = parts[0].strip()
                    values = tuple(float(v.strip()) for v in parts[1].split(","))
                    min_lat, min_lon, max_lat, max_lon = values
                    
                    # Ensure min values are actually less than max values
                    if min_lon > max_lon:
                        print(f"Warning: min_lon ({min_lon}) > max_lon ({max_lon}) for region {name}, swapping")
                        min_lon, max_lon = max_lon, min_lon
                    if min_lat > max_lat:
                        print(f"Warning: min_lat ({min_lat}) > max_lat ({max_lat}) for region {name}, swapping")
                        min_lat, max_lat = max_lat, min_lat
                    
                    regions[name] = (min_lat, min_lon, max_lat, max_lon)
    return regions

# Define the bounding boxes and zoom levels. Below are random examples.
regions = load_regions_from_env()
print(regions)
WORKERS=os.getenv("WORKERS", 10)
zoom_levels = range(int(os.getenv("MINZOOM", 1)), int(os.getenv("MAXZOOM", 14))+1)  # Defaults to zoom levels 1 to 14

# mapstyle = "cycle"
# mapstyle = "transport"
# mapstyle = "landscape"
# mapstyle = "outdoors"
# mapstyle = "transport-dark"
# mapstyle = "spinal-map"
# mapstyle = "pioneer"
mapstyle = "mobile-atlas"
# mapstyle = "neighbourhood"
# mapstyle = "atlas"

# API Key and output directory
api_key = os.getenv("API_KEY")
output_dir = "./maps"
os.makedirs(output_dir, exist_ok=True)

def lon2tilex(lon, zoom):
    return int((lon + 180.0) / 360.0 * (1 << zoom))

def lat2tiley(lat, zoom):
    return int((1.0 - log(tan(lat * pi / 180.0) + 1.0 / cos(lat * pi / 180.0)) / pi) / 2.0 * (1 << zoom))

def download_tile(zoom, region_name, x, y):
    url = f"https://tile.thunderforest.com/{mapstyle}/{zoom}/{x}/{y}.png?apikey={api_key}"
    tile_dir = os.path.join(output_dir, region_name, str(zoom), str(x))
    tile_path = os.path.join(tile_dir, f"{y}.png")

    if os.path.exists(tile_path):
        return

    os.makedirs(tile_dir, exist_ok=True)

    response = requests.get(url)
    if response.status_code == 200:
        with open(tile_path, "wb") as file:
            file.write(response.content)
    else:
        print(f"Failed to download tile {zoom}/{x}/{y}: {response.status_code} {response.reason}")

def main():
    total_tiles = 0

    for zoom in zoom_levels:
        for region_name, (min_lat, min_lon, max_lat, max_lon) in regions.items():
            start_x = lon2tilex(min_lon, zoom)
            end_x = lon2tilex(max_lon, zoom)
            start_y = lat2tiley(max_lat, zoom)
            end_y = lat2tiley(min_lat, zoom)
# 
            print(zoom)
            print(f"folders={end_x-start_x +1} tiles/folder = {end_y-start_y +1}" )
            print(f"{(end_x - start_x + 1) * (end_y - start_y + 1)} Tiles at Zoom level {zoom}")
            total_tiles += (end_x - start_x + 1) * (end_y - start_y + 1)

    print(total_tiles, "total tiles")


    with tqdm(total=total_tiles, desc="Downloading tiles") as pbar:
        for zoom in zoom_levels:
            for region_name, (min_lat, min_lon, max_lat, max_lon) in regions.items():
                start_x = lon2tilex(min_lon, zoom)
                end_x = lon2tilex(max_lon, zoom)
                start_y = lat2tiley(max_lat, zoom)
                end_y = lat2tiley(min_lat, zoom)
                
                tiles = [(x, y) for x in range(start_x, end_x + 1) for y in range(start_y, end_y + 1)]
                
                with ThreadPoolExecutor(max_workers=WORKERS) as executor:
                    futures = {executor.submit(download_tile, zoom, region_name, x, y): (x, y) for x, y in tiles}
                    for future in as_completed(futures):
                        x, y = futures[future]
                        pbar.set_description(f"📁:{x - start_x + 1}/{end_x-start_x +1} 🖼️:{y - start_y + 1}/{end_y-start_y +1} of 🔍:{zoom}")
                        pbar.update(1)

if __name__ == "__main__":
    main()
