from django.urls import path
from . import views

app_name = 'payments'
urlpatterns = [
    path('upload-payment/', views.upload_payment, name='upload_payment'),
]