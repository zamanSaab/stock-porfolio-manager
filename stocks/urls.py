from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('brokers/', views.broker_list, name='broker_list'),
    path('stocks-portfolio/', views.stock_list, name='stock_list'),
    path('transactions/', views.transaction_list, name='transaction_list'),
    path('brokers/add/', views.add_broker, name='add_broker'),
    path('brokers/edit/<int:pk>/', views.edit_broker, name='edit_broker'),
    path('brokers/delete/<int:pk>/', views.delete_broker, name='delete_broker'),
    path('transactions/add/', views.add_transaction, name='add_transaction'),
    path('transactions/edit/<int:pk>/', views.edit_transaction, name='edit_transaction'),
    path('transactions/delete/<int:pk>/', views.delete_transaction, name='delete_transaction'),
    path('stocks/<int:pk>/', views.stock_details, name='stock_details'),
    path('stocks/update-market-price/<int:pk>/', views.update_market_price, name='update_market_price'),
    path('stocks/fetch-market-price/<int:pk>/', views.fetch_market_price, name='fetch_market_price'),
    path('stocks/edit/<int:pk>/', views.edit_stock, name='edit_stock'),
    path('stocks/add/', views.add_stock, name='add_stock'),
    path('earnings-history/', views.earnings_history, name='earnings_history'),
    path('stocks/<int:pk>/transactions/', views.stock_transaction_history, name='stock_transaction_history'),
]
