from django.db import models


class Company(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.name}"


class Transaction(models.Model):
    TRADE_TYPES = (
        ('BUY', 'Buy'),
        ('SELL', 'Sell'),
        ('SPLIT', 'Split'),
    )

    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    trade_type = models.CharField(max_length=5, choices=TRADE_TYPES)
    quantity = models.PositiveIntegerField()
    price_per_share = models.FloatField(null=True, blank=True)
    trade_date = models.DateField()
