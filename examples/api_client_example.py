#!/usr/bin/env python
"""
Example client for the Route Optimizer API.

This script demonstrates how to use the Route Optimizer API to:
1. Get fuel prices
2. Calculate a route using coordinates
3. Calculate a route using location names
"""
import requests
import json
import webbrowser
from pprint import pprint

# Base URL for the API
BASE_URL = "http://localhost:8000/api"

def get_fuel_prices(limit=5):
    """Get a list of fuel prices."""
    url = f"{BASE_URL}/fuel-prices/?limit={limit}"
    response = requests.get(url)
    
    if response.status_code == 200:
        print(f"Successfully retrieved {len(response.json())} fuel prices:")
        pprint(response.json())
    else:
        print(f"Error: {response.status_code}")
        print(response.text)

def calculate_route_by_coordinates(start_lat, start_lng, finish_lat, finish_lng):
    """Calculate a route using coordinates."""
    url = f"{BASE_URL}/route/"
    data = {
        "start": {"lat": start_lat, "lng": start_lng},
        "finish": {"lat": finish_lat, "lng": finish_lng}
    }
    
    response = requests.post(url, json=data)
    
    if response.status_code == 200:
        result = response.json()
        print("\nRoute calculated successfully:")
        print(f"Distance: {result['route']['distance']:.1f} {result['route']['unit']}")
        print(f"Duration: {result['route']['duration'] / 3600:.1f} hours")
        print(f"Total fuel cost: ${result['fuel']['total_cost']:.2f}")
        
        print("\nFuel stops:")
        for stop in result['fuel']['stops']:
            print(f"- {stop['name']} in {stop['city']}, {stop['state']}: ${float(stop['price']):.2f}/gallon")
        
        # Open the map in a browser
        map_url = f"http://localhost:8000{result['map_url']}"
        print(f"\nMap URL: {map_url}")
        webbrowser.open(map_url)
        
        return result
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
        return None

def calculate_route_by_names(start_location, finish_location):
    """Calculate a route using location names."""
    url = f"{BASE_URL}/route-by-name/"
    data = {
        "start_location": start_location,
        "finish_location": finish_location
    }
    
    response = requests.post(url, json=data)
    
    if response.status_code == 200:
        result = response.json()
        print("\nRoute calculated successfully:")
        print(f"Start: {result['locations']['start']['name']} ({result['locations']['start']['coordinates']['lat']}, {result['locations']['start']['coordinates']['lng']})")
        print(f"Finish: {result['locations']['finish']['name']} ({result['locations']['finish']['coordinates']['lat']}, {result['locations']['finish']['coordinates']['lng']})")
        print(f"Distance: {result['route']['distance']:.1f} {result['route']['unit']}")
        print(f"Duration: {result['route']['duration'] / 3600:.1f} hours")
        print(f"Total fuel cost: ${result['fuel']['total_cost']:.2f}")
        
        print("\nFuel stops:")
        for stop in result['fuel']['stops']:
            print(f"- {stop['name']} in {stop['city']}, {stop['state']}: ${float(stop['price']):.2f}/gallon")
        
        # Open the map in a browser
        map_url = f"http://localhost:8000{result['map_url']}"
        print(f"\nMap URL: {map_url}")
        webbrowser.open(map_url)
        
        return result
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
        return None

if __name__ == "__main__":
    print("Route Optimizer API Client Example\n")
    
    # Example 1: Get fuel prices
    print("Example 1: Getting fuel prices")
    get_fuel_prices(limit=3)
    
    # Example 2: Calculate route by coordinates
    print("\nExample 2: Calculating route by coordinates (New York to Chicago)")
    calculate_route_by_coordinates(
        start_lat=40.7128, start_lng=-74.0060,  # New York
        finish_lat=41.8781, finish_lng=-87.6298  # Chicago
    )
    
    # Example 3: Calculate route by names
    print("\nExample 3: Calculating route by names (Los Angeles to San Francisco)")
    calculate_route_by_names(
        start_location="Los Angeles, CA",
        finish_location="San Francisco, CA"
    ) 