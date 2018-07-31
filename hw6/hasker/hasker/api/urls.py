from django.urls import path, include

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView
)

from . import views


app_name = "api"

questions_patterns = ([
    path("", views.QuestionListView.as_view(sort_by_date=True), name="index"),
    path("hot/", views.QuestionListView.as_view(), name="hot"),
    path("search/", views.QuestionListView.as_view(), name="search"),
    path("<int:q_id>/", views.QuestionDetailView.as_view(), name="detail"),
    path("<int:q_id>/answers/", views.AnswerListView.as_view(), name="answers"),
], "question")

token_patterns = ([
    path("", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("refresh/", TokenRefreshView.as_view(), name='token_refresh'),
    path("verify/", TokenVerifyView.as_view(), name='token_verify'),
], "token")

urlpatterns = [
    path("token/", include(token_patterns)),
    path("questions/", include(questions_patterns)),
]
