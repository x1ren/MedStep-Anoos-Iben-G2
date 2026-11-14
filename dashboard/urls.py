from django.urls import path

from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard_home, name='home'),
    path('student/', views.student_dashboard, name='student'),
    path('instructor/', views.InstructorDashboardView.as_view(), name='instructor'),
]
