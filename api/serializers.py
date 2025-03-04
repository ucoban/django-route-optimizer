"""
Serializers for the API models.
"""
from rest_framework import serializers
from .models import FuelData

class FuelDataSerializer(serializers.ModelSerializer):
    """
    Serializer for the FuelData model.
    """
    class Meta:
        model = FuelData
        fields = '__all__'

class LocationSerializer(serializers.Serializer):
    """
    Serializer for location data.
    """
    lat = serializers.FloatField(required=True)
    lng = serializers.FloatField(required=True)

class RouteRequestSerializer(serializers.Serializer):
    """
    Serializer for route request data.
    """
    start = LocationSerializer(required=True)
    finish = LocationSerializer(required=True)

class RouteByNameRequestSerializer(serializers.Serializer):
    """
    Serializer for route by name request data.
    """
    start_location = serializers.CharField(required=True)
    finish_location = serializers.CharField(required=True)

class NamedLocationSerializer(serializers.Serializer):
    """
    Serializer for named location data.
    """
    name = serializers.CharField()
    coordinates = LocationSerializer()

class LocationsInfoSerializer(serializers.Serializer):
    """
    Serializer for locations information.
    """
    start = NamedLocationSerializer()
    finish = NamedLocationSerializer()

class FuelStopSerializer(serializers.Serializer):
    """
    Serializer for fuel stop data.
    """
    name = serializers.CharField()
    price = serializers.DecimalField(max_digits=5, decimal_places=2)
    location = LocationSerializer()
    city = serializers.CharField(required=False)
    state = serializers.CharField(required=False)
    distance_from_route = serializers.FloatField()

class RouteInfoSerializer(serializers.Serializer):
    """
    Serializer for route information.
    """
    distance = serializers.FloatField()
    duration = serializers.FloatField()
    unit = serializers.CharField()

class FuelInfoSerializer(serializers.Serializer):
    """
    Serializer for fuel information.
    """
    stops = FuelStopSerializer(many=True)
    total_cost = serializers.FloatField()
    mpg = serializers.FloatField()

class RouteResponseSerializer(serializers.Serializer):
    """
    Serializer for route response data.
    """
    message = serializers.CharField()
    route = RouteInfoSerializer()
    fuel = FuelInfoSerializer()
    map_url = serializers.CharField()

class RouteByNameResponseSerializer(serializers.Serializer):
    """
    Serializer for route by name response data.
    """
    message = serializers.CharField()
    locations = LocationsInfoSerializer()
    route = RouteInfoSerializer()
    fuel = FuelInfoSerializer()
    map_url = serializers.CharField() 