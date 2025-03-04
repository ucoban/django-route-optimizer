from django.shortcuts import render
from django.http import JsonResponse, HttpResponse, Http404
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt
import json
import os
import logging
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import FuelData
from utils.routing import RoutingService
from utils.fuel_optimization import FuelOptimizer
from utils.map_generator import MapGenerator
from utils.geocoding import GeocodingService
from .serializers import (
    FuelDataSerializer, 
    RouteRequestSerializer, 
    RouteResponseSerializer,
    RouteByNameRequestSerializer,
    RouteByNameResponseSerializer
)

# Configure logging
logger = logging.getLogger(__name__)

# Initialize services
routing_service = RoutingService()
fuel_optimizer = FuelOptimizer()
map_generator = MapGenerator()
geocoding_service = GeocodingService()

# Swagger parameters
fuel_prices_params = [
    openapi.Parameter(
        'limit', 
        openapi.IN_QUERY, 
        description="Maximum number of fuel prices to return", 
        type=openapi.TYPE_INTEGER,
        default=10
    )
]

route_params = [
    openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['start', 'finish'],
        properties={
            'start': openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'lat': openapi.Schema(type=openapi.TYPE_NUMBER),
                    'lng': openapi.Schema(type=openapi.TYPE_NUMBER),
                }
            ),
            'finish': openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'lat': openapi.Schema(type=openapi.TYPE_NUMBER),
                    'lng': openapi.Schema(type=openapi.TYPE_NUMBER),
                }
            ),
        }
    )
]

route_by_name_params = [
    openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=['start_location', 'finish_location'],
        properties={
            'start_location': openapi.Schema(type=openapi.TYPE_STRING),
            'finish_location': openapi.Schema(type=openapi.TYPE_STRING),
        }
    )
]

@swagger_auto_schema(
    method='get',
    operation_description="Get a list of fuel prices from truck stops across the USA",
    manual_parameters=fuel_prices_params,
    responses={
        200: openapi.Response(
            description="List of fuel prices",
            schema=FuelDataSerializer(many=True)
        ),
        500: "Server error"
    },
    tags=['fuel']
)
@api_view(['GET'])
@permission_classes([AllowAny])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
def fuel_prices(request):
    """
    Get a list of fuel prices from truck stops across the USA.
    
    This endpoint returns a list of fuel prices from various truck stops,
    which can be used to calculate optimal fuel stops along a route.
    
    Args:
        request: HTTP request with optional 'limit' parameter.
        
    Returns:
        JSON response with fuel price data.
    """
    try:
        # Get the limit from the request parameters
        limit = int(request.GET.get('limit', 10))  # Default limit is 10
        
        # Query the database
        fuel_data = FuelData.objects.all()[:limit]
        
        # Serialize the data
        serializer = FuelDataSerializer(fuel_data, many=True)
        
        return Response(serializer.data)
    except Exception as e:
        logger.error(f"Error fetching fuel prices: {str(e)}")
        return Response(
            {'error': f"Failed to fetch fuel prices: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@swagger_auto_schema(
    method='post',
    operation_description="Calculate an optimized route with fuel stops using coordinates",
    request_body=RouteRequestSerializer,
    responses={
        200: openapi.Response(
            description="Route data with optimized fuel stops",
            schema=RouteResponseSerializer
        ),
        400: "Invalid request parameters",
        500: "Server error"
    },
    tags=['routes']
)
@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
def route(request):
    """
    Calculate an optimized route with fuel stops using coordinates.
    
    This endpoint accepts start and finish coordinates and calculates the
    most efficient route between them, along with optimal fuel stops.
    
    Args:
        request: HTTP request with start and finish coordinates.
        
    Returns:
        JSON response with route data and optimized fuel stops.
    """
    try:
        # Parse the JSON body
        body = request.data
        start = body.get('start')
        finish = body.get('finish')
        
        # Validate input
        if not start or not finish:
            return Response(
                {'error': 'Start and finish locations are required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Ensure start and finish are JSON objects with 'lat' and 'lng'
        if not all(k in start for k in ('lat', 'lng')) or not all(k in finish for k in ('lat', 'lng')):
            return Response(
                {'error': 'Start and finish must be JSON objects with lat and lng.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get the route
        try:
            route_data = routing_service.get_route(start, finish)
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Extract route info
        route_info = routing_service.extract_route_info(route_data)
        
        # Calculate fuel stops
        fuel_stops, total_cost, checked_points = fuel_optimizer.optimize_fuel_stops(
            route_info['distance'],
            route_info['steps'],
            route_info['coordinates']
        )
        
        # Generate the map
        map_id, map_file = map_generator.generate_map(
            route_data,
            fuel_stops,
            checked_points,
            search_radius=fuel_optimizer.search_radius
        )
        
        # Prepare the response
        response_data = {
            'message': 'Route data fetched successfully.',
            'route': {
                'distance': route_info['distance'],
                'duration': route_info['duration'],
                'unit': 'miles'
            },
            'fuel': {
                'stops': fuel_stops,
                'total_cost': total_cost,
                'mpg': fuel_optimizer.miles_per_gallon
            },
            'map_url': f'/api/map/{map_id}/'
        }
        
        return Response(response_data)
    
    except json.JSONDecodeError:
        return Response(
            {'error': 'Invalid JSON body.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f"Error calculating route: {str(e)}")
        return Response(
            {'error': f"Failed to calculate route: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@swagger_auto_schema(
    method='get',
    operation_description="Display an interactive map showing the route and fuel stops",
    manual_parameters=[
        openapi.Parameter(
            'map_id', 
            openapi.IN_PATH, 
            description="Unique ID of the map to display", 
            type=openapi.TYPE_STRING,
            required=True
        )
    ],
    responses={
        200: "HTML content with the interactive map",
        404: "Map not found"
    },
    tags=['maps']
)
@api_view(['GET'])
@permission_classes([AllowAny])
def show_map(request, map_id):
    """
    Display an interactive map showing the route and fuel stops.
    
    This endpoint returns an HTML page with an interactive map showing
    the calculated route, fuel stops, and other relevant information.
    
    Args:
        request: HTTP request.
        map_id: Unique ID of the map to display.
        
    Returns:
        HTML response with the interactive map.
        
    Raises:
        Http404: If the map with the given ID is not found.
    """
    # Path to the map file
    map_file = os.path.join(map_generator.map_dir, f'{map_id}.html')
    
    # Check if the file exists
    if not os.path.exists(map_file):
        raise Http404("Map not found")
    
    # Read the file
    with open(map_file, 'r') as f:
        map_html = f.read()
    
    return HttpResponse(map_html)

@swagger_auto_schema(
    method='post',
    operation_description="Calculate an optimized route with fuel stops using location names instead of coordinates. This endpoint geocodes the provided location names to coordinates before calculating the route.",
    request_body=RouteByNameRequestSerializer,
    responses={
        200: openapi.Response(
            description="Route data with optimized fuel stops",
            schema=RouteByNameResponseSerializer
        ),
        400: "Invalid request parameters or geocoding failure",
        500: "Server error"
    },
    tags=['routes']
)
@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([AnonRateThrottle, UserRateThrottle])
def route_by_name(request):
    """
    Calculate an optimized route with fuel stops using location names.
    
    This endpoint accepts location names (e.g., "New York, NY") instead of coordinates,
    geocodes them to coordinates, and then calculates the optimized route with fuel stops.
    
    Args:
        request: HTTP request with start_location and finish_location names.
        
    Returns:
        JSON response with route data and optimized fuel stops.
    """
    try:
        # Parse the JSON body
        body = request.data
        start_location = body.get('start_location')
        finish_location = body.get('finish_location')
        
        # Validate input
        if not start_location or not finish_location:
            return Response(
                {'error': 'Start and finish locations are required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Geocode the locations
        logger.info(f"Geocoding start location: {start_location}")
        start_coords = geocoding_service.geocode(start_location)
        if not start_coords:
            return Response(
                {'error': f"Could not geocode start location: {start_location}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        logger.info(f"Geocoding finish location: {finish_location}")
        finish_coords = geocoding_service.geocode(finish_location)
        if not finish_coords:
            return Response(
                {'error': f"Could not geocode finish location: {finish_location}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get the route
        try:
            route_data = routing_service.get_route(start_coords, finish_coords)
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Extract route info
        route_info = routing_service.extract_route_info(route_data)
        
        # Calculate fuel stops
        fuel_stops, total_cost, checked_points = fuel_optimizer.optimize_fuel_stops(
            route_info['distance'],
            route_info['steps'],
            route_info['coordinates']
        )
        
        # Generate the map
        map_id, map_file = map_generator.generate_map(
            route_data,
            fuel_stops,
            checked_points,
            search_radius=fuel_optimizer.search_radius
        )
        
        # Prepare the response
        response_data = {
            'message': 'Route data fetched successfully.',
            'locations': {
                'start': {
                    'name': start_location,
                    'coordinates': start_coords
                },
                'finish': {
                    'name': finish_location,
                    'coordinates': finish_coords
                }
            },
            'route': {
                'distance': route_info['distance'],
                'duration': route_info['duration'],
                'unit': 'miles'
            },
            'fuel': {
                'stops': fuel_stops,
                'total_cost': total_cost,
                'mpg': fuel_optimizer.miles_per_gallon
            },
            'map_url': f'/api/map/{map_id}/'
        }
        
        return Response(response_data)
    
    except json.JSONDecodeError:
        return Response(
            {'error': 'Invalid JSON body.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f"Error calculating route by name: {str(e)}")
        return Response(
            {'error': f"Failed to calculate route: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
