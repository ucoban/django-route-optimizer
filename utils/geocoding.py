"""
Geocoding utility functions for the route optimizer API.
"""
import logging
from typing import Dict, Optional, Tuple
import requests
from django.core.cache import cache
from django.conf import settings

# Configure logging
logger = logging.getLogger(__name__)

# Cache timeout (7 days)
CACHE_TIMEOUT = 60 * 60 * 24 * 7

class GeocodingService:
    """
    Service for geocoding location names to coordinates.
    """
    def __init__(self):
        """
        Initialize the geocoding service.
        """
        # Using OpenStreetMap Nominatim API for geocoding
        self.api_url = "https://nominatim.openstreetmap.org/search"
        self.headers = {
            "User-Agent": "RouteOptimizerAPI/1.0",
        }
    
    def geocode(self, location_name: str, country_code: str = "us") -> Optional[Dict[str, float]]:
        """
        Convert a location name to coordinates.
        
        Args:
            location_name: Name of the location to geocode.
            country_code: Country code to limit results (default: "us").
            
        Returns:
            Dictionary with 'lat' and 'lng' keys, or None if geocoding failed.
        """
        # Clean the location name
        location_name = location_name.strip()
        
        # Create a cache key
        cache_key = f"geocode_{location_name}_{country_code}"
        
        # Try to get the coordinates from cache
        cached_coords = cache.get(cache_key)
        if cached_coords:
            logger.info(f"Coordinates for '{location_name}' retrieved from cache")
            return cached_coords
        
        # Prepare the request parameters
        params = {
            "q": location_name,
            "format": "json",
            "limit": 1,
            "countrycodes": country_code,
            "addressdetails": 1,
        }
        
        try:
            # Make the API request
            response = requests.get(self.api_url, params=params, headers=self.headers, timeout=5)
            response.raise_for_status()
            
            # Parse the response
            data = response.json()
            
            # Check if we got any results
            if not data:
                logger.warning(f"No geocoding results found for '{location_name}'")
                return None
            
            # Extract the coordinates
            result = data[0]
            coordinates = {
                "lat": float(result["lat"]),
                "lng": float(result["lon"])
            }
            
            # Cache the coordinates
            cache.set(cache_key, coordinates, CACHE_TIMEOUT)
            
            logger.info(f"Successfully geocoded '{location_name}' to {coordinates}")
            return coordinates
            
        except Exception as e:
            logger.error(f"Error geocoding '{location_name}': {str(e)}")
            return None
    
    def batch_geocode(self, locations: list) -> Dict[str, Dict[str, float]]:
        """
        Geocode multiple locations at once.
        
        Args:
            locations: List of location names to geocode.
            
        Returns:
            Dictionary mapping location names to coordinate dictionaries.
        """
        results = {}
        
        for location in locations:
            coords = self.geocode(location)
            if coords:
                results[location] = coords
        
        return results 