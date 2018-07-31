from django.urls import path

from . import views


app_name = 'user'
urlpatterns = [
    # Auth
    path("login/", views.HaskerLoginView.as_view(), name="login"),
    path("logout/", views.HaskerLogoutView.as_view(), name="logout"),
    path("signup/", views.HaskerSignupView.as_view(), name="signup"),


    # User pages
    path("settings/", views.HaskerUserEditView.as_view(), name="edit"),
    path(
        "<slug:username>/",
        views.UserDetailView.as_view(),
        name="profile"
    ),
]
