from django.urls import path
from . import views

urlpatterns = [
    path('producao/', views.registrar_producao, name='registrar_producao'),
]