from django.urls import path
from Apps.accounts.views import EmailLoginView, RegisterView, logout_view

urlpatterns = [
    path('login/', EmailLoginView.as_view(), name='login'),
    path('register/', RegisterView.as_view(), name='register'),
    path('logout/', logout_view, name='logout'),
]