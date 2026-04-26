## import commands 
import requests 
import pandas as pd 
import numpy as np
import time 

# station parameters
station = '8656483'  # Beaufort, NC 
product = 'hourly_height' 
datum = 'MLLW' 
units = 'metric' 
time_zone = 'GMT' 

 
# Initializing the data frame
years = range(1984, 2027) 
all_data = [] 

 
# For loop to get all the data from NOAA
for year in years: 
    url = ( 
        f"https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?" 
        f"begin_date={year}0101&end_date={year}1231" 
        f"&station={station}&product={product}&datum={datum}" 
        f"&units={units}&time_zone={time_zone}&application=web_services&format=json" 
    ) 
    response = requests.get(url) 
    data = response.json() 
    if 'data' in data: 
        df = pd.DataFrame(data['data']) 
        df['year'] = year 
        all_data.append(df) 
        print(f"Downloaded {year}") 
    else: 
        print(f"No data for {year}: {data.get('error', 'unknown error')}") 
    time.sleep(1)  # be polite to the API 

tides = pd.concat(all_data, ignore_index=True) 
tides.rename(columns={'t': 'datetime', 'v': 'water_level_m'}, inplace=True) 
tides['datetime'] = pd.to_datetime(tides['datetime']) 
tides['water_level_m'] = pd.to_numeric(tides['water_level_m'], errors='coerce') 

tides.to_csv('beaufort_tides_1984_2026.csv', index=False) 
print("Done — saved to beaufort_tides_1984_2026.csv") 

# Load GEE MNDWI data
mndwi_file_path = "O:\\ide_project\\Data\\Remote_Sensing_Data\\SharkIsland_MNDWI_TimeSeries_LatLong.csv"
mndwi = pd.read_csv(mndwi_file_path)
print(mndwi.head())

# Load NOAA tide data
tides_file_path = "O:\\ide_project\\Scripts\\beaufort_tides_1984_2026.csv"
Beaufort_tides = pd.read_csv(tides_file_path)
print(Beaufort_tides.head())

# Set the tidal data to noon UTC as a neutral midpoint for image acquistion 
mndwi['datetime'] = pd.to_datetime(mndwi['date'], utc=True)

# Tide data is hourly and already in GMT from the API download
Beaufort_tides['datetime'] = pd.to_datetime(Beaufort_tides['datetime'], utc=True)

print("MNDWI date range:", mndwi['datetime'].min(), "to", mndwi['datetime'].max())
print("Tide date range:", Beaufort_tides['datetime'].min(), "to", Beaufort_tides['datetime'].max())

# Sort both dataframes by datetime
mndwi = mndwi.sort_values('datetime').reset_index(drop=True)
Beaufort_tides = Beaufort_tides.sort_values('datetime').reset_index(drop=True)

# Merge each MNDWI observation to the nearest tide record within a 1-hour window
merged = pd.merge_asof(
    mndwi,
    Beaufort_tides[['datetime', 'water_level_m']],
    on='datetime',
    direction='nearest',
    tolerance=pd.Timedelta('1hour')
)

print(f"MNDWI observations: {len(mndwi)}")
print(f"Successfully matched with tide: {merged['water_level_m'].notna().sum()}")
print(f"Unmatched (outside 1hr window): {merged['water_level_m'].isna().sum()}")

# Add island presence classification based on MNDWI threshold of 0.2
merged['island_status'] = merged['MNDWI'].apply(
    lambda x: 'exposed' if x < 0.2 else ('submerged' if x >= 0.2 else 'unknown')
)

# Classifying tidal stages 
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

print(merged['tidal_stage'].value_counts())

# Plot MNDWI against water level 
import matplotlib.pyplot as plt

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8))

# Time series of MNDWI
ax1.scatter(merged['date'], merged['MNDWI'], 
            c=merged['water_level_m'], cmap='Blues', s=20, alpha=0.7)
ax1.axhline(0, color='red', linestyle='--', linewidth=1, label='MNDWI = 0 threshold')
ax1.set_ylabel('MNDWI')
ax1.set_title('MNDWI Time Series — Shark Island (colored by tidal height)')
ax1.legend()

# Scatter of MNDWI vs water level
ax2.scatter(merged['water_level_m'], merged['MNDWI'], 
            s=15, alpha=0.5, color='steelblue')
ax2.axhline(0, color='red', linestyle='--', linewidth=1)
ax2.set_xlabel('Water Level (m above MLLW)')
ax2.set_ylabel('MNDWI')
ax2.set_title('MNDWI vs Tidal Stage')

plt.tight_layout()
plt.savefig('mndwi_tidal_check.png', dpi=150)
plt.show()

# Export 
merged.to_csv('SharkIsland_MNDWI_TidalMerged_GeoRef.csv', index=False)
print(merged[['date', 'MNDWI', 'longitude', 'latitude', 
              'water_level_m', 'island_status']].head(10))