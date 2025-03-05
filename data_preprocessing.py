import pandas as pd
import googlemaps
from time import sleep
import folium
from folium import plugins
import webbrowser
import os
from pathlib import Path
import re

# Get the user's home directory and create a temporary directory
home_dir = str(Path.home())
temp_dir = os.path.join(home_dir, 'fuel_prices_temp')
os.makedirs(temp_dir, exist_ok=True)

# Initialize Google Maps client
gmaps = googlemaps.Client(key='google-maps-key')

# Read the CSV file from the original location
current_dir = os.path.dirname(os.path.abspath(__file__))
csv_path = os.path.join(current_dir, 'data', 'fuel-prices-for-be-assessment.csv')
df = pd.read_csv(csv_path)

# Display initial dataset info
print("\nInitial Dataset Info:")
print(f"Total number of rows: {len(df)}")

# Find and display duplicates
duplicates = df[df.duplicated(['OPIS Truckstop ID'], keep=False)]
print("\nDuplicate entries found (showing first few):")
print(duplicates.sort_values('OPIS Truckstop ID').head(10))

# Count how many OPIS Truckstop IDs have duplicates
duplicate_counts = df['OPIS Truckstop ID'].value_counts()
duplicate_stations = duplicate_counts[duplicate_counts > 1]
print(f"\nNumber of OPIS Truckstop IDs with multiple entries: {len(duplicate_stations)}")

# Group by OPIS Truckstop ID and calculate mean price
df_grouped = df.groupby('OPIS Truckstop ID').agg({
    'Truckstop Name': 'first',
    'Address': 'first',
    'City': 'first',
    'State': 'first',
    'Rack ID': 'first',
    'Retail Price': 'mean'
}).reset_index()

print("\nAfter grouping:")
print(f"Total number of rows: {len(df_grouped)}")

# After grouping the data, check for existing processed data
processed_file = os.path.join(current_dir, 'data', 'fuel_prices_processed.csv')

# Create data directory if it doesn't exist
os.makedirs(os.path.join(current_dir, 'data'), exist_ok=True)

# Try to load existing processed data
if os.path.exists(processed_file):
    print(f"\nLoading existing processed data from {processed_file}...")
    existing_data = pd.read_csv(processed_file)
    # Create a dictionary of existing coordinates
    existing_coords = existing_data.set_index('OPIS Truckstop ID')[['latitude', 'longitude', 'cleaned_name']].to_dict('index')
    print(f"Found {len(existing_coords)} existing locations")
else:
    print(f"\nNo existing processed data found. Will create new file at {processed_file}")
    existing_coords = {}

def clean_business_name(name):
    # Remove only numbers that come after #
    name = re.sub(r'#\d+', '', name)
    return name.strip()

# Function to get coordinates for an address
def get_coordinates(row):
    try:
        # Check if we already have coordinates for this location
        if row['OPIS Truckstop ID'] in existing_coords:
            existing = existing_coords[row['OPIS Truckstop ID']]
            print(f"\nUsing existing coordinates for {row['Truckstop Name']}")
            return pd.Series({
                'latitude': existing['latitude'],
                'longitude': existing['longitude'],
                'geocoding_query': None,  # We don't have the original query
                'cleaned_name': existing['cleaned_name'],
                'is_new_geocoding': False
            })

        # If not, proceed with geocoding
        truckstop_name = clean_business_name(row['Truckstop Name'])
        city = row['City'].strip()
        state = row['State'].strip()
        
        search_query = f"{truckstop_name}, {city}, {state}, USA"
        
        print(f"\nProcessing new location: {search_query}")
        print(f"Original name: {row['Truckstop Name']}")
        print(f"Cleaned name: {truckstop_name}")
        
        result = gmaps.geocode(search_query)
        
        if result:
            location = result[0]['geometry']['location']
            print(f"Successfully geocoded: {search_query}")
            print(f"Coordinates: {location['lat']}, {location['lng']}")
            return pd.Series({
                'latitude': location['lat'], 
                'longitude': location['lng'],
                'geocoding_query': search_query,
                'cleaned_name': truckstop_name,
                'is_new_geocoding': True
            })
        else:
            print(f"No results found for: {search_query}")
            return pd.Series({
                'latitude': None, 
                'longitude': None,
                'geocoding_query': None,
                'cleaned_name': truckstop_name,
                'is_new_geocoding': True
            })
            
    except Exception as e:
        print(f"Error geocoding: {search_query if 'search_query' in locals() else ''}")
        print(f"Error message: {str(e)}")
        return pd.Series({
            'latitude': None, 
            'longitude': None,
            'geocoding_query': None,
            'cleaned_name': truckstop_name if 'truckstop_name' in locals() else None,
            'is_new_geocoding': True
        })
    # finally:
    #     # Sleep to respect API rate limits (only for new geocoding)
    #     if 'is_new_geocoding' not in locals() or is_new_geocoding:
    #         sleep(0.1)

# Process the data
print("\nProcessing locations...")
df_test = df_grouped.copy()  # Process all rows instead of just head(50)
df_test[['latitude', 'longitude', 'geocoding_query', 'cleaned_name', 'is_new_geocoding']] = df_test.apply(get_coordinates, axis=1)

# Print test results summary
new_geocodes = df_test['is_new_geocoding'].sum()
print("\nResults:")
print(f"Total locations processed: {len(df_test)}")
print(f"Existing locations reused: {len(df_test) - new_geocodes}")
print(f"New locations geocoded: {new_geocodes}")
print(f"Successfully geocoded: {df_test['latitude'].notna().sum()} addresses")
print(f"Failed to geocode: {df_test['latitude'].isna().sum()} addresses")

# Save the complete processed dataframe
processed_df = df_test.copy()
processed_df['processed_date'] = pd.Timestamp.now().strftime('%Y-%m-%d')
processed_df['geocoding_success'] = processed_df['latitude'].notna()

# Save to the main processed file
processed_df.to_csv(processed_file, index=False)
print(f"\nProcessed data saved to '{processed_file}'")

# Create a map centered on the mean coordinates of successful geocodes
center_lat = df_test[df_test['latitude'].notna()]['latitude'].mean()
center_lng = df_test[df_test['latitude'].notna()]['longitude'].mean()
m = folium.Map(location=[center_lat, center_lng], zoom_start=4)

# Add marker clusters to handle large number of markers efficiently
marker_cluster = plugins.MarkerCluster().add_to(m)

# Add a marker for each location
for idx, row in df_test.iterrows():
    if pd.notna(row['latitude']) and pd.notna(row['longitude']):  # Only add markers for successful geocodes
        # Create popup content
        popup_content = f"""
        <b>{row['Truckstop Name']}</b><br>
        <i>Cleaned name: {row['cleaned_name']}</i><br>
        Address: {row['Address']}<br>
        {row['City']}, {row['State']}<br>
        <div style="background-color: #f0f0f0; padding: 5px; margin: 5px 0;">
        <b>Coordinates:</b><br>
        Lat: {row['latitude']:.6f}<br>
        Lng: {row['longitude']:.6f}
        </div>
        Fuel Price: ${row['Retail Price']:.3f}
        """
        
        # Add marker with popup
        folium.Marker(
            location=[row['latitude'], row['longitude']],
            popup=folium.Popup(popup_content, max_width=300),
            tooltip=row['cleaned_name'],
            icon=folium.Icon(color='red', icon='info-sign')
        ).add_to(marker_cluster)

# Add a legend
legend_html = '''
<div style="position: fixed; 
            bottom: 50px; left: 50px; width: 150px; height: 90px; 
            border:2px solid grey; z-index:9999; 
            background-color:white;
            opacity: 0.8;
            font-size: 14px;
            padding: 10px">
            <b>Legend</b><br>
            <i class="fa fa-map-marker fa-2x" style="color:red"></i> Truck Stop<br>
            </div>
'''
m.get_root().html.add_child(folium.Element(legend_html))

# Save the map
map_path = os.path.join(temp_dir, 'fuel_prices_map_100.html')
m.save(map_path)
print(f"\nInteractive map saved to '{map_path}'")

# Open the map in the default web browser
print(f"Opening map in your default web browser...")
webbrowser.open('file://' + os.path.abspath(map_path))

# Display summary of results
print("\nSummary of results:")
print("\nSample of successful geocodes:")
successful = df_test[df_test['latitude'].notna()].head()
print(successful[['OPIS Truckstop ID', 'Truckstop Name', 'cleaned_name', 'City', 'State', 'Retail Price', 'latitude', 'longitude']])

if df_test['latitude'].isna().any():
    print("\nSample of failed geocodes:")
    failed = df_test[df_test['latitude'].isna()].head()
    print(failed[['OPIS Truckstop ID', 'Truckstop Name', 'cleaned_name', 'City', 'State']]) 