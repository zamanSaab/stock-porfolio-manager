from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from .models import Broker, Stock, Transaction, Dividend, MonthlyDeposit, MonthlyPortfolioSnapshot
from .forms import BrokerForm, TransactionForm, StockForm, DividendForm, CustomSignupForm, MonthlyDepositForm
from .utils import fetch_market_watch_data
from django.db.models import Sum, Case, When, IntegerField, Avg, Q, F, FloatField, ExpressionWrapper
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
import json
from datetime import datetime, timedelta
from django.db.models.functions import TruncMonth
from dateutil.relativedelta import relativedelta

@login_required
def index(request):
    # stocks = Stock.objects.filter(user=request.user)

    stocks = Stock.objects.filter(user=request.user, is_active=True).annotate(
        quantity=Sum(
            Case(
                When(transactions__transaction_type='buy', then='transactions__quantity'),
                default=0,
                output_field=IntegerField()
            )
        ) - Sum(
            Case(
                When(transactions__transaction_type='sell', then='transactions__quantity'),
                default=0,
                output_field=IntegerField()
            )
        )
    ).filter(quantity__gt=0).order_by('-name')
    total_value = 0
    stock_data = []
    sector_data_json = []
    current_price = 200

    # Get all stock symbols for market data fetch
    stock_symbols = [stock.symbol for stock in stocks]
    
    # Fetch current market prices
    market_data = None
    if stock_symbols:
        try:
            market_data = fetch_market_watch_data(stock_symbols)
            if market_data is not None:
                market_data = market_data.set_index('SYMBOL')['CURRENT'].to_dict()
        except Exception as e:
            print(f"Error fetching market data: {e}")
            market_data = {}
    
    for stock in stocks:
        # Use current market price if available, otherwise use average price
        if market_data and stock.symbol in market_data:
            try:
                current_price = float(market_data[stock.symbol].replace(',', ''))
            except (ValueError, AttributeError):
                current_price = float(stock.avg_price)
        else:
            current_price = float(stock.avg_price)
        
        value = current_price * stock.total_quantity
        total_value += value
        
        # Calculate profit/loss for this stock
        avg_price = stock.avg_price
        # Convert both to float for calculation
        current_price_float = float(current_price)
        avg_price_float = float(avg_price) if avg_price and avg_price > 0 else 0.0
        stock_profit_loss = (current_price_float - avg_price_float) * stock.total_quantity if stock.total_quantity > 0 else 0
        
        stock_data.append({
            'name': stock.name,
            'symbol': stock.symbol,
            'value': int(value),
            'quantity': stock.quantity,  # Add quantity for template
            'current_price': float(current_price),
            'avg_price': float(avg_price) if avg_price else 0.0,
            'profit_loss': float(stock_profit_loss),
            "exploded": True,
        })
    for data in stock_data:
        data['y'] = int((data['value']  / total_value)*100) if total_value > 0 else 0

    top_holdings = sorted(stock_data, key=lambda x: x['value'], reverse=True)[:5]

    # Calculate actual portfolio metrics (moved up)
    brokers = Broker.objects.filter(user=request.user)
    total_free_amount = round(sum(float(broker.free_amount) for broker in brokers), 2)
    total_value_float = float(total_value)
    total_free_amount_float = float(total_free_amount)
    current_portfolio_value = round(total_value_float + total_free_amount_float, 2)
    total_invested_amount = MonthlyDeposit.objects.filter(user=request.user).aggregate(
        total=Sum('amount')
    )['total'] or 0
    total_invested_amount = round(float(total_invested_amount), 2)

    # Get real portfolio performance data from snapshots
    snapshots = MonthlyPortfolioSnapshot.objects.filter(user=request.user).order_by('snapshot_date')
    
    if snapshots.exists():
        # Use actual snapshot data
        performance_labels = []
        portfolio_values = []
        invested_amounts = []
        
        for snapshot in snapshots:
            performance_labels.append(snapshot.snapshot_date.strftime('%b %Y'))
            portfolio_values.append(float(snapshot.total_portfolio_value + snapshot.total_free_amount))
            invested_amounts.append(float(snapshot.total_invested_amount))
        
        # Add current portfolio value as the latest data point
        from datetime import datetime
        current_month = datetime.now().strftime('%b %Y')
        
        # Only add current data if it's different from the last snapshot
        if not performance_labels or performance_labels[-1] != current_month:
            performance_labels.append(current_month)
            portfolio_values.append(current_portfolio_value)
            invested_amounts.append(total_invested_amount)
        
        performance_datasets = [
            {
                "label": "Portfolio Value",
                "data": portfolio_values,
                "borderColor": "#4e73df",
                "backgroundColor": "rgba(78, 115, 223, 0.1)",
                "borderWidth": 3,
                "tension": 0.4,
                "fill": True
            },
            {
                "label": "Invested Amount",
                "data": invested_amounts,
                "borderColor": "#858796",
                "backgroundColor": "rgba(133, 135, 150, 0.1)",
                "borderWidth": 2,
                "borderDash": [5, 5],
                "tension": 0.4,
                "fill": False
            }
        ]
    else:
        # Fallback to monthly deposit data if no snapshots exist
        deposits = MonthlyDeposit.objects.filter(user=request.user).order_by('deposit_date')
        
        if deposits.exists():
            # Group deposits by month
            monthly_deposits = {}
            for deposit in deposits:
                month_key = deposit.deposit_date.strftime('%b %Y')
                if month_key not in monthly_deposits:
                    monthly_deposits[month_key] = 0
                monthly_deposits[month_key] += float(deposit.amount)
            
            performance_labels = list(monthly_deposits.keys())
            invested_amounts = list(monthly_deposits.values())
            
            # Calculate cumulative invested amount
            cumulative_invested = []
            total = 0
            for amount in invested_amounts:
                total += amount
                cumulative_invested.append(total)
            
            # Estimate portfolio value (assuming some growth)
            portfolio_values = [amount * 1.1 for amount in cumulative_invested]  # 10% growth estimate
            
            # Add current portfolio value as the latest data point
            from datetime import datetime
            current_month = datetime.now().strftime('%b %Y')
            
            # Only add current data if it's different from the last deposit month
            if not performance_labels or performance_labels[-1] != current_month:
                performance_labels.append(current_month)
                portfolio_values.append(current_portfolio_value)
                invested_amounts.append(total_invested_amount)
            
            performance_datasets = [
                {
                    "label": "Portfolio Value (Estimated)",
                    "data": portfolio_values,
                    "borderColor": "#4e73df",
                    "backgroundColor": "rgba(78, 115, 223, 0.1)",
                    "borderWidth": 3,
                    "tension": 0.4,
                    "fill": True
                },
                {
                    "label": "Invested Amount",
                    "data": cumulative_invested,
                    "borderColor": "#858796",
                    "backgroundColor": "rgba(133, 135, 150, 0.1)",
                    "borderWidth": 2,
                    "borderDash": [5, 5],
                    "tension": 0.4,
                    "fill": False
                }
            ]
        else:
            # No data available - show empty chart
            performance_labels = ["No Data"]
            performance_datasets = [
                {
                    "label": "Portfolio Value",
                    "data": [0],
                    "borderColor": "#4e73df",
                    "backgroundColor": "rgba(78, 115, 223, 0.1)",
                    "borderWidth": 3,
                    "tension": 0.4,
                    "fill": True
                },
                {
                    "label": "Invested Amount",
                    "data": [0],
                    "borderColor": "#858796",
                    "backgroundColor": "rgba(133, 135, 150, 0.1)",
                    "borderWidth": 2,
                    "borderDash": [5, 5],
                    "tension": 0.4,
                    "fill": False
                }
            ]
    
    # Calculate current profit/loss
    current_portfolio_gain = round(current_portfolio_value - total_invested_amount, 2)
    
    # Calculate gain percentage
    gain_percent = 0
    if total_invested_amount > 0:
        gain_percent = round((current_portfolio_gain / total_invested_amount) * 100, 2)
    
    # Calculate total dividends received
    total_dividends = Dividend.objects.filter(user=request.user).aggregate(
        total=Sum('amount')
    )['total'] or 0
    total_dividends = round(float(total_dividends), 2)
    
    # Get latest snapshot for comparison
    latest_snapshot = MonthlyPortfolioSnapshot.objects.filter(user=request.user).order_by('-snapshot_date').first()
    
    # Calculate total gain (current value + dividends - invested)
    total_gain = round(current_portfolio_gain + total_dividends, 2)
    
    # Get cache status for display
    from .utils import get_cache_status
    cache_status = get_cache_status()

    return render(request, 'index.html', {
        'top_holdings': top_holdings,
        'total_gain': total_gain,
        'gain_percent': gain_percent,
        'current_portfolio_gain': current_portfolio_gain,
        'current_portfolio': current_portfolio_value,
        'dividend': total_dividends,
        'total_free_amount': total_free_amount,
        'total_invested_amount': total_invested_amount,
        'stock_data_json': json.dumps(stock_data),
        'performance_labels_json': json.dumps(performance_labels),
        'performance_datasets_json': json.dumps(performance_datasets),
        'cache_status': cache_status,
    })

@login_required
def broker_list(request):
    brokers = Broker.objects.filter(user=request.user)
    total_amount = sum(broker.total_amount for broker in brokers)
    free_amount = sum(broker.free_amount for broker in brokers)
    return render(request, 'brokers.html', {
        'brokers': brokers,
        'total_amount': total_amount,
        'free_amount': free_amount,
    })

@login_required
def stock_list(request):
    stocks = Stock.objects.filter(user=request.user, is_active=True).annotate(
        quantity=Sum(
            Case(
                When(transactions__transaction_type='buy', then='transactions__quantity'),
                default=0,
                output_field=IntegerField()
            )
        ) - Sum(
            Case(
                When(transactions__transaction_type='sell', then='transactions__quantity'),
                default=0,
                output_field=IntegerField()
            )
        )
    ).filter(quantity__gt=0).order_by('-name')
    return render(request, 'stocks.html', {'stocks': stocks})

@login_required
def transaction_list(request):
    transactions = Transaction.objects.filter(user=request.user)
    return render(request, 'transactions.html', {'transactions': transactions})


@login_required
def add_broker(request):
    if request.method == 'POST':
        form = BrokerForm(request.POST)
        if form.is_valid():
            broker = form.save(commit=False)
            broker.user = request.user
            broker.save()
            messages.success(request, 'Broker added successfully!')
            return redirect('broker_list')
    else:
        form = BrokerForm()
    return render(request, 'add-broker.html', {'form': form})


@login_required
def edit_broker(request, pk):
    broker = get_object_or_404(Broker, pk=pk, user=request.user)
    if request.method == 'POST':
        form = BrokerForm(request.POST, instance=broker)
        if form.is_valid():
            form.save()
            messages.success(request, 'Broker updated successfully!')
            return redirect('broker_list')
    else:
        form = BrokerForm(instance=broker)
    return render(request, 'edit-brocker.html', {'form': form, 'broker': broker})


@login_required
def delete_broker(request, pk):
    broker = get_object_or_404(Broker, pk=pk, user=request.user)
    if request.method == 'POST':
        broker.delete()
        messages.success(request, 'Broker deleted successfully!')
        return redirect('broker_list')
    return render(request, 'del-brocker.html', {'broker': broker})

@login_required
def add_transaction(request):
    if request.method == 'POST':
        form = TransactionForm(request.POST, user=request.user)
        if form.is_valid():
            transaction = form.save(commit=False)
            transaction.user = request.user
            transaction.save()
            if transaction.transaction_type == 'buy':
                transaction.broker.free_amount -= transaction.quantity * transaction.price
            elif transaction.transaction_type == 'sell':
                transaction.broker.free_amount += transaction.quantity * transaction.price
            transaction.broker.save()
            messages.success(request, 'Transaction added successfully!')
            return redirect('transaction_list')
    else:
        form = TransactionForm(user=request.user)
    return render(request, 'transaction-form.html', {'form': form})


@login_required
def edit_transaction(request, pk):
    transaction = get_object_or_404(Transaction, pk=pk, user=request.user)
    original_quantity = transaction.quantity
    original_price = transaction.price
    original_type = transaction.transaction_type

    if request.method == 'POST':
        form = TransactionForm(request.POST, instance=transaction, user=request.user)
        if form.is_valid():
            updated_transaction = form.save()

            if original_type == 'buy':
                transaction.broker.free_amount += original_quantity * original_price
            elif original_type == 'sell':
                transaction.broker.free_amount -= original_quantity * original_price

            if updated_transaction.transaction_type == 'buy':
                updated_transaction.broker.free_amount -= updated_transaction.quantity * updated_transaction.price
            elif updated_transaction.transaction_type == 'sell':
                updated_transaction.broker.free_amount += updated_transaction.quantity * updated_transaction.price

            updated_transaction.broker.save()
            messages.success(request, 'Transaction updated successfully!')
            return redirect('transaction_list')
    else:
        form = TransactionForm(instance=transaction, user=request.user)
    return render(request, 'transaction-form.html', {'form': form, 'transaction': transaction})


@login_required
def delete_transaction(request, pk):
    transaction = get_object_or_404(Transaction, pk=pk, user=request.user)
    if request.method == 'POST':
        # Adjust broker free amount before deleting the transaction
        if transaction.transaction_type == 'buy':
            transaction.broker.free_amount += transaction.quantity * transaction.price
        elif transaction.transaction_type == 'sell':
            transaction.broker.free_amount -= transaction.quantity * transaction.price
        transaction.broker.save()
        
        transaction.delete()
        messages.success(request, 'Transaction deleted successfully!')
        return redirect('transaction_list')
    return render(request, 'del-transaction.html', {'transaction': transaction})

@login_required
def stock_details(request, pk):
    stock = get_object_or_404(Stock, pk=pk, user=request.user)
    return render(request, 'stock-details.html', {'stock': stock})

@login_required
def update_market_price(request, pk):
    pass

@login_required
def fetch_market_price(request, pk):
    stock = get_object_or_404(Stock, pk=pk)
    stock_details = fetch_market_watch_data([stock.symbol])
    stock_details = stock_details.to_dict('records')
    if stock_details:
        current_price = stock_details[0].get('CURRENT')
        return JsonResponse({'success': True, 'market_price': current_price})
    return JsonResponse({'success': False, 'message': 'Stock not found or no market data available.'})

@login_required
def edit_stock(request, pk):
    stock = get_object_or_404(Stock, pk=pk, user=request.user)
    if request.method == 'POST':
        form = StockForm(request.POST, instance=stock)
        if form.is_valid():
            form.save()
            messages.success(request, 'Stock updated successfully!')
            return redirect('stock_details', pk=pk)
    else:
        form = StockForm(instance=stock)
    return render(request, 'edit-stock.html', {'form': form, 'stock': stock})

@login_required
def add_stock(request):
    if request.method == 'POST':
        form = StockForm(request.POST)
        if form.is_valid():
            stock = form.save(commit=False)
            stock.user = request.user
            stock.save()
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'stock': {'id': stock.id, 'name': stock.name}})
            messages.success(request, 'Stock added successfully!')
            return redirect('stock_list')
    else:
        form = StockForm()
    return render(request, 'add-stock.html', {'form': form})


@login_required
def earnings_history(request):
    stocks = Stock.objects.filter(user=request.user, is_active=False).annotate(
        buy_quantity=Sum('transactions__quantity', filter=Q(transactions__transaction_type='buy')),
        sell_quantity=Sum('transactions__quantity', filter=Q(transactions__transaction_type='sell')),
        buy_amount=Sum(F('transactions__quantity') * F('transactions__price'), filter=Q(transactions__transaction_type='buy')),
        sell_amount=Sum(F('transactions__quantity') * F('transactions__price'), filter=Q(transactions__transaction_type='sell')),
    ).exclude(sell_amount__isnull=True)
    
    # Calculate profit/loss for each stock
    earnings = []
    for stock in stocks:
        quantity_sold = stock.sell_quantity or 0
        # Calculate weighted average prices
        avg_buy_price = stock.buy_amount / stock.buy_quantity if stock.buy_quantity and stock.buy_quantity > 0 else 0
        avg_sell_price = stock.sell_amount / stock.sell_quantity if stock.sell_quantity and stock.sell_quantity > 0 else 0
        
        profit_loss = (avg_sell_price - avg_buy_price) * quantity_sold
        profit_loss_percent = (avg_sell_price - avg_buy_price) / avg_buy_price * 100 if avg_buy_price > 0 else 0
        
        earnings.append({
            'name': stock.name,
            'symbol': stock.symbol,
            'id': stock.id,
            'quantity': quantity_sold,
            'avg_buy_price': avg_buy_price,
            'avg_sell_price': avg_sell_price,
            'profit_loss': profit_loss,
            'profit_loss_percent': profit_loss_percent,
        })
    
    # Calculate totals
    total = {
        'avg_buy': sum(e['avg_buy_price'] for e in earnings) / len(earnings) if earnings else 0,
        'avg_sell': sum(e['avg_sell_price'] for e in earnings) / len(earnings) if earnings else 0,
        'profit_loss': sum(e['profit_loss'] for e in earnings),
        'profit_loss_percent': sum(e['profit_loss'] for e in earnings) / sum(e['avg_buy_price'] * e['quantity'] for e in earnings) * 100 if earnings else 0,
    }
    
    return render(request, 'earnings-history.html', {
        'earnings': earnings,
        'total': total,
    })

@login_required
def stock_transaction_history(request, pk):
    stock = get_object_or_404(Stock, pk=pk, user=request.user)
    transactions = stock.transactions.all()
    return render(request, 'stock-transaction-history.html', {'transactions': transactions})

def signup(request):
    if request.method == 'POST':
        form = CustomSignupForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form = CustomSignupForm()
    return render(request, 'signup.html', {'form': form})

@login_required
def dividend_list(request):
    dividends = Dividend.objects.filter(user=request.user)
    filter_param = request.GET.get('filter')
    if filter_param == 'recent':
        dividends = dividends.order_by('-date')
    elif filter_param == 'highest':
        dividends = dividends.order_by('-amount')
    elif filter_param == 'impact':
        dividends = dividends.filter(impact_average=True)
    return render(request, 'dividends.html', {'dividends': dividends})

@login_required
def add_dividend(request):
    if request.method == 'POST':
        form = DividendForm(request.POST, user=request.user)
        if form.is_valid():
            dividend = form.save(commit=False)
            dividend.user = request.user
            dividend.save()
            return redirect('dividend_list')
    else:
        form = DividendForm(user=request.user)
    return render(request, 'dividend-form.html', {'form': form})

@login_required
def edit_dividend(request, pk):
    dividend = get_object_or_404(Dividend, pk=pk, user=request.user)
    if request.method == 'POST':
        form = DividendForm(request.POST, instance=dividend, user=request.user)
        if form.is_valid():
            form.save()
            return redirect('dividend_list')
    else:
        form = DividendForm(instance=dividend, user=request.user)
    return render(request, 'dividend-form.html', {'form': form})

@login_required
def delete_dividend(request, pk):
    dividend = get_object_or_404(Dividend, pk=pk, user=request.user)
    if request.method == 'POST':
        dividend.delete()
        messages.success(request, 'Dividend deleted successfully!')
        return redirect('dividend_list')
    return render(request, 'del-dividend.html', {'dividend': dividend})

# Monthly Deposit Views
@login_required
def monthly_deposit_list(request):
    deposits = MonthlyDeposit.objects.filter(user=request.user).order_by('-deposit_date')
    
    # Calculate summary statistics
    total_deposits = deposits.aggregate(total=Sum('amount'))['total'] or 0
    current_year = datetime.now().year
    current_year_deposits = deposits.filter(deposit_date__year=current_year).aggregate(total=Sum('amount'))['total'] or 0
    
    # Calculate average monthly deposit
    deposit_count = deposits.count()
    average_monthly = total_deposits / deposit_count if deposit_count > 0 else 0
    
    # Monthly summary for current year
    monthly_summary = deposits.filter(deposit_date__year=current_year).annotate(
        month=TruncMonth('deposit_date')
    ).values('month').annotate(
        total_amount=Sum('amount'),
        deposit_count=Sum(1)
    ).order_by('month')
    
    # Broker-wise summary
    broker_summary = deposits.values('broker__name').annotate(
        total_amount=Sum('amount'),
        deposit_count=Sum(1)
    ).order_by('-total_amount')
    
    return render(request, 'monthly-deposits.html', {
        'deposits': deposits,
        'total_deposits': total_deposits,
        'current_year_deposits': current_year_deposits,
        'average_monthly': average_monthly,
        'monthly_summary': monthly_summary,
        'broker_summary': broker_summary,
    })

@login_required
def add_monthly_deposit(request):
    if request.method == 'POST':
        form = MonthlyDepositForm(request.POST, user=request.user)
        if form.is_valid():
            deposit = form.save(commit=False)
            deposit.user = request.user
            deposit.save()
            messages.success(request, 'Monthly deposit added successfully!')
            return redirect('monthly_deposit_list')
    else:
        form = MonthlyDepositForm(user=request.user)
    
    return render(request, 'monthly-deposit-form.html', {'form': form, 'title': 'Add Monthly Deposit'})

@login_required
def edit_monthly_deposit(request, pk):
    deposit = get_object_or_404(MonthlyDeposit, pk=pk, user=request.user)
    if request.method == 'POST':
        form = MonthlyDepositForm(request.POST, instance=deposit, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Monthly deposit updated successfully!')
            return redirect('monthly_deposit_list')
    else:
        form = MonthlyDepositForm(instance=deposit, user=request.user)
    
    return render(request, 'monthly-deposit-form.html', {'form': form, 'title': 'Edit Monthly Deposit', 'deposit': deposit})

@login_required
def delete_monthly_deposit(request, pk):
    deposit = get_object_or_404(MonthlyDeposit, pk=pk, user=request.user)
    
    # Calculate amounts after deletion
    free_amount_after_deletion = deposit.broker.free_amount - deposit.amount
    total_amount_after_deletion = deposit.broker.total_amount - deposit.amount
    
    if request.method == 'POST':
        deposit.delete()
        messages.success(request, 'Monthly deposit deleted successfully!')
        return redirect('monthly_deposit_list')
    return render(request, 'del-monthly-deposit.html', {
        'deposit': deposit,
        'free_amount_after_deletion': free_amount_after_deletion,
        'total_amount_after_deletion': total_amount_after_deletion,
    })

@login_required
def monthly_deposit_chart_data(request):
    """API endpoint for chart data"""
    deposits = MonthlyDeposit.objects.filter(user=request.user)
    
    # Monthly data for the last 12 months
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    
    monthly_data = deposits.filter(
        deposit_date__range=[start_date, end_date]
    ).annotate(
        month=TruncMonth('deposit_date')
    ).values('month').annotate(
        total_amount=Sum('amount')
    ).order_by('month')
    
    # Prepare chart data
    labels = []
    data = []
    
    current_date = start_date.replace(day=1)
    while current_date <= end_date:
        month_key = current_date.strftime('%Y-%m-01')
        labels.append(current_date.strftime('%b %Y'))
        
        # Find data for this month
        month_data = next((item for item in monthly_data if item['month'].strftime('%Y-%m-01') == month_key), None)
        data.append(float(month_data['total_amount']) if month_data else 0)
        
        # Move to next month
        if current_date.month == 12:
            current_date = current_date.replace(year=current_date.year + 1, month=1)
        else:
            current_date = current_date.replace(month=current_date.month + 1)
    
    return JsonResponse({
        'labels': labels,
        'data': data,
    })

# Portfolio Snapshot Views
@login_required
def portfolio_snapshots(request):
    """View for listing portfolio snapshots"""
    snapshots = MonthlyPortfolioSnapshot.objects.filter(user=request.user).order_by('-snapshot_date')
    
    # Get latest snapshot for summary
    latest_snapshot = snapshots.first()
    
    # Calculate summary statistics
    total_snapshots = snapshots.count()
    if total_snapshots > 0:
        total_invested = snapshots.aggregate(total=Sum('total_invested_amount'))['total'] or 0
        total_portfolio_value = snapshots.aggregate(total=Sum('total_portfolio_value'))['total'] or 0
        avg_profit_loss = snapshots.aggregate(avg=Avg('total_profit_loss'))['avg'] or 0
        avg_profit_percentage = snapshots.aggregate(avg=Avg('profit_loss_percentage'))['avg'] or 0
    else:
        total_invested = total_portfolio_value = avg_profit_loss = avg_profit_percentage = 0
    
    # Get monthly growth data for charts
    monthly_growth = snapshots[:12]  # Last 12 months
    
    return render(request, 'portfolio-snapshots.html', {
        'snapshots': snapshots,
        'latest_snapshot': latest_snapshot,
        'total_snapshots': total_snapshots,
        'total_invested': total_invested,
        'total_portfolio_value': total_portfolio_value,
        'avg_profit_loss': avg_profit_loss,
        'avg_profit_percentage': avg_profit_percentage,
        'monthly_growth': monthly_growth,
    })

@login_required
def generate_snapshot(request):
    """Manually generate a portfolio snapshot"""
    if request.method == 'POST':
        try:
            # Get the target date (default to today)
            target_date_str = request.POST.get('snapshot_date')
            if target_date_str:
                target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
            else:
                target_date = datetime.now().date()
            
            # Create the snapshot
            snapshot = MonthlyPortfolioSnapshot.create_monthly_snapshot(request.user, target_date)
            
            messages.success(
                request, 
                f'Portfolio snapshot created for {snapshot.snapshot_date.strftime("%B %d, %Y")}. '
                f'Portfolio Value: Rs. {snapshot.total_portfolio_value:,.0f}, '
                f'Invested: Rs. {snapshot.total_invested_amount:,.0f}, '
                f'P&L: Rs. {snapshot.total_profit_loss:,.0f} ({snapshot.profit_loss_percentage:+.1f}%)'
            )
            
            return redirect('portfolio_snapshots')
            
        except Exception as e:
            messages.error(request, f'Error generating snapshot: {str(e)}')
    
    return render(request, 'generate-snapshot.html', {
        'today_date': datetime.now().date()
    })

@login_required
def snapshot_detail(request, pk):
    """View detailed information about a specific snapshot"""
    snapshot = get_object_or_404(MonthlyPortfolioSnapshot, pk=pk, user=request.user)
    
    # Get stocks data for this snapshot date
    stocks = Stock.objects.filter(user=request.user, is_active=True)
    stock_details = []
    
    for stock in stocks:
        if stock.total_quantity > 0:
            stock_value = stock.total_quantity * stock.avg_price
            stock_details.append({
                'name': stock.name,
                'symbol': stock.symbol,
                'quantity': stock.total_quantity,
                'avg_price': stock.avg_price,
                'current_value': stock_value,
                'percentage': (stock_value / snapshot.total_portfolio_value * 100) if snapshot.total_portfolio_value > 0 else 0
            })
    
    # Sort by value (highest first)
    stock_details.sort(key=lambda x: x['current_value'], reverse=True)
    
    return render(request, 'snapshot-detail.html', {
        'snapshot': snapshot,
        'stock_details': stock_details,
    })

@login_required
def delete_snapshot(request, pk):
    """Delete a portfolio snapshot"""
    snapshot = get_object_or_404(MonthlyPortfolioSnapshot, pk=pk, user=request.user)
    
    if request.method == 'POST':
        snapshot.delete()
        messages.success(request, 'Portfolio snapshot deleted successfully!')
        return redirect('portfolio_snapshots')
    
    return render(request, 'del-snapshot.html', {'snapshot': snapshot})

@login_required
def refresh_market_cache(request):
    """Refresh market data cache manually"""
    from .utils import fetch_market_watch_data, get_cache_status
    
    try:
        # Fetch fresh data (this will automatically cache it)
        df = fetch_market_watch_data(use_cache=False)
        
        if df is not None and not df.empty:
            cache_status = get_cache_status()
            return JsonResponse({
                'success': True,
                'message': f'Cache refreshed successfully! Fetched {len(df)} data points.',
                'cache_status': cache_status
            })
        else:
            return JsonResponse({
                'success': False,
                'message': 'Failed to refresh cache - API error'
            })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error refreshing cache: {str(e)}'
        })


@login_required
def portfolio_growth_chart_data(request):
    """API endpoint for portfolio growth chart data"""
    snapshots = MonthlyPortfolioSnapshot.objects.filter(user=request.user).order_by('snapshot_date')
    
    # Prepare chart data
    labels = []
    invested_data = []
    portfolio_data = []
    profit_loss_data = []
    
    for snapshot in snapshots:
        labels.append(snapshot.snapshot_date.strftime('%b %Y'))
        invested_data.append(float(snapshot.total_invested_amount))
        portfolio_data.append(float(snapshot.total_portfolio_value))
        profit_loss_data.append(float(snapshot.total_profit_loss))
    
    return JsonResponse({
        'labels': labels,
        'invested_data': invested_data,
        'portfolio_data': portfolio_data,
        'profit_loss_data': profit_loss_data,
    })
