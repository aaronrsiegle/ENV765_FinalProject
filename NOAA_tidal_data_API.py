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

# Load in data for joining process
import pandas as pd

# Load GEE MNDWI data
mndwi_file_path = "O:\\ide_project\\Data\Remote_Sensing_Data\\SharkIsland_MNDWI_TimeSeries.csv"
mndwi = pd.read_csv(mndwi_file_path)
print(mndwi.head())

# Load NOAA tide data
tides_file_path = "O:\\ide_project\\Scripts\\beaufort_tides_1984_2026.csv"
Beaufort_tides = pd.read_csv(mndwi_file_path)
print(Beaufort_tides.head())

# Set the tidal data to noon UTC as a neutral midpoint for image acquistion 
mndwi['datetime'] = pd.to_datetime(mndwi['date'], utc=True)

# Tide data is hourly and already in GMT from the API download
Beaufort_tides['datetime'] = pd.to_datetime(Beaufort_tides['date'], utc=True)

print("MNDWI date range:", mndwi['datetime'].min(), "to", mndwi['datetime'].max())
print("Tide date range:", Beaufort_tides['datetime'].min(), "to", Beaufort_tides['datetime'].max())

# Sort both dataframes by datetime — required for merge_asof
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