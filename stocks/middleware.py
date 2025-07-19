import os
from datetime import datetime, date
from django.utils import timezone
from django.core.cache import cache
from django.conf import settings
import calendar
from dateutil.relativedelta import relativedelta


class MonthlySnapshotMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check if we should generate monthly snapshots
        self.check_and_generate_snapshots()
        
        response = self.get_response(request)
        return response

    def check_and_generate_snapshots(self):
        """
        Check if it's the last day of the month after 4 PM and generate snapshots
        """
        try:
            # Get current date and time
            now = timezone.now()
            current_date = now.date()
            current_time = now.time()
            
            # Check if it's the last day of the month
            last_day = calendar.monthrange(current_date.year, current_date.month)[1]
            is_last_day = current_date.day == last_day
            
            # Check if time is after 4 PM (16:00)
            is_after_4pm = current_time.hour >= 16
            
            # Create a cache key for this month
            cache_key = f"monthly_snapshot_generated_{current_date.year}_{current_date.month:02d}"
            
            # Check if we've already generated snapshots for this month
            already_generated = cache.get(cache_key)
            
            if is_last_day and is_after_4pm and not already_generated:
                # Generate snapshots
                self.generate_monthly_snapshots(current_date)
                
                # Mark as generated for this month (cache for 2 days to be safe)
                cache.set(cache_key, True, 60 * 60 * 48)  # 48 hours
                
        except Exception as e:
            # Log error but don't break the application
            print(f"Error in MonthlySnapshotMiddleware: {str(e)}")

    def generate_monthly_snapshots(self, snapshot_date):
        """
        Generate monthly snapshots for all users
        """
        try:
            from django.core.management import call_command
            from django.contrib.auth.models import User
            from .models import MonthlyDeposit
            
            # Get users who have made deposits
            user_ids = MonthlyDeposit.objects.values_list('user_id', flat=True).distinct()
            users = User.objects.filter(id__in=user_ids)
            
            if not users:
                print("No users found for monthly snapshot generation")
                return
            
            print(f"Generating monthly snapshots for {snapshot_date.strftime('%B %Y')}")
            
            # Generate snapshots for each user
            for user in users:
                try:
                    from .models import MonthlyPortfolioSnapshot
                    snapshot = MonthlyPortfolioSnapshot.create_monthly_snapshot(user, snapshot_date)
                    print(f"✓ Generated snapshot for {user.username}: Portfolio: Rs. {snapshot.total_portfolio_value:,.0f}, P&L: Rs. {snapshot.total_profit_loss:,.0f}")
                except Exception as e:
                    print(f"✗ Error generating snapshot for {user.username}: {str(e)}")
            
            print(f"Monthly snapshot generation completed for {snapshot_date.strftime('%B %Y')}")
            
        except Exception as e:
            print(f"Error in generate_monthly_snapshots: {str(e)}")


class SnapshotStatusMiddleware:
    """
    Middleware to add snapshot status to request for display purposes
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Add snapshot status to request
        self.add_snapshot_status(request)
        
        response = self.get_response(request)
        return response

    def add_snapshot_status(self, request):
        """
        Add snapshot generation status to request context
        """
        try:
            from .models import MonthlyPortfolioSnapshot
            
            # Get latest snapshot for the user
            if request.user.is_authenticated:
                latest_snapshot = MonthlyPortfolioSnapshot.objects.filter(
                    user=request.user
                ).order_by('-snapshot_date').first()
                
                # Check if we need to generate a snapshot
                now = timezone.now()
                current_date = now.date()
                last_day = calendar.monthrange(current_date.year, current_date.month)[1]
                is_last_day = current_date.day == last_day
                is_after_4pm = now.time().hour >= 16
                
                # Check if snapshot exists for this month
                this_month_snapshot = None
                if latest_snapshot:
                    this_month_snapshot = MonthlyPortfolioSnapshot.objects.filter(
                        user=request.user,
                        snapshot_date__year=current_date.year,
                        snapshot_date__month=current_date.month
                    ).first()
                
                # Add to request
                request.snapshot_status = {
                    'latest_snapshot': latest_snapshot,
                    'this_month_snapshot': this_month_snapshot,
                    'should_generate': is_last_day and is_after_4pm and not this_month_snapshot,
                    'is_last_day': is_last_day,
                    'is_after_4pm': is_after_4pm,
                }
            else:
                request.snapshot_status = None
                
        except Exception as e:
            request.snapshot_status = None
            print(f"Error in SnapshotStatusMiddleware: {str(e)}") 