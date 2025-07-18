from django.urls import path
from django.contrib.auth import views as auth_views
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
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('signup/', views.signup, name='signup'),
    path('password-reset/', auth_views.PasswordResetView.as_view(template_name='password_reset.html'), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='password_reset_complete.html'), name='password_reset_complete'),

    path('dividends/', views.dividend_list, name='dividend_list'),
    path('dividends/add/', views.add_dividend, name='add_dividend'),
    path('dividends/<int:pk>/edit/', views.edit_dividend, name='edit_dividend'),
    path('dividends/<int:pk>/delete/', views.delete_dividend, name='delete_dividend'),
]
