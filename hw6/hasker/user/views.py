from django.core.exceptions import PermissionDenied

from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import CreateView, UpdateView, DetailView

from django.shortcuts import redirect
from django.urls import reverse_lazy, reverse

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
        return redirect(reverse("home_page"))


class HaskerLoginView(NotLoggedInMixin, LoginView):
    form_class = LoginForm
    next = "home_page"
    template_name = "user/login.html"


class HaskerLogoutView(LoginRequiredMixin, LogoutView):
    next = reverse_lazy("home_page")


class HaskerSignupView(NotLoggedInMixin, CreateView):
    form_class = UserSignupForm
    template_name = "user/signup.html"
    success_url = reverse_lazy("home_page")


class HaskerUserEditView(LoginRequiredMixin, UpdateView):
    form_class = UserEditForm
    template_name = "user/edit.html"
    success_url = reverse_lazy("user_edit")

    def get_object(self, queryset=None):
        return self.request.user


class UserDetailView(DetailView):
    model = User
    context_object_name = "user"
    slug_url_kwarg = "username"
    slug_field = "username"
