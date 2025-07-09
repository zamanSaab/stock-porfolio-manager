from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from .models import Broker, Stock, Transaction
from .forms import BrokerForm, TransactionForm, StockForm
from .utils import fetch_market_watch_data
from django.db.models import Sum, Case, When, IntegerField, Avg, Q

def index(request):
    return render(request, 'base.html')

def broker_list(request):
    brokers = Broker.objects.all()
    total_amount = sum(broker.total_amount for broker in brokers)
    free_amount = sum(broker.free_amount for broker in brokers)
    return render(request, 'brokers.html', {
        'brokers': brokers,
        'total_amount': total_amount,
        'free_amount': free_amount,
    })

def stock_list(request):
    stocks = Stock.objects.annotate(
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

def transaction_list(request):
    transactions = Transaction.objects.all()
    return render(request, 'transactions.html', {'transactions': transactions})


def add_broker(request):
    if request.method == 'POST':
        form = BrokerForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Broker added successfully!')
            return redirect('broker_list')
    else:
        form = BrokerForm()
    return render(request, 'add-broker.html', {'form': form})


def edit_broker(request, pk):
    broker = get_object_or_404(Broker, pk=pk)
    if request.method == 'POST':
        form = BrokerForm(request.POST, instance=broker)
        if form.is_valid():
            form.save()
            messages.success(request, 'Broker updated successfully!')
            return redirect('broker_list')
    else:
        form = BrokerForm(instance=broker)
    return render(request, 'edit-brocker.html', {'form': form, 'broker': broker})


def delete_broker(request, pk):
    broker = get_object_or_404(Broker, pk=pk)
    if request.method == 'POST':
        broker.delete()
        messages.success(request, 'Broker deleted successfully!')
        return redirect('broker_list')
    return render(request, 'del-brocker.html', {'broker': broker})

def add_transaction(request):
    if request.method == 'POST':
        form = TransactionForm(request.POST)
        if form.is_valid():
            transaction = form.save()
            if transaction.transaction_type == 'buy':
                transaction.broker.free_amount -= transaction.quantity * transaction.price
            elif transaction.transaction_type == 'sell':
                transaction.broker.free_amount += transaction.quantity * transaction.price
            transaction.broker.save()
            messages.success(request, 'Transaction added successfully!')
            return redirect('transaction_list')
    else:
        form = TransactionForm()
    return render(request, 'transaction-form.html', {'form': form})


def edit_transaction(request, pk):
    transaction = get_object_or_404(Transaction, pk=pk)
    original_quantity = transaction.quantity
    original_price = transaction.price
    original_type = transaction.transaction_type

    if request.method == 'POST':
        form = TransactionForm(request.POST, instance=transaction)
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
        form = TransactionForm(instance=transaction)
    return render(request, 'transaction-form.html', {'form': form, 'transaction': transaction})


def delete_transaction(request, pk):
    transaction = get_object_or_404(Transaction, pk=pk)
    if request.method == 'POST':
        transaction.delete()
        messages.success(request, 'Transaction deleted successfully!')
        return redirect('transaction_list')
    return render(request, 'del-transaction.html', {'transaction': transaction})

def stock_details(request, pk):
    stock = get_object_or_404(Stock, pk=pk)
    return render(request, 'stock-details.html', {'stock': stock})

def update_market_price(request, pk):
    pass

def fetch_market_price(request, pk):
    stock = get_object_or_404(Stock, pk=pk)
    stock_details = fetch_market_watch_data([stock.symbol])
    stock_details = stock_details.to_dict('records')
    if stock_details:
        current_price = stock_details[0].get('CURRENT')
        return JsonResponse({'success': True, 'market_price': current_price})
    return JsonResponse({'success': False, 'message': 'Stock not found or no market data available.'})

def edit_stock(request, pk):
    stock = get_object_or_404(Stock, pk=pk)
    if request.method == 'POST':
        form = StockForm(request.POST, instance=stock)
        if form.is_valid():
            form.save()
            messages.success(request, 'Stock updated successfully!')
            return redirect('stock_details', pk=pk)
    else:
        form = StockForm(instance=stock)
    return render(request, 'edit-stock.html', {'form': form, 'stock': stock})

def add_stock(request):
    if request.method == 'POST':
        form = StockForm(request.POST)
        if form.is_valid():
            stock = form.save()
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'stock': {'id': stock.id, 'name': stock.name}})
            messages.success(request, 'Stock added successfully!')
            return redirect('stock_list')
    else:
        form = StockForm()
    return render(request, 'add-stock.html', {'form': form})


def earnings_history(request):
    stocks = Stock.objects.annotate(
        avg_buy_price=Avg('transactions__price', filter=Q(transactions__transaction_type='buy')),
        avg_sell_price=Avg('transactions__price', filter=Q(transactions__transaction_type='sell')),
        buy_quantity=Sum('transactions__quantity', filter=Q(transactions__transaction_type='buy')),
        sell_quantity=Sum('transactions__quantity', filter=Q(transactions__transaction_type='sell')),
    ).exclude(avg_sell_price__isnull=True)
    
    # Calculate profit/loss for each stock
    earnings = []
    for stock in stocks:
        quantity_sold = stock.sell_quantity or 0
        profit_loss = (stock.avg_sell_price - stock.avg_buy_price) * quantity_sold
        profit_loss_percent = (stock.avg_sell_price - stock.avg_buy_price) / stock.avg_buy_price * 100
        
        earnings.append({
            'name': stock.name,
            'symbol': stock.symbol,
            'id': stock.id,
            'quantity': quantity_sold,
            'avg_buy_price': stock.avg_buy_price,
            'avg_sell_price': stock.avg_sell_price,
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

def stock_transaction_history(request, pk):
    stock = get_object_or_404(Stock, pk=pk)
    transactions = stock.transactions.all()
    return render(request, 'stock-transaction-history.html', {'transactions': transactions})