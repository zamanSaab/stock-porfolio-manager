from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, date
import calendar


class Command(BaseCommand):
    help = 'Test automatic monthly snapshot generation'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force generation even if conditions are not met',
        )
        parser.add_argument(
            '--date',
            type=str,
            help='Test with specific date (YYYY-MM-DD)',
        )

    def handle(self, *args, **options):
        from stocks.middleware import MonthlySnapshotMiddleware
        
        # Create middleware instance
        middleware = MonthlySnapshotMiddleware(lambda request: None)
        
        if options['date']:
            try:
                test_date = datetime.strptime(options['date'], '%Y-%m-%d').date()
                self.stdout.write(f'Testing with date: {test_date}')
                
                # Override timezone for testing
                original_now = timezone.now
                timezone.now = lambda: datetime.combine(test_date, datetime.min.time())
                
                try:
                    middleware.check_and_generate_snapshots()
                finally:
                    timezone.now = original_now
                    
            except ValueError:
                self.stdout.write(
                    self.style.ERROR('Invalid date format. Use YYYY-MM-DD')
                )
                return
        else:
            # Test current conditions
            now = timezone.now()
            current_date = now.date()
            current_time = now.time()
            
            last_day = calendar.monthrange(current_date.year, current_date.month)[1]
            is_last_day = current_date.day == last_day
            is_after_4pm = current_time.hour >= 16
            
            self.stdout.write(f'Current Date: {current_date}')
            self.stdout.write(f'Current Time: {current_time}')
            self.stdout.write(f'Is Last Day: {is_last_day}')
            self.stdout.write(f'Is After 4 PM: {is_after_4pm}')
            
            if options['force'] or (is_last_day and is_after_4pm):
                self.stdout.write(
                    self.style.SUCCESS('Conditions met! Generating snapshots...')
                )
                middleware.check_and_generate_snapshots()
            else:
                self.stdout.write(
                    self.style.WARNING('Conditions not met for automatic generation.')
                )
                if not is_last_day:
                    self.stdout.write('  - Not the last day of the month')
                if not is_after_4pm:
                    self.stdout.write('  - Not after 4 PM')
                self.stdout.write('Use --force to generate anyway.') 