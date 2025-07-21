from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from decimal import Decimal
from django.utils import timezone

class Broker(models.Model):
    user = models.ForeignKey(User, null=True, on_delete=models.CASCADE, related_name='brokers')
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    free_amount = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return self.name

class MonthlyDeposit(models.Model):
    user = models.ForeignKey(User, null=True, on_delete=models.CASCADE, related_name='monthly_deposits')
    broker = models.ForeignKey(Broker, on_delete=models.CASCADE, related_name='monthly_deposits')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    deposit_date = models.DateField()
    description = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-deposit_date']
        unique_together = ['broker', 'deposit_date']  # One deposit per broker per date

    def __str__(self):
        return f"{self.broker.name} - {self.amount} - {self.deposit_date}"

    def save(self, *args, **kwargs):
        # Update broker's free amount when deposit is saved
        if not self.pk:  # New deposit
            self.broker.free_amount += self.amount
            self.broker.total_amount += self.amount
            self.broker.save()
        else:  # Updating existing deposit
            old_deposit = MonthlyDeposit.objects.get(pk=self.pk)
            amount_difference = self.amount - old_deposit.amount
            self.broker.free_amount += amount_difference
            self.broker.total_amount += amount_difference
            self.broker.save()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # Update broker's free amount when deposit is deleted
        self.broker.free_amount -= self.amount
        self.broker.total_amount -= self.amount
        self.broker.save()
        super().delete(*args, **kwargs)

class MonthlyPortfolioSnapshot(models.Model):
    user = models.ForeignKey(User, null=True, on_delete=models.CASCADE, related_name='portfolio_snapshots')
    snapshot_date = models.DateField()
    total_invested_amount = models.DecimalField(max_digits=15, decimal_places=2)
    total_portfolio_value = models.DecimalField(max_digits=15, decimal_places=2)
    total_free_amount = models.DecimalField(max_digits=15, decimal_places=2)
    total_profit_loss = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True, default=0)
    profit_loss_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-snapshot_date']
        unique_together = ['user', 'snapshot_date']  # One snapshot per user per date

    def __str__(self):
        return f"{self.user.username} - {self.snapshot_date} - Portfolio: Rs. {self.total_portfolio_value}"

    @property
    def month_year(self):
        """Return month and year for display"""
        return self.snapshot_date.strftime('%B %Y')

    @property
    def is_profitable(self):
        """Check if portfolio is profitable"""
        return self.total_profit_loss > 0

    @classmethod
    def create_monthly_snapshot(cls, user, snapshot_date):
        """Create a monthly snapshot for a user on a specific date"""
        from datetime import datetime
        
        # Calculate total invested amount (sum of all deposits)
        total_invested = MonthlyDeposit.objects.filter(
            user=user,
            deposit_date__lte=snapshot_date
        ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')
        
        # Calculate total portfolio value (stocks + free amounts)
        total_portfolio_value = Decimal('0.00')
        total_free_amount = Decimal('0.00')
        
        # Get all active stocks with their current values
        stocks = Stock.objects.filter(user=user, is_active=True)
        
        # Import fetch_market_watch_data function
        from .utils import fetch_market_watch_data
        
        # Get current market prices for all stocks
        stock_symbols = [stock.symbol for stock in stocks]
        market_data = None
        if stock_symbols:
            try:
                market_data = fetch_market_watch_data(stock_symbols)
                if market_data is not None:
                    market_data = market_data.set_index('SYMBOL')['CURRENT'].to_dict()
            except Exception as e:
                print(f"Error fetching market data for snapshot: {e}")
                market_data = {}
        
        for stock in stocks:
            if stock.total_quantity > 0:
                # Use current market price if available, otherwise use average price
                if market_data and stock.symbol in market_data:
                    try:
                        current_price = float(market_data[stock.symbol].replace(',', ''))
                    except (ValueError, AttributeError):
                        current_price = stock.avg_price
                else:
                    current_price = stock.avg_price
                
                # Convert current_price to Decimal for consistency
                current_price_decimal = Decimal(str(current_price))
                stock_value = stock.total_quantity * current_price_decimal
                total_portfolio_value += stock_value
        
        # Add free amounts from all brokers
        brokers = Broker.objects.filter(user=user)
        for broker in brokers:
            total_free_amount += broker.free_amount
        
        total_portfolio_value += total_free_amount
        
        # Calculate profit/loss
        total_profit_loss = total_portfolio_value - total_invested
        
        # Calculate profit/loss percentage
        profit_loss_percentage = Decimal('0.00')
        if total_invested > 0:
            profit_loss_percentage = (total_profit_loss / total_invested) * 100
        
        # Create or update snapshot
        snapshot, created = cls.objects.update_or_create(
            user=user,
            snapshot_date=snapshot_date,
            defaults={
                'total_invested_amount': total_invested,
                'total_portfolio_value': total_portfolio_value,
                'total_free_amount': total_free_amount,
                'total_profit_loss': total_profit_loss,
                'profit_loss_percentage': profit_loss_percentage,
            }
        )
        
        return snapshot

    @classmethod
    def get_latest_snapshot(cls, user):
        """Get the latest snapshot for a user"""
        return cls.objects.filter(user=user).first()

    @classmethod
    def get_monthly_growth(cls, user, months=12):
        """Get monthly growth data for charts"""
        from datetime import datetime, timedelta
        from dateutil.relativedelta import relativedelta
        
        end_date = datetime.now().date()
        start_date = end_date - relativedelta(months=months)
        
        snapshots = cls.objects.filter(
            user=user,
            snapshot_date__range=[start_date, end_date]
        ).order_by('snapshot_date')
        
        return snapshots

class Stock(models.Model):
    user = models.ForeignKey(User, null=True, on_delete=models.CASCADE, related_name='stocks')
    name = models.CharField(max_length=255)
    symbol = models.CharField(max_length=50)
    stop_loss = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    target1 = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    target2 = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    free_float = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    tax = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=0)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    @property
    def avg_price(self):
        if self.total_quantity > 0:
            total_price = self.total_price
            # Include dividends impacting average price
            dividend_impact = sum(dividend.amount for dividend in self.dividends.filter(impact_average=True))
            total_price -= dividend_impact
            return round(total_price / self.total_quantity, 2)
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
        # Filter stocks with non-zero total_quantity
        remaining_stocks = [stock for stock in Stock.objects.filter(is_active=True) if stock.total_quantity > 0]
        total_portfolio_value = sum(stock.total_price for stock in remaining_stocks)
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
    user = models.ForeignKey(User, null=True, on_delete=models.CASCADE, related_name='transactions')
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name='transactions')
    quantity = models.IntegerField()
    broker = models.ForeignKey(Broker, on_delete=models.CASCADE, related_name='transactions')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(max_length=4, choices=[('buy', 'Buy'), ('sell', 'Sell')])
    date = models.DateField(default=timezone.now)

    def __str__(self):
        return f"{self.stock.name} - {self.quantity}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Check if the stock's total quantity is zero
        if self.stock.total_quantity == 0:
            self.stock.is_active = False
            self.stock.save()

    def delete(self, *args, **kwargs):
        stock = self.stock
        super().delete(*args, **kwargs)
        # Check if the stock's total quantity is greater than zero
        if stock.total_quantity > 0:
            stock.is_active = True
            stock.save()

class Dividend(models.Model):
    user = models.ForeignKey(User, null=True, on_delete=models.CASCADE, related_name='dividends')
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name='dividends')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField()
    impact_average = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.stock.name} - {self.amount}"
