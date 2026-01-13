from django.core.management.base import BaseCommand
from stocks.utils import clear_market_data_cache, get_cache_status, fetch_market_watch_data


class Command(BaseCommand):
    help = 'Manage market data cache'

    def add_arguments(self, parser):
        parser.add_argument(
            'action',
            choices=['status', 'clear', 'refresh'],
            help='Action to perform: status, clear, or refresh'
        )

    def handle(self, *args, **options):
        action = options['action']

        if action == 'status':
            self.show_cache_status()
        elif action == 'clear':
            self.clear_cache()
        elif action == 'refresh':
            self.refresh_cache()

    def show_cache_status(self):
        """Show current cache status"""
        status = get_cache_status()
        
        self.stdout.write(self.style.SUCCESS('=== Market Data Cache Status ==='))
        
        if status['cached']:
            self.stdout.write(f"✅ Cache Status: Active")
            self.stdout.write(f"📊 Data Points: {status['data_count']}")
            if status['ttl_minutes'] != 'unknown':
                self.stdout.write(f"⏰ TTL: {status['ttl_minutes']} minutes")
                self.stdout.write(f"🔄 Expires in: {status['ttl_seconds']} seconds")
            else:
                self.stdout.write("⏰ TTL: Unknown (using default 1 hour)")
                self.stdout.write("💡 Cache will expire after 1 hour")
        else:
            self.stdout.write("❌ Cache Status: Empty/Expired")
            self.stdout.write("💡 Use 'refresh' to fetch fresh data")

    def clear_cache(self):
        """Clear the market data cache"""
        self.stdout.write("🗑️ Clearing market data cache...")
        clear_market_data_cache()
        self.stdout.write(self.style.SUCCESS("✅ Cache cleared successfully"))

    def refresh_cache(self):
        """Refresh the market data cache with fresh data"""
        self.stdout.write("🔄 Refreshing market data cache...")
        
        # Fetch fresh data (this will automatically cache it)
        df = fetch_market_watch_data(use_cache=False)
        
        if df is not None and not df.empty:
            self.stdout.write(self.style.SUCCESS(f"✅ Cache refreshed successfully"))
            self.stdout.write(f"📊 Fetched {len(df)} data points")
            
            # Show cache status after refresh
            self.show_cache_status()
        else:
            self.stdout.write(self.style.ERROR("❌ Failed to refresh cache - API error")) 