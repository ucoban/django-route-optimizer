# Django Route Optimizer

A Django 3.2.23 API that calculates optimized travel routes within the USA, identifying cost-effective fuel stops based on fuel prices.

## Features

- Calculate optimized routes between any two points in the USA
- Find the most cost-effective fuel stops along the route
- Visualize routes and fuel stops on the map
- RESTful API with Swagger documentation
- Support for location names (geocoding) or direct coordinates

## Requirements

- Python 3.9+
- Django 3.2.23
- Other dependencies listed in requirements.txt

## Installation

1. Clone the repository:

   ```
   git clone https://github.com/yourusername/django-route-optimizer.git
   cd django-route-optimizer
   ```

2. Create and activate a virtual environment:

   ```
   python -m venv .venv
   # On Windows
   .venv\Scripts\activate
   # On macOS/Linux
   source .venv/bin/activate
   ```

3. Install dependencies:

   ```
   pip install -r requirements.txt
   ```

4. Apply migrations:

   ```
   python manage.py migrate
   ```

## Running the Application

Start the development server:

```
python manage.py runserver
```

The application will be available at http://localhost:8000/

## API Endpoints

- `GET /api/fuel-prices/`: Get a list of fuel prices
- `POST /api/route/`: Calculate an optimized route with fuel stops using coordinates
- `POST /api/route-by-name/`: Calculate an optimized route with fuel stops using location names
- `GET /api/map/<map_id>/`: View a generated map

### Route by Coordinates Example

```json
POST /api/route/
{
  "start": {"lat": 40.7128, "lng": -74.0060},
  "finish": {"lat": 41.8781, "lng": -87.6298}
}
```

### Route by Names Example

```json
POST /api/route-by-name/
{
  "start_location": "New York, NY",
  "finish_location": "Chicago, IL"
}
```

## API Documentation

API documentation is available at:

- Swagger UI: http://localhost:8000/swagger/
- ReDoc: http://localhost:8000/redoc/

## Environment Variables

Create a `.env` file in the project root with the following variables:

```
DEBUG=True
SECRET_KEY=your-secret-key-here
DJANGO_ALLOWED_HOSTS=localhost 127.0.0.1 [::1]
OPENROUTE_API_KEY=your-openroute-api-key
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.
