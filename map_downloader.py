import requests
from PIL import Image
import io
import math
import time
import os
from geopy.distance import distance
from concurrent.futures import ThreadPoolExecutor, as_completed

def deg2num(lat_deg, lon_deg, zoom):
    lat_rad = math.radians(lat_deg)
    n = 1 << zoom
    x = int((lon_deg + 180.0) / 360.0 * n)
    y = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return x, y

def num2deg(x, y, zoom):
    n = 1 << zoom
    lon = x / n * 360.0 - 180.0
    lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / n))))
    return lat, lon

def get_bounding_box(center_lat, center_lon, radius_km):
    north_point = distance(kilometers=radius_km).destination((center_lat, center_lon), bearing=0)
    south_point = distance(kilometers=radius_km).destination((center_lat, center_lon), bearing=180)
    east_point = distance(kilometers=radius_km).destination((center_lat, center_lon), bearing=90)
    west_point = distance(kilometers=radius_km).destination((center_lat, center_lon), bearing=270)
    return {
        'north': north_point.latitude,
        'south': south_point.latitude,
        'east': east_point.longitude,
        'west': west_point.longitude
    }

def calculate_tiles_info(center_lat, center_lon, radius_km, zoom):
    """پیش‌محاسبه تعداد تایل‌ها و ابعاد تصویر بدون شروع دانلود واقعی"""
    bbox = get_bounding_box(center_lat, center_lon, radius_km)
    x_min, y_max = deg2num(bbox['north'], bbox['west'], zoom)
    x_max, y_min = deg2num(bbox['south'], bbox['east'], zoom)
    
    tiles_x = abs(x_max - x_min) + 1
    tiles_y = abs(y_max - y_min) + 1
    return tiles_x * tiles_y, tiles_x * 256, tiles_y * 256

def download_one_tile(session, tile_x, tile_y, zoom, engine, max_retries=3):
    engines = {
        "Esri Satellite": f"https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{zoom}/{tile_y}/{tile_x}",
        "Google Satellite": f"https://mt1.google.com/vt/lyrs=s&x={tile_x}&y={tile_y}&z={zoom}",
        "OpenStreetMap": f"https://tile.openstreetmap.org/{zoom}/{tile_x}/{tile_y}.png"
    }
    
    url = engines.get(engine, engines["Esri Satellite"])
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    for attempt in range(max_retries):
        try:
            response = session.get(url, headers=headers, timeout=(5, 8))
            if response.status_code == 200:
                return Image.open(io.BytesIO(response.content))
            time.sleep(0.3 * (attempt + 1))
        except Exception:
            time.sleep(0.3 * (attempt + 1))
    return None

def download_map(
    center_lat, center_lon, radius_km, zoom=18, 
    output_file="map.webp", max_workers=16, 
    target_width=2000, quality=85, engine="Esri Satellite",
    progress_callback=None, cancel_event=None
):
    if progress_callback:
        progress_callback(2, "Initializing Advanced Sync Core...")

    bbox = get_bounding_box(center_lat, center_lon, radius_km)
    x_min, y_max = deg2num(bbox['north'], bbox['west'], zoom)
    x_max, y_min = deg2num(bbox['south'], bbox['east'], zoom)

    x_start, x_end = min(x_min, x_max), max(x_min, x_max)
    y_start, y_end = min(y_min, y_max), max(y_min, y_max)

    tiles_x = x_end - x_start + 1
    tiles_y = y_end - y_start + 1
    total_tiles = tiles_x * tiles_y

    tasks = [(i, j, x_start + i, y_start + j) for i in range(tiles_x) for j in range(tiles_y)]
    
    tile_size = 256
    final_img = Image.new('RGB', (tiles_x * tile_size, tiles_y * tile_size))
    
    downloaded = 0
    failed = 0
    session = requests.Session()
    
    if progress_callback:
        progress_callback(10, f"Downloading 0/{total_tiles} matrix tiles...")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_task = {executor.submit(download_one_tile, session, tx, ty, zoom, engine): (i, j) for i, j, tx, ty in tasks}
        
        for future in as_completed(future_to_task):
            if cancel_event and cancel_event.is_set():
                raise Exception("Process terminated by Operator.")
                
            i, j = future_to_task[future]
            try:
                img = future.result()
                if img:
                    final_img.paste(img, (i * tile_size, j * tile_size))
                    downloaded += 1
                else:
                    failed += 1
            except Exception:
                failed += 1

            total_done = downloaded + failed
            percent = 10 + int((total_done / total_tiles) * 75)
            if progress_callback and total_done % max(1, total_tiles // 10) == 0:
                progress_callback(percent, f"Sync: {downloaded} Secured | {failed} Dropped")

    if progress_callback:
        progress_callback(85, "Cropping bounding box matrix...")

    lat_top, lon_left = num2deg(x_start, y_start, zoom)
    lat_bottom, lon_right = num2deg(x_end + 1, y_end + 1, zoom)

    pixel_per_lon = (tiles_x * tile_size) / (lon_right - lon_left)
    pixel_per_lat = (tiles_y * tile_size) / (lat_top - lat_bottom)

    c_px = (center_lon - lon_left) * pixel_per_lon
    c_py = (lat_top - center_lat) * pixel_per_lat

    r_px = (radius_km / (111.0 * math.cos(math.radians(center_lat)))) * pixel_per_lon
    r_py = (radius_km / 111.0) * pixel_per_lat

    left = max(int(c_px - r_px), 0)
    top = max(int(c_py - r_py), 0)
    right = min(int(c_px + r_px), tiles_x * tile_size)
    bottom = min(int(c_py + r_py), tiles_y * tile_size)

    cropped_img = final_img.crop((left, top, right, bottom))

    if cropped_img.size[0] > target_width:
        h = int(cropped_img.size[1] * (target_width / cropped_img.size[0]))
        cropped_img = cropped_img.resize((target_width, h), Image.Resampling.LANCZOS)

    if progress_callback:
        progress_callback(95, "Compiling image assets...")

    ext = output_file.split('.')[-1].lower()
    fmt_m = {'png': 'PNG', 'jpg': 'JPEG', 'jpeg': 'JPEG', 'webp': 'WEBP'}
    
    save_args = {'format': fmt_m.get(ext, 'PNG'), 'optimize': True}
    if ext in ['jpg', 'jpeg', 'webp']:
        save_args['quality'] = quality

    cropped_img.save(output_file, **save_args)
    
    return {
        'file_path': output_file,
        'size_mb': os.path.getsize(output_file) / (1024 * 1024),
        'dimensions': cropped_img.size,
        'engine': engine
    }