from django.db import models

# Create your models here.

class FuelData(models.Model):
    opis_truckstop_id = models.CharField(max_length=100)
    truckstop_name = models.CharField(max_length=255)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    rack_id = models.CharField(max_length=100)
    retail_price = models.DecimalField(max_digits=5, decimal_places=2)
    latitude = models.FloatField()
    longitude = models.FloatField()

    def __str__(self):
        return self.truckstop_name
