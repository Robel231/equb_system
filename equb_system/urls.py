from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('equb.urls', namespace='equb')),
    path('register/', include('users.urls', namespace='users')),
    path('accounts/', include('django.contrib.auth.urls')),  # Added prefix to avoid conflict
    path('payments/', include('payments.urls', namespace='payments')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)