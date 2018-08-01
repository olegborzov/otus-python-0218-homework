from django.db.models import F, Q, Count
from django.shortcuts import get_object_or_404

from rest_framework import generics

from hasker.question.views import Question
from . import serializers


class IndexQuestionListView(generics.ListAPIView):
    """
    Index page

    Return paginated set of all questions data (id and url).
    Questions are sorted by date.
    """
    serializer_class = serializers.QuestionListSerializer
    queryset = Question.objects.all()


class HotQuestionListView(generics.ListAPIView):
    """
    Hot questions

    Return paginated set of all questions data (id and url).
    Questions are sorted by votes count and date.
    """
    serializer_class = serializers.QuestionListSerializer

    def get_queryset(self):
        questions = Question.objects.all()

        questions = questions.annotate(
            likes=Count("likers"),
            dislikes=Count("dislikers"),
        ).order_by(F("dislikes") - F("likes"), "-published")

        return questions


class SearchQuestionListView(generics.ListAPIView):
    """
    Search page

    Return paginated set of questions data (id and url),
    filtered by the occurrence of a phrase in title or text.
    Questions are sorted by votes count and date.
    """
    serializer_class = serializers.QuestionListSerializer

    def get_queryset(self):
        search_phrase = self.request.query_params.get("q", "")
        if search_phrase:
            questions = Question.objects.filter(
                Q(title__icontains=search_phrase) |
                Q(text__icontains=search_phrase)
            )
        else:
            questions = Question.objects.all()

        questions = questions.annotate(
            likes=Count("likers"),
            dislikes=Count("dislikers"),
        ).order_by(F("dislikes") - F("likes"), "-published")

        return questions


class QuestionDetailView(generics.RetrieveAPIView):
    """
    Question detail

    Return info about question:
    id, title, text, publish date, author username, tags, votes count,
    answers count and link to AnswerListView page.
    """
    serializer_class = serializers.QuestionSerializer
    queryset = Question.objects.all()
    lookup_url_kwarg = "q_id"


class AnswerListView(generics.ListAPIView):
    """
    Questions answers page

    Return info about answers to qiven question.
    Answer data: id, text, publish date, author username and votes count
    """
    serializer_class = serializers.AnswerSerializer

    def get_queryset(self):
        q_id = self.kwargs.get("q_id")
        question = get_object_or_404(Question, pk=q_id)
        return question.answers.all()
