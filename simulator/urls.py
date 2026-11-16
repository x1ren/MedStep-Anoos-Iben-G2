from django.urls import path

from . import views

app_name = 'simulator'

urlpatterns = [
    # Lab Admin: Gram stain scenario catalog management
    path('scenarios/', views.ScenarioListView.as_view(), name='scenario_list'),
    path('scenarios/new/', views.ScenarioCreateView.as_view(), name='scenario_create'),
    path('scenarios/<int:pk>/edit/', views.ScenarioUpdateView.as_view(), name='scenario_update'),
    path('scenarios/<int:pk>/delete/', views.ScenarioDeleteView.as_view(), name='scenario_delete'),

    # Learner: interactive Gram staining workbench
    path('workbench/<int:pk>/', views.workbench, name='workbench'),
    path('workbench/<int:pk>/submit/', views.submit_attempt, name='submit_attempt'),

    # Learner: own simulation attempts (practice log)
    path('attempts/', views.AttemptListView.as_view(), name='attempt_list'),
    path('attempts/<int:pk>/', views.attempt_detail, name='attempt_detail'),
    path('attempts/<int:pk>/notes/', views.attempt_notes, name='attempt_notes'),
    path('attempts/<int:pk>/delete/', views.AttemptDeleteView.as_view(), name='attempt_delete'),
]
