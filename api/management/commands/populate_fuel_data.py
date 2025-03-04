from django.core.management.base import BaseCommand
import pandas as pd
from api.models import FuelData

class Command(BaseCommand):
    help = 'Populate FuelData from a CSV file'

    def handle(self, *args, **kwargs):
        # Load the CSV data
        CSV_FILE_PATH = 'data/fuel_prices_processed.csv'
        df = pd.read_csv(CSV_FILE_PATH)

        # Iterate over the rows in the DataFrame and create FuelData objects
        for _, row in df.iterrows():
            FuelData.objects.create(
                opis_truckstop_id=row['OPIS Truckstop ID'],
                truckstop_name=row['Truckstop Name'],
                address=row['Address'],
                city=row['City'],
                state=row['State'],
                rack_id=row['Rack ID'],
                retail_price=row['Retail Price'],
                latitude=row['latitude'],
                longitude=row['longitude']
            )

        self.stdout.write(self.style.SUCCESS('Successfully populated FuelData from CSV.')) 