from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from .models import Broker, Stock, Transaction, Dividend
from .forms import BrokerForm, TransactionForm, StockForm, DividendForm, CustomSignupForm
from .utils import fetch_market_watch_data
from django.db.models import Sum, Case, When, IntegerField, Avg, Q, F, FloatField, ExpressionWrapper
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
import json

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

    for stock in stocks:
        avg_price = stock.total_price / stock.total_quantity if stock.total_quantity > 0 else 0
        value = avg_price * stock.total_quantity
        total_value += value
        stock_data.append({
            'name': stock.name,
            'symbol': stock.symbol,
            'value': int(value),
            'quantity': stock.quantity,  # Add quantity for template
            "exploded": True,
            # 'change': current_price - avg_price
        })
    for data in stock_data:
        data['y'] = int((data['value']  / total_value)*100) if total_value > 0 else 0

    top_holdings = sorted(stock_data, key=lambda x: x['value'], reverse=True)[:5]

    # Example dynamic portfolio performance data (replace with real calculations as needed)
    performance_labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    performance_datasets = [
        {
            "label": "My Portfolio",
            "data": [100, 105, 112, 108, 118, 125],
            "borderColor": "#4e73df",
            "backgroundColor": "rgba(78, 115, 223, 0.1)",
            "borderWidth": 2,
            "tension": 0.4,
            "fill": True
        },
        {
            "label": "NIFTY 50",
            "data": [100, 102, 104, 101, 107, 110],
            "borderColor": "#858796",
            "backgroundColor": "rgba(133, 135, 150, 0.1)",
            "borderWidth": 2,
            "borderDash": [5, 5],
            "tension": 0.4,
            "fill": True
        }
    ]
    performance_labels_json = json.dumps(performance_labels)
    performance_datasets_json = json.dumps(performance_datasets)

    return render(request, 'index.html', {
        'top_holdings': top_holdings,
        'total_gain': 12840,
        'gain_percent': 18.1,
        'current_portfolio_gain': -1900,
        'current_portfolio': 947000,
        'dividend': 42300,
        'total_free_amount': sum(broker.free_amount for broker in Broker.objects.filter(user=request.user)),
        'stock_data_json': json.dumps(stock_data),
        'performance_labels_json': performance_labels_json,
        'performance_datasets_json': performance_datasets_json,
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
        return redirect('dividend_list')
    return render(request, 'del-dividend.html', {'dividend': dividend})
