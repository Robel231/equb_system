from django.urls import path
from . import views

app_name = 'equb'

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('refer/', views.refer_member, name='refer_member'),
]