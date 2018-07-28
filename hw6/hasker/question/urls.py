from django.urls import path

from . import views


urlpatterns = [
    # Main page
    path("", views.test_index, name="home_page"),
    # path("hot/", views.QuestionList.as_view(), name="question_hot"),
    # path("search/", name="questions_search_results"),  # TODO: search

    # TODO: Question pages
    path("ask/", views.QuestionAddView.as_view(), name="question_add"),
    path("question/<int:id>/", views.test_index, name="question_page"),
    path("question/<int:id>/edit/", views.test_index, name="question_edit"),

    # TODO: Tag
    path("tag/add/", views.add_tag, name="question_tag_add"),
    path("tag/<slug:name>/", views.test_index, name="question_tag_page")
]
