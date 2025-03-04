"""
Routing utility functions for the route optimizer API.
"""
import os
import logging
from typing import Dict, List, Tuple, Any
from openrouteservice import client
from django.conf import settings
from django.core.cache import cache

# Configure logging
logger = logging.getLogger(__name__)

# Cache timeout (24 hours)
CACHE_TIMEOUT = 60 * 60 * 24

class RoutingService:
    """
    Service for handling routing calculations using OpenRouteService.
    """
    def __init__(self, api_key: str = None):
        """
        Initialize the routing service with the API key.
        
        Args:
            api_key: OpenRouteService API key. If None, uses the key from settings.
        """
        self.api_key = api_key or settings.OPENROUTE_API_KEY
        self.client = client.Client(key=self.api_key)
    
    def get_route(self, start: Dict[str, float], finish: Dict[str, float]) -> Dict[str, Any]:
        """
        Get a route between two points.
        
        Args:
            start: Dictionary with 'lat' and 'lng' keys for the starting point.
            finish: Dictionary with 'lat' and 'lng' keys for the ending point.
            
        Returns:
            Dictionary with route data.
            
        Raises:
            ValueError: If the route cannot be calculated.
        """
        # Create a cache key based on the start and finish coordinates
        cache_key = f"route_{start['lat']}_{start['lng']}_{finish['lat']}_{finish['lng']}"
        
        # Try to get the route from cache
        cached_route = cache.get(cache_key)
        if cached_route:
            logger.info("Route retrieved from cache")
            return cached_route
        
        # Prepare the request payload
        payload = {
            'coordinates': [
                [float(start['lng']), float(start['lat'])],
                [float(finish['lng']), float(finish['lat'])]
            ],
            'format': 'geojson',
            'units': 'mi'  # Use miles as the unit for distance
        }
        
        try:
            # Make the API request
            response = self.client.directions(**payload)
            
            # Check for successful response
            if 'features' not in response:
                raise ValueError("Failed to fetch route data")
            
            # Cache the response
            cache.set(cache_key, response, CACHE_TIMEOUT)
            
            return response
        except Exception as e:
            logger.error(f"Error fetching route: {str(e)}")
            raise ValueError(f"Failed to fetch route data: {str(e)}")
    
    def extract_route_info(self, route_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract useful information from the route data.
        
        Args:
            route_data: Route data from OpenRouteService.
            
        Returns:
            Dictionary with extracted route information.
        """
        try:
            feature = route_data['features'][0]
            properties = feature['properties']
            geometry = feature['geometry']
            
            # Extract route distance and duration
            distance = properties['segments'][0]['distance']
            duration = properties['segments'][0]['duration']
            
            # Extract steps
            steps = properties['segments'][0]['steps']
            
            # Extract coordinates
            coordinates = geometry['coordinates']
            
            return {
                'distance': distance,
                'duration': duration,
                'steps': steps,
                'coordinates': coordinates
            }
        except (KeyError, IndexError) as e:
            logger.error(f"Error extracting route info: {str(e)}")
            raise ValueError(f"Invalid route data format: {str(e)}") 