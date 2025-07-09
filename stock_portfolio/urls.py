from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('stocks/', include('stocks.urls')),
    path('', include('stocks.urls')),
]