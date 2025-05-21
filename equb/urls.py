from django.urls import path
from . import views

app_name = 'equb'
urlpatterns = [
    path('', views.home, name='home'),  # Root path for homepage
    path('dashboard/', views.dashboard, name='dashboard'),
    path('complete-round/', views.complete_round, name='complete_round'),
]