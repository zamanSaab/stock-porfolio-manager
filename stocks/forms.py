from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from .models import Broker, Transaction, Stock, Dividend
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model


class BrokerForm(forms.ModelForm):
    class Meta:
        model = Broker
        fields = ['name', 'code', 'total_amount', 'free_amount']

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['name'].queryset = Broker.objects.filter(user=user)

class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ['stock', 'quantity', 'broker', 'price', 'transaction_type']

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['stock'].queryset = Stock.objects.filter(user=user, is_active=True)
            self.fields['broker'].queryset = Broker.objects.filter(user=user)

    def clean(self):
        cleaned_data = super().clean()
        stock = cleaned_data.get('stock')
        transaction_type = cleaned_data.get('transaction_type')
        quantity = cleaned_data.get('quantity')
        broker = cleaned_data.get('broker')
        price = cleaned_data.get('price')

        # if transaction_type == 'sell' and stock and quantity is not None and stock.total_quantity is not None:
        #     if quantity > stock.total_quantity:
        #         self.add_error('quantity', 'Sell quantity cannot exceed the available buy quantity.')

        # Check if broker has sufficient quantity for sell transactions
        if transaction_type == 'sell' and stock and broker and quantity is not None:
            # Calculate total buy quantity from this broker for this stock
            broker_buy_quantity = sum(
                t.quantity for t in stock.transactions.filter(
                    broker=broker, 
                    transaction_type='buy'
                )
            )
            # Calculate total sell quantity from this broker for this stock
            broker_sell_quantity = sum(
                t.quantity for t in stock.transactions.filter(
                    broker=broker, 
                    transaction_type='sell'
                )
            )
            # Available quantity from this broker
            broker_available_quantity = broker_buy_quantity - broker_sell_quantity
            
            if quantity > broker_available_quantity:
                self.add_error('quantity', f'Insufficient quantity from this broker. Available: {broker_available_quantity}, Requested: {quantity}')

        # Check if broker has sufficient free cash for buy transactions
        if transaction_type == 'buy' and broker and quantity is not None and price is not None:
            required_amount = quantity * price
            if required_amount > broker.free_amount:
                self.add_error('quantity', f'Insufficient funds. Required: Rs. {required_amount:.2f}, Available: Rs. {broker.free_amount:.2f}')

        return cleaned_data

class StockForm(forms.ModelForm):
    class Meta:
        model = Stock
        fields = ['name', 'symbol', 'free_float', 'tax', 'stop_loss', 'target1', 'target2']

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['name'].queryset = Stock.objects.filter(user=user, is_active=True)

class CustomLoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'}))

class CustomSignupForm(UserCreationForm):
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    email = forms.EmailField(max_length=255, required=True)
    terms = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'termsCheck'})
    )
    
    class Meta:
        model = get_user_model()
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2', 'terms')

class DividendForm(forms.ModelForm):
    class Meta:
        model = Dividend
        fields = ['stock', 'amount', 'date', 'impact_average']
        widgets = {
            'date': forms.DateInput(attrs={'class': 'form-control'}),
            'impact_average': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user:
            self.fields['stock'].queryset = user.stocks.filter(is_active=True)
        
        for field in self.fields:
            self.fields[field].widget.attrs.update({
                'class': 'form-control',
            })
        
        self.fields['impact_average'].label = 'Include in Stocks average price calculations'
        self.fields['impact_average'].widget.attrs.update({'style': 'margin-top: 2px;'})
