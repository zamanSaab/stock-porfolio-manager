from django.db import models

class Broker(models.Model):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    free_amount = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return self.name

class Stock(models.Model):
    name = models.CharField(max_length=255)
    symbol = models.CharField(max_length=50)
    stop_loss = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    target1 = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    target2 = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    free_float = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    tax = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=0)

    def __str__(self):
        return self.name

    @property
    def avg_price(self):
        if self.total_quantity > 0:
            return round(self.total_price / self.total_quantity, 2)
        return 0

    @property
    def total_quantity(self):
        buy_quantity = sum(transaction.quantity for transaction in self.transactions.filter(transaction_type='buy'))
        sell_quantity = sum(transaction.quantity for transaction in self.transactions.filter(transaction_type='sell'))
        return buy_quantity - sell_quantity

    @property
    def total_price(self):
        buy_price = sum(transaction.quantity * transaction.price for transaction in self.transactions.filter(transaction_type='buy'))
        sell_price = sum(transaction.quantity * transaction.price for transaction in self.transactions.filter(transaction_type='sell'))
        return round(buy_price - sell_price, 2)

    @property
    def portfolio_percentage(self):
        total_portfolio_value = sum(stock.total_price for stock in Stock.objects.all())
        if total_portfolio_value > 0:
            return round((self.total_price / total_portfolio_value) * 100, 2)
        return 0

    @property
    def RRR1(self):
        if self.stop_loss and self.target1:
            return round((self.target1 - self.avg_price) / (self.avg_price - self.stop_loss), 2)
        return None

    @property
    def RRR2(self):
        if self.stop_loss and self.target2:
            return round((self.target2 - self.avg_price) / (self.avg_price - self.stop_loss), 2)
        return None

    @property
    def total_price_after_stop_loss(self):
        if self.stop_loss:
            return round(self.total_quantity * self.stop_loss, 2)
        return None

    @property
    def amount_loss_after_stop_loss(self):
        if self.stop_loss:
            return round(self.total_price - self.total_price_after_stop_loss, 2)
        return None

    @property
    def percentage_loss_after_stop_loss(self):
        if self.stop_loss and self.total_price > 0:
            return round((self.amount_loss_after_stop_loss / self.total_price) * 100, 2)
        return None

    @property
    def profit_after_target1(self):
        if self.target1:
            return round(self.total_quantity * (self.target1 - self.avg_price), 2)
        return None

    @property
    def profit_after_target2(self):
        if self.target2:
            return round(self.total_quantity * (self.target2 - self.avg_price), 2)
        return None

class Transaction(models.Model):
    TRANSACTION_TYPES = [
        ('buy', 'Buy'),
        ('sell', 'Sell'),
    ]
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name='transactions')
    quantity = models.IntegerField()
    broker = models.ForeignKey(Broker, on_delete=models.CASCADE, related_name='transactions')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(max_length=4, choices=TRANSACTION_TYPES)
    date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.stock.name} - {self.quantity}"