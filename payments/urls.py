from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    path('pay-upline/', views.pay_upline, name='pay_upline'),
]