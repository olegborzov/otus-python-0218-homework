from django.urls import path, include

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView
)
from rest_framework_swagger.views import get_swagger_view

from . import views


app_name = "api"

questions_patterns = ([
    path("", views.IndexQuestionListView.as_view(), name="index"),
    path("hot/", views.HotQuestionListView.as_view(), name="hot"),
    path("search/", views.SearchQuestionListView.as_view(), name="search"),
    path("<int:q_id>/", views.QuestionDetailView.as_view(), name="detail"),
    path("<int:q_id>/answers/", views.AnswerListView.as_view(), name="answers"),
], "question")

token_patterns = ([
    path("", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("refresh/", TokenRefreshView.as_view(), name='token_refresh'),
    path("verify/", TokenVerifyView.as_view(), name='token_verify'),
], "token")

swagger_view = get_swagger_view("Hasker REST API")

urlpatterns = [
    path("token/", include(token_patterns)),
    path("questions/", include(questions_patterns)),
    path("schema/", swagger_view)
]
