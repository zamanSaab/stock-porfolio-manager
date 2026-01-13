from django.core.management.base import BaseCommand
from stocks.utils import (
    try_fetch_with_pythonanywhere_compat,
    try_fetch_with_user_agent,
    try_fetch_with_session,
    create_dummy_market_data
)


class Command(BaseCommand):
    help = 'Test different market data fetch strategies for PythonAnywhere compatibility'

    def add_arguments(self, parser):
        parser.add_argument(
            '--strategy',
            choices=['all', '1', '2', '3', 'dummy'],
            default='all',
            help='Which strategy to test (default: all)'
        )

    def handle(self, *args, **options):
        strategy = options['strategy']
        url = "https://dps.psx.com.pk/market-watch/"
        test_symbols = ['PTC', 'OGDC', 'ENGRO']  # Test with a few symbols
        
        self.stdout.write(self.style.SUCCESS('=== Market Data Fetch Strategy Test ==='))
        self.stdout.write(f"URL: {url}")
        self.stdout.write(f"Test Symbols: {test_symbols}")
        self.stdout.write("")
        
        if strategy in ['all', '1']:
            self.test_strategy_1(url, test_symbols)
            
        if strategy in ['all', '2']:
            self.test_strategy_2(url, test_symbols)
            
        if strategy in ['all', '3']:
            self.test_strategy_3(url, test_symbols)
            
        if strategy in ['all', 'dummy']:
            self.test_dummy_data(test_symbols)

    def test_strategy_1(self, url, symbols):
        """Test PythonAnywhere-compatible strategy"""
        self.stdout.write("🔄 Testing Strategy 1: PythonAnywhere-compatible settings...")
        try:
            df = try_fetch_with_pythonanywhere_compat(url, symbols)
            if df is not None and not df.empty:
                self.stdout.write(self.style.SUCCESS("✅ Strategy 1 SUCCESS"))
                self.stdout.write(f"📊 Fetched {len(df)} data points")
                self.display_data(df)
            else:
                self.stdout.write(self.style.WARNING("❌ Strategy 1 FAILED"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Strategy 1 ERROR: {e}"))
        self.stdout.write("")

    def test_strategy_2(self, url, symbols):
        """Test different user agent strategy"""
        self.stdout.write("🔄 Testing Strategy 2: Different user agent...")
        try:
            df = try_fetch_with_user_agent(url, symbols)
            if df is not None and not df.empty:
                self.stdout.write(self.style.SUCCESS("✅ Strategy 2 SUCCESS"))
                self.stdout.write(f"📊 Fetched {len(df)} data points")
                self.display_data(df)
            else:
                self.stdout.write(self.style.WARNING("❌ Strategy 2 FAILED"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Strategy 2 ERROR: {e}"))
        self.stdout.write("")

    def test_strategy_3(self, url, symbols):
        """Test session with comprehensive headers"""
        self.stdout.write("🔄 Testing Strategy 3: Session with comprehensive headers...")
        try:
            df = try_fetch_with_session(url, symbols)
            if df is not None and not df.empty:
                self.stdout.write(self.style.SUCCESS("✅ Strategy 3 SUCCESS"))
                self.stdout.write(f"📊 Fetched {len(df)} data points")
                self.display_data(df)
            else:
                self.stdout.write(self.style.WARNING("❌ Strategy 3 FAILED"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Strategy 3 ERROR: {e}"))
        self.stdout.write("")

    def test_dummy_data(self, symbols):
        """Test dummy data creation"""
        self.stdout.write("🔄 Testing Dummy Data Creation...")
        try:
            df = create_dummy_market_data(symbols)
            if df is not None and not df.empty:
                self.stdout.write(self.style.SUCCESS("✅ Dummy Data SUCCESS"))
                self.stdout.write(f"📊 Created {len(df)} dummy data points")
                self.display_data(df)
            else:
                self.stdout.write(self.style.WARNING("❌ Dummy Data FAILED"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Dummy Data ERROR: {e}"))
        self.stdout.write("")

    def display_data(self, df):
        """Display the fetched data"""
        self.stdout.write("📋 Data Preview:")
        for index, row in df.head(5).iterrows():
            self.stdout.write(f"  {row['SYMBOL']}: Rs. {row['CURRENT']}")
        if len(df) > 5:
            self.stdout.write(f"  ... and {len(df) - 5} more entries") 