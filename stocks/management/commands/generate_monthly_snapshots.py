from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from stocks.models import MonthlyPortfolioSnapshot
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import calendar


class Command(BaseCommand):
    help = 'Generate monthly portfolio snapshots for all users'

    def add_arguments(self, parser):
        parser.add_argument(
            '--month',
            type=str,
            help='Month in YYYY-MM format (e.g., 2024-01). If not provided, uses last month.',
        )
        parser.add_argument(
            '--all-users',
            action='store_true',
            help='Generate snapshots for all users',
        )
        parser.add_argument(
            '--user-id',
            type=int,
            help='Generate snapshot for specific user ID',
        )

    def handle(self, *args, **options):
        # Determine the target month
        if options['month']:
            try:
                target_date = datetime.strptime(options['month'], '%Y-%m').date()
                # Set to last day of the month
                last_day = calendar.monthrange(target_date.year, target_date.month)[1]
                target_date = target_date.replace(day=last_day)
            except ValueError:
                self.stdout.write(
                    self.style.ERROR('Invalid month format. Use YYYY-MM (e.g., 2024-01)')
                )
                return
        else:
            # Default to last month's end
            today = date.today()
            last_month = today - relativedelta(months=1)
            last_day = calendar.monthrange(last_month.year, last_month.month)[1]
            target_date = last_month.replace(day=last_day)

        # Determine which users to process
        if options['user_id']:
            try:
                users = [User.objects.get(id=options['user_id'])]
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'User with ID {options["user_id"]} does not exist')
                )
                return
        elif options['all_users']:
            users = User.objects.all()
        else:
            # Default to users who have made deposits
            from stocks.models import MonthlyDeposit
            user_ids = MonthlyDeposit.objects.values_list('user_id', flat=True).distinct()
            users = User.objects.filter(id__in=user_ids)

        if not users:
            self.stdout.write(
                self.style.WARNING('No users found to generate snapshots for')
            )
            return

        self.stdout.write(
            self.style.SUCCESS(f'Generating snapshots for {target_date.strftime("%B %Y")}')
        )

        created_count = 0
        updated_count = 0

        for user in users:
            try:
                snapshot, created = MonthlyPortfolioSnapshot.create_monthly_snapshot(
                    user, target_date
                )
                
                if created:
                    created_count += 1
                    self.stdout.write(
                        f'✓ Created snapshot for {user.username}: '
                        f'Portfolio: Rs. {snapshot.total_portfolio_value:,.0f}, '
                        f'Invested: Rs. {snapshot.total_invested_amount:,.0f}, '
                        f'P&L: Rs. {snapshot.total_profit_loss:,.0f} ({snapshot.profit_loss_percentage:+.1f}%)'
                    )
                else:
                    updated_count += 1
                    self.stdout.write(
                        f'↻ Updated snapshot for {user.username}: '
                        f'Portfolio: Rs. {snapshot.total_portfolio_value:,.0f}, '
                        f'Invested: Rs. {snapshot.total_invested_amount:,.0f}, '
                        f'P&L: Rs. {snapshot.total_profit_loss:,.0f} ({snapshot.profit_loss_percentage:+.1f}%)'
                    )

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error generating snapshot for {user.username}: {str(e)}')
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'\nSummary: {created_count} created, {updated_count} updated'
            )
        ) 