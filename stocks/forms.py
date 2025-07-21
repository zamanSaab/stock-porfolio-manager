from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from .models import Broker, Transaction, Stock, Dividend, MonthlyDeposit
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from decimal import Decimal
from django.utils import timezone


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
    date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        initial=timezone.now().date()
    )
    commission = forms.DecimalField(
        label='Commission', required=False, decimal_places=2, max_digits=10, min_value=0,
        help_text='Default commission rate = 0.15%'
    )
    sales_tax = forms.DecimalField(
        label='Sales Tax', required=False, decimal_places=2, max_digits=10, min_value=0,
        help_text='Default sales tax rate = 0.0225%'
    )
    cdc_charges = forms.DecimalField(
        label='CDC Charges', required=False, decimal_places=2, max_digits=10, min_value=0,
        help_text='Default CDC charges rate = 0.5%'
    )
    class Meta:
        model = Transaction
        fields = ['stock', 'quantity', 'broker', 'price', 'transaction_type', 'commission', 'sales_tax', 'cdc_charges', 'date']

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
        sales_tax = cleaned_data.get('sales_tax')
        commission = cleaned_data.get('commission')
        cdc_charges = cleaned_data.get('cdc_charges')
        date = cleaned_data.get('date')

        if not date:
            self.add_error('date', 'Please select a date.')

        # Convert to Decimal for precise calculations
        quantity = Decimal(str(quantity)) if quantity else Decimal('0')
        price = Decimal(str(price)) if price else Decimal('0')
        sales_tax = Decimal(str(sales_tax)) if sales_tax else Decimal('0')
        commission = Decimal(str(commission)) if commission else Decimal('0')
        cdc_charges = Decimal(str(cdc_charges)) if cdc_charges else Decimal('0')

        total_amount = quantity * price
        commission_rate = Decimal('0.0015')  # 0.2%
        sales_tax_rate = Decimal('0.000225')  # 0.15% 
        cdc_rate = Decimal('0.005')  # 0.01%
        
        if not sales_tax:
            sales_tax = total_amount * sales_tax_rate
        if not commission:
            commission = total_amount * commission_rate
        if not cdc_charges:
            cdc_charges = quantity * cdc_rate

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

        # Calculate adjusted price with proper decimal handling
        if quantity > 0:
            charges_per_share = (sales_tax + commission + cdc_charges) / quantity
            if transaction_type == 'buy':
                new_price = price + charges_per_share
            else:  # sell
                new_price = price - charges_per_share
            # Ensure exactly 2 decimal places
            cleaned_data['price'] = new_price.quantize(Decimal('0.01'))
        else:
            cleaned_data['price'] = price.quantize(Decimal('0.01'))

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

class MonthlyDepositForm(forms.ModelForm):
    class Meta:
        model = MonthlyDeposit
        fields = ['broker', 'amount', 'deposit_date', 'description']
        widgets = {
            'deposit_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'description': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Optional description (e.g., Salary, Bonus, etc.)'
            }),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user:
            self.fields['broker'].queryset = Broker.objects.filter(user=user)
        
        for field in self.fields:
            if field != 'description':
                self.fields[field].widget.attrs.update({
                    'class': 'form-control',
                })

    def clean(self):
        cleaned_data = super().clean()
        broker = cleaned_data.get('broker')
        deposit_date = cleaned_data.get('deposit_date')
        amount = cleaned_data.get('amount')

        if amount and amount <= 0:
            self.add_error('amount', 'Deposit amount must be greater than zero.')

        # Check if deposit already exists for this broker on this date
        if broker and deposit_date:
            existing_deposit = MonthlyDeposit.objects.filter(
                broker=broker,
                deposit_date=deposit_date
            ).exclude(pk=self.instance.pk if self.instance.pk else None)
            
            if existing_deposit.exists():
                self.add_error('deposit_date', f'A deposit already exists for {broker.name} on {deposit_date}.')

        return cleaned_data
