from django.urls import path
from . import views

urlpatterns = [
    path('fuel-prices/', views.fuel_prices, name='fuel_prices'),
    path('route/', views.route, name='route'),
    path('route-by-name/', views.route_by_name, name='route_by_name'),
    path('map/<str:map_id>/', views.show_map, name='show_map'),
] 