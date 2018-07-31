from django.core.exceptions import PermissionDenied

from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import CreateView, UpdateView, DetailView

from django.shortcuts import redirect
from django.urls import reverse_lazy

from .forms import UserSignupForm, UserEditForm, LoginForm
from .models import User


# Create your views here.
class NotLoggedInMixin(UserPassesTestMixin):
    request = None

    def test_func(self):
        return not self.request.user.is_authenticated

    def handle_no_permission(self):
        if self.raise_exception:
            raise PermissionDenied(self.get_permission_denied_message())
        return redirect("question:home")


class HaskerLoginView(NotLoggedInMixin, LoginView):
    form_class = LoginForm
    next = "home_page"
    template_name = "user/login.html"


class HaskerLogoutView(LoginRequiredMixin, LogoutView):
    next = reverse_lazy("question:home")


class HaskerSignupView(NotLoggedInMixin, CreateView):
    form_class = UserSignupForm
    template_name = "user/signup_edit.html"
    success_url = reverse_lazy("user:login")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Регистрация"
        return context


class HaskerUserEditView(LoginRequiredMixin, UpdateView):
    form_class = UserEditForm
    template_name = "user/signup_edit.html"
    success_url = reverse_lazy("user:edit")

    def get_object(self, queryset=None):
        return self.request.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Настройки"
        return context


class UserDetailView(DetailView):
    model = User
    template_name = "user/detail.html"
    context_object_name = "user"
    slug_url_kwarg = "username"
    slug_field = "username"
