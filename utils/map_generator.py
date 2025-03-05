"""
Map generator utility functions for the route optimizer API.
"""
import os
import uuid
import logging
from typing import Dict, List, Tuple, Any
import folium
from django.conf import settings

# Configure logging
logger = logging.getLogger(__name__)

class MapGenerator:
    """
    Service for generating interactive maps.
    """
    def __init__(self, map_dir: str = None):
        """
        Initialize the map generator.
        
        Args:
            map_dir: Directory to save maps. If None, uses 'templates/maps/'.
        """
        self.map_dir = map_dir or os.path.join(settings.BASE_DIR, 'templates', 'maps')
        os.makedirs(self.map_dir, exist_ok=True)
    
    def generate_map(self, 
                    geojson_data: Dict[str, Any], 
                    fuel_stops: List[Dict[str, Any]], 
                    checked_points: List[Tuple[float, float]],
                    search_radius: float = 15.0) -> Tuple[str, str]:
        """
        Generate an interactive map with the route, fuel stops, and check points.
        
        Args:
            geojson_data: GeoJSON data from OpenRouteService.
            fuel_stops: List of fuel stops.
            checked_points: List of check points.
            search_radius: Radius used to search for fuel stations in miles.
            
        Returns:
            Tuple of (map_id, map_file_path).
        """
        # Extract coordinates from the GeoJSON response
        coordinates = geojson_data['features'][0]['geometry']['coordinates']
        first_coord = coordinates[0]
        last_coord = coordinates[-1]
        
        # Create a map centered on the first coordinate
        m = folium.Map(location=[first_coord[1], first_coord[0]], zoom_start=5)
        
        # Add the route as a PolyLine
        folium.PolyLine([(lat, lon) for lon, lat in coordinates], color='blue', weight=2.5, opacity=1).add_to(m)
        
        # Add start marker
        folium.Marker(
            location=[first_coord[1], first_coord[0]], 
            popup='Start', 
            icon=folium.Icon(color='green')
        ).add_to(m)
        
        # Add end marker
        folium.Marker(
            location=[last_coord[1], last_coord[0]], 
            popup='End', 
            icon=folium.Icon(color='red')
        ).add_to(m)
        
        # Add markers for fuel stations
        for stop in fuel_stops:
            distance_info = f" ({stop['distance_from_route']:.1f} miles from route)" if 'distance_from_route' in stop else ""
            location_info = f"{stop['city']}, {stop['state']}" if 'city' in stop and 'state' in stop else ""
            
            popup_content = f"""
            <b>{stop['name']}</b><br>
            {location_info}<br>
            <b>Price:</b> ${float(stop['price']):.2f}{distance_info}
            """
            
            folium.Marker(
                location=[stop['location']['lat'], stop['location']['lng']],
                popup=folium.Popup(popup_content, max_width=200),
                tooltip=f"{stop['name']} - ${float(stop['price']):.2f}",
                icon=folium.Icon(color='orange', icon='tint')
            ).add_to(m)
        
        # Add markers for checked points
        for point in checked_points:
            folium.CircleMarker(
                location=point,
                radius=5,
                color='purple',
                fill=True,
                popup=f"Checked point: {point}",
                opacity=0.7
            ).add_to(m)
            
            # Draw a circle representing the search radius
            folium.Circle(
                location=point,
                radius=search_radius * 1609.34,  # Convert miles to meters
                color='purple',
                fill=False,
                opacity=0.3,
                weight=1
            ).add_to(m)
        
        # Add a legend
        legend_html = '''
        <div style="position: fixed; 
                    bottom: 50px; right: 50px; width: 180px; 
                    border:2px solid grey; z-index:9999; 
                    background-color:white;
                    opacity: 0.8;
                    font-size: 14px;
                    padding: 10px">
            <b>Legend</b><br>
            <i class="fa fa-circle" style="color:green"></i> Start<br>
            <i class="fa fa-circle" style="color:red"></i> End<br>
            <i class="fa fa-tint" style="color:orange"></i> Fuel Stop<br>
            <i class="fa fa-circle" style="color:purple"></i> Check Point<br>
            <i class="fa fa-circle-o" style="color:purple"></i> Search Radius
        </div>
        '''
        m.get_root().html.add_child(folium.Element(legend_html))
        
        # Generate a unique ID for the map
        map_id = str(uuid.uuid4())
        
        # Save the map to an HTML file with the random ID
        map_file = os.path.join(self.map_dir, f'{map_id}.html')
        m.save(map_file)
        
        logger.info(f"Map generated and saved to {map_file}")
        
        return map_id, map_file 