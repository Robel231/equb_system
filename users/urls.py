from django.urls import path
from . import views

app_name = 'users'
urlpatterns = [
    path('', views.register, name='register'),  # Maps /register/ to the register view
    path('upload-kyc/', views.upload_kyc, name='upload_kyc'),
]