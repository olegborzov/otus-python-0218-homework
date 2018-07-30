from django.urls import path

from . import views


urlpatterns = [
    # Main page
    path(
        "",
        views.QuestionList.as_view(
            sort_by_date=True, title="Главная"
        ),
        name="home_page"
    ),
    path(
        "hot/",
        views.QuestionList.as_view(title="Лучшие вопросы"),
        name="question_hot"
    ),

    # Questions
    path("ask/", views.QuestionAddView.as_view(), name="question_add"),
    path(
        "question/<int:id>/",
        views.QuestionDetailView.as_view(),
        name="question_page"
    ),
    path(
        "question/<int:id>/edit/",
        views.QuestionEditView.as_view(),
        name="question_edit"
    ),
    path("vote/", views.vote, name="vote"),
    path(
        "choose_answer/<int:a_id>/",
        views.choose_correct_answer,
        name="choose_correct_answer"
    ),

    # Tags
    path("tag/add/", views.add_tag, name="question_tag_add"),
    path(
        "tag/<str:name>/",
        views.QuestionList.as_view(),
        name="question_tag_page"
    ),

    # Search
    path(
        "search/",
        views.QuestionList.as_view(),
        name="question_search_results"
    )
]
