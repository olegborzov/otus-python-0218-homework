from django.urls import path, include

from . import views

# TODO:
# index (sort by date)
# hot (sort by votes)
# search (filter by search phrase)
# question_detail
# question_answers

app_name = "api"

questions_patterns = ([
    path(
        "",
        views.QuestionListView.as_view(sort_by_date=True),
        name="index",
    ),
    path(
        "hot/",
        views.QuestionListView.as_view(),
        name="hot"
    ),
    path(
        "search/",
        views.QuestionListView.as_view(),
        name="search"
    ),
    path(
        "<int:q_id>/",
        views.QuestionDetailView.as_view(),
        name="detail"
    ),
    path(
        "<int:q_id>/answers/",
        views.AnswerListView.as_view(),
        name="answers"
    ),
], "question")

urlpatterns = [
    path("auth/", include("rest_framework.urls", namespace="rest_framework")),
    path("questions/", include(questions_patterns)),
]
