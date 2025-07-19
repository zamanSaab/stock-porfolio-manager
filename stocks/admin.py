from django.contrib import admin
from django.utils.html import format_html
from .models import Broker, Stock, Transaction, Dividend, MonthlyDeposit, MonthlyPortfolioSnapshot
from .utils import get_cache_status

@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ('name', 'symbol', 'avg_price', 'total_quantity', 'total_price', 'portfolio_percentage')
    readonly_fields = ('avg_price', 'total_quantity', 'total_price', 'portfolio_percentage', 'RRR1', 'RRR2', 'total_price_after_stop_loss', 'amount_loss_after_stop_loss', 'percentage_loss_after_stop_loss', 'profit_after_target1', 'profit_after_target2')

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('stock', 'quantity', 'broker', 'price', 'transaction_type')

@admin.register(Dividend)
class DividendAdmin(admin.ModelAdmin):
    list_display = ('stock', 'amount', 'date', 'impact_average')
    list_filter = ('impact_average', 'date')
    search_fields = ('stock__name', 'amount')

admin.site.register(Broker)

@admin.register(MonthlyDeposit)
class MonthlyDepositAdmin(admin.ModelAdmin):
    list_display = ('user', 'broker', 'amount', 'deposit_date', 'description')
    list_filter = ('deposit_date', 'broker', 'user')
    search_fields = ('user__username', 'broker__name', 'description')
    date_hierarchy = 'deposit_date'
    ordering = ('-deposit_date',)
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'broker', 'amount', 'deposit_date')
        }),
        ('Additional Details', {
            'fields': ('description',),
            'classes': ('collapse',)
        }),
    )

@admin.register(MonthlyPortfolioSnapshot)
class MonthlyPortfolioSnapshotAdmin(admin.ModelAdmin):
    list_display = ('user', 'snapshot_date', 'total_invested_amount', 'total_portfolio_value', 'total_free_amount')#, 'total_profit_loss', 'profit_loss_percentage')
    list_filter = ('snapshot_date', 'user')
    search_fields = ('user__username',)
    date_hierarchy = 'snapshot_date'
    ordering = ('-snapshot_date',)
    readonly_fields = ('total_profit_loss', 'profit_loss_percentage')
    
    fieldsets = (
        ('Snapshot Information', {
            'fields': ('user', 'snapshot_date')
        }),
        ('Financial Data', {
            'fields': ('total_invested_amount', 'total_portfolio_value', 'total_free_amount')
        }),
        ('Calculated Fields', {
            'fields': ('total_profit_loss', 'profit_loss_percentage'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')

# Add cache status to admin index
admin.site.site_header = "PSX Portfolio Admin"
admin.site.site_title = "PSX Portfolio Admin Portal"
admin.site.index_title = "Welcome to PSX Portfolio Administration"

def get_admin_cache_status():
    """Get cache status for admin display"""
    try:
        status = get_cache_status()
        if status['cached']:
            ttl_display = f'TTL: {status["ttl_minutes"]} minutes' if status["ttl_minutes"] != 'unknown' else 'TTL: Unknown (1 hour default)'
            return format_html(
                '<div style="background: #d4edda; border: 1px solid #c3e6cb; padding: 10px; margin: 10px 0; border-radius: 4px;">'
                '<strong>📊 Market Data Cache:</strong> Active<br>'
                f'Data Points: {status["data_count"]} | {ttl_display}'
                '</div>'
            )
        else:
            return format_html(
                '<div style="background: #f8d7da; border: 1px solid #f5c6cb; padding: 10px; margin: 10px 0; border-radius: 4px;">'
                '<strong>⚠️ Market Data Cache:</strong> Empty/Expired<br>'
                'Use management command to refresh: python manage.py manage_market_cache refresh'
                '</div>'
            )
    except Exception as e:
        return format_html(
            '<div style="background: #fff3cd; border: 1px solid #ffeaa7; padding: 10px; margin: 10px 0; border-radius: 4px;">'
            f'<strong>❌ Cache Status Error:</strong> {str(e)}'
            '</div>'
        )

# Override admin index to show cache status
original_index = admin.site.index

def admin_index_with_cache(request, extra_context=None):
    extra_context = extra_context or {}
    extra_context['cache_status'] = get_admin_cache_status()
    return original_index(request, extra_context)

admin.site.index = admin_index_with_cache
