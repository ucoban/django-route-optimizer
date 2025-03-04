"""
Fuel optimization utility functions for the route optimizer API.
"""
import logging
from typing import Dict, List, Tuple, Any
from geopy.distance import geodesic
from django.core.cache import cache
from api.models import FuelData

# Configure logging
logger = logging.getLogger(__name__)

# Cache timeout (1 hour)
CACHE_TIMEOUT = 60 * 60

class FuelOptimizer:
    """
    Service for optimizing fuel stops along a route.
    """
    def __init__(self, miles_per_gallon: float = 10.0, segment_distance: float = 400.0, search_radius: float = 15.0):
        """
        Initialize the fuel optimizer.
        
        Args:
            miles_per_gallon: Miles per gallon for the vehicle.
            segment_distance: Maximum distance between fuel stops in miles.
            search_radius: Radius to search for fuel stations in miles.
        """
        self.miles_per_gallon = miles_per_gallon
        self.segment_distance = segment_distance
        self.search_radius = search_radius
        self.buffer_degrees = search_radius / 69  # Convert miles to approximate degrees (1 degree ≈ 69 miles)
    
    def calculate_check_points(self, route_distance: float, steps: List[Dict[str, Any]], route_geometry: List[List[float]]) -> List[Tuple[float, float]]:
        """
        Calculate check points along the route where we should look for fuel stations.
        
        Args:
            route_distance: Total route distance in miles.
            steps: List of steps along the route.
            route_geometry: List of coordinates along the route.
            
        Returns:
            List of check points as (latitude, longitude) tuples.
        """
        check_points = []
        cumulative_distance = 0
        
        for step in steps:
            cumulative_distance += step['distance']
            if cumulative_distance >= self.segment_distance:
                key_index = step['way_points'][-1]
                check_points.append((route_geometry[key_index][1], route_geometry[key_index][0]))
                cumulative_distance = 0
        
        # Add a final check point if we've accumulated a significant distance
        if cumulative_distance > self.segment_distance / 2 and steps:
            last_step = steps[-1]
            key_index = last_step['way_points'][-1]
            check_points.append((route_geometry[key_index][1], route_geometry[key_index][0]))
        
        return check_points
    
    def find_stations_in_bounding_box(self, check_points: List[Tuple[float, float]]) -> List[Dict[str, Any]]:
        """
        Find all stations within the bounding box of the check points.
        
        Args:
            check_points: List of check points as (latitude, longitude) tuples.
            
        Returns:
            List of stations within the bounding box.
        """
        if not check_points:
            return []
        
        # Calculate the bounding box for all check points at once
        check_lats = [point[0] for point in check_points]
        check_lngs = [point[1] for point in check_points]
        min_lat, max_lat = min(check_lats), max(check_lats)
        min_lng, max_lng = min(check_lngs), max(check_lngs)
        
        # Create a cache key for this bounding box
        cache_key = f"stations_bbox_{min_lat:.4f}_{min_lng:.4f}_{max_lat:.4f}_{max_lng:.4f}"
        
        # Try to get the stations from cache
        cached_stations = cache.get(cache_key)
        if cached_stations:
            logger.info("Stations retrieved from cache")
            return cached_stations
        
        # Get all stations within the bounding box in a single query
        bounded_stations = list(FuelData.objects.filter(
            latitude__range=(min_lat - self.buffer_degrees, max_lat + self.buffer_degrees),
            longitude__range=(min_lng - self.buffer_degrees, max_lng + self.buffer_degrees)
        ).values('id', 'truckstop_name', 'retail_price', 'latitude', 'longitude', 'city', 'state'))
        
        # Cache the stations
        cache.set(cache_key, bounded_stations, CACHE_TIMEOUT)
        
        logger.info(f"Found {len(bounded_stations)} stations in bounding box")
        return bounded_stations
    
    def find_nearest_cheapest_stations(self, check_points: List[Tuple[float, float]], bounded_stations: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], float]:
        """
        Find the nearest and cheapest stations for each check point.
        
        Args:
            check_points: List of check points as (latitude, longitude) tuples.
            bounded_stations: List of stations within the bounding box.
            
        Returns:
            Tuple of (list of optimal fuel stops, total fuel cost).
        """
        fuel_stops = []
        total_cost = 0
        
        for check_point in check_points:
            logger.debug(f"Checking stations near point: {check_point}")
            
            # Filter stations by approximate distance first (faster than geodesic)
            nearby_stations = []
            check_lat, check_lng = check_point
            
            for station in bounded_stations:
                # Quick rectangular distance check (much faster than geodesic)
                lat_diff = abs(station['latitude'] - check_lat)
                lng_diff = abs(station['longitude'] - check_lng)
                
                # If within rough bounds (slightly larger than actual radius)
                if lat_diff <= self.buffer_degrees and lng_diff <= self.buffer_degrees:
                    # Now do accurate geodesic calculation only for close stations
                    distance = geodesic(check_point, (station['latitude'], station['longitude'])).miles
                    if distance <= self.search_radius:
                        nearby_stations.append((distance, float(station['retail_price']), station))
            
            # Find the cheapest station if any were found
            if nearby_stations:
                # Sort by price first, then by distance if prices are equal
                cheapest_stations = sorted(nearby_stations, key=lambda x: (x[1], x[0]))
                distance, price, cheapest_station = cheapest_stations[0]
                
                logger.debug(f"Selected cheapest: {cheapest_station['truckstop_name']} at ${price:.2f}")
                
                fuel_stops.append({
                    'name': cheapest_station['truckstop_name'],
                    'price': cheapest_station['retail_price'],
                    'location': {
                        'lat': cheapest_station['latitude'],
                        'lng': cheapest_station['longitude']
                    },
                    'city': cheapest_station['city'],
                    'state': cheapest_station['state'],
                    'distance_from_route': distance
                })
                total_cost += (self.segment_distance / self.miles_per_gallon) * price
            else:
                logger.warning(f"No stations found within {self.search_radius} miles of {check_point}")
        
        return fuel_stops, total_cost
    
    def optimize_fuel_stops(self, route_distance: float, steps: List[Dict[str, Any]], route_geometry: List[List[float]]) -> Tuple[List[Dict[str, Any]], float, List[Tuple[float, float]]]:
        """
        Calculate optimal fuel stops along a route.
        
        Args:
            route_distance: Total route distance in miles.
            steps: List of steps along the route.
            route_geometry: List of coordinates along the route.
            
        Returns:
            Tuple of (list of optimal fuel stops, total fuel cost, list of check points).
        """
        logger.info("Calculating fuel stops and costs...")
        
        # Calculate check points
        check_points = self.calculate_check_points(route_distance, steps, route_geometry)
        
        if not check_points:
            logger.warning("No check points found along the route")
            return [], 0, []
        
        # Find stations in bounding box
        bounded_stations = self.find_stations_in_bounding_box(check_points)
        
        # Find nearest cheapest stations
        fuel_stops, total_cost = self.find_nearest_cheapest_stations(check_points, bounded_stations)
        
        # Log summary
        logger.info(f"Total fuel stops: {len(fuel_stops)}")
        logger.info(f"Total estimated cost: ${total_cost:.2f}")
        
        return fuel_stops, total_cost, check_points 