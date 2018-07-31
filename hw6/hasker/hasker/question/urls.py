from django.urls import path, include

from . import views


app_name = 'question'
tags_patterns = ([
    path("add/", views.add_tag, name="add"),
    path("<str:name>/", views.QuestionList.as_view(), name="detail"),
], "tag")
urlpatterns = [
    # Main page
    path(
        "",
        views.QuestionList.as_view(
            sort_by_date=True, title="Главная"
        ),
        name="home"
    ),
    path(
        "hot/",
        views.QuestionList.as_view(title="Лучшие вопросы"),
        name="hot"
    ),

    # Questions
    path(
        "question/<int:id>/",
        views.QuestionDetailView.as_view(),
        name="detail"
    ),
    path(
        "question/<int:id>/edit/",
        views.QuestionEditView.as_view(),
        name="edit"
    ),
    path("ask/", views.QuestionAddView.as_view(), name="add"),
    path("vote/", views.vote, name="vote"),
    path(
        "choose_answer/<int:a_id>/",
        views.choose_correct_answer,
        name="choose_correct_answer"
    ),
    path(
        "search/",
        views.QuestionList.as_view(),
        name="search_results"
    ),

    # Tags
    path("tag/", include(([
        path("add/", views.add_tag, name="add"),
        path("<str:name>/", views.QuestionList.as_view(), name="detail"),
    ], "tag"))),
]
