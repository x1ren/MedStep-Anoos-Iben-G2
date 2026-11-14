"""Test-only URLconf with dummy views protected by the role checks."""

from django.http import HttpResponse
from django.urls import path
from django.views import View

from accounts.decorators import (
    RoleRequiredMixin,
    instructor_required,
    role_required,
    student_required,
)
from accounts.models import User
from medstep.urls import urlpatterns as project_urlpatterns


@student_required
def student_only(request):
    return HttpResponse('student area')


@instructor_required
def instructor_only(request):
    return HttpResponse('instructor area')


@role_required(User.Role.STUDENT, User.Role.INSTRUCTOR)
def any_role(request):
    return HttpResponse('shared area')


class InstructorOnlyView(RoleRequiredMixin, View):
    allowed_roles = (User.Role.INSTRUCTOR,)

    def get(self, request):
        return HttpResponse('instructor cbv')


urlpatterns = project_urlpatterns + [
    path('t/student/', student_only),
    path('t/instructor/', instructor_only),
    path('t/any/', any_role),
    path('t/instructor-cbv/', InstructorOnlyView.as_view()),
]
