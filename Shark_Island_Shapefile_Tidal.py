import geopandas as gpd
import pandas as pd

# Load the shapefile
island = "O:\\ide_project\\Data\\Remote_Sensing_Data\\SharkIsland_Extents_TimeSeries.shp"
SharkIsland = gpd.read_file(island)
print(SharkIsland.head())

# Load tidal data
tides_file_path = "O:\\ide_project\\Scripts\\beaufort_tides_1984_2026.csv"
Beaufort_tides = pd.read_csv(tides_file_path)
print(Beaufort_tides.head())

# Parse datetimes
SharkIsland['datetime'] = pd.to_datetime(SharkIsland['date'], utc=True)
Beaufort_tides['datetime'] = pd.to_datetime(Beaufort_tides['datetime'], utc=True)

# Sort for merge
SharkIsland = SharkIsland.sort_values('datetime').reset_index(drop=True)
Beaufort_tides = Beaufort_tides.sort_values('datetime').reset_index(drop=True)

# Nearest hour merge — same as before but on geodataframe
merged = pd.merge_asof(
    SharkIsland,
    Beaufort_tides[['datetime', 'water_level_m']],
    on='datetime',
    direction='nearest',
    tolerance=pd.Timedelta('1hour')
)

# Calculate area of each polygon in square meters
# First reproject to a projected CRS appropriate for NC
merged = merged.to_crs(epsg=32618)  # UTM Zone 18N
merged['area_m2'] = merged.geometry.area

# Classify tidal stage
def classify_tide(wl):
    if pd.isna(wl):
        return 'unknown'
    elif wl <= 0.2:
        return 'low'
    elif wl <= 0.6:
        return 'mid_low'
    elif wl <= 1.0:
        return 'mid_high'
    else:
        return 'high'

merged['tidal_stage'] = merged['water_level_m'].apply(classify_tide)

# Export back to shapefile for ArcGIS Pro
merged.to_file('SharkIsland_Extents_TidalMerged.shp')
print(f"Exported {len(merged)} features with tidal data attached")
print(merged[['date', 'area_m2', 'water_level_m', 'tidal_stage']].head(10))