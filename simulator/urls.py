from django.urls import path

from . import views

app_name = 'simulator'

urlpatterns = [
    # Lab Admin: Gram stain scenario catalog management
    path('scenarios/', views.ScenarioListView.as_view(), name='scenario_list'),
    path('scenarios/new/', views.ScenarioCreateView.as_view(), name='scenario_create'),
    path('scenarios/<int:pk>/edit/', views.ScenarioUpdateView.as_view(), name='scenario_update'),
    path('scenarios/<int:pk>/delete/', views.ScenarioDeleteView.as_view(), name='scenario_delete'),
]
