from django.contrib import admin
from .models import Broker, Stock, Transaction

@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ('name', 'symbol', 'avg_price', 'total_quantity', 'total_price', 'portfolio_percentage')
    readonly_fields = ('avg_price', 'total_quantity', 'total_price', 'portfolio_percentage', 'RRR1', 'RRR2', 'total_price_after_stop_loss', 'amount_loss_after_stop_loss', 'percentage_loss_after_stop_loss', 'profit_after_target1', 'profit_after_target2')

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('stock', 'quantity', 'broker', 'price', 'transaction_type')

admin.site.register(Broker)