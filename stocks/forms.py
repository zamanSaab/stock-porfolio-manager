from django import forms
from .models import Broker, Transaction, Stock

class BrokerForm(forms.ModelForm):
    class Meta:
        model = Broker
        fields = ['name', 'code', 'total_amount', 'free_amount']

class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ['stock', 'quantity', 'broker', 'price', 'transaction_type']

class StockForm(forms.ModelForm):
    class Meta:
        model = Stock
        fields = ['name', 'symbol', 'free_float', 'tax', 'stop_loss', 'target1', 'target2']
