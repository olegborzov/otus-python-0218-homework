from django.urls import path

from . import views


urlpatterns = [
    # Auth
    path("login/", views.HaskerLoginView.as_view(), name="login"),
    path("logout/", views.HaskerLogoutView.as_view(), name="logout"),
    path("signup/", views.HaskerSignupView.as_view(), name="signup"),


    # User pages
    path("settings/", views.HaskerUserEditView.as_view(), name="user_edit"),
    path(
        "<slug:username>/",
        views.UserDetailView.as_view(),
        name="user_profile"
    ),
]
