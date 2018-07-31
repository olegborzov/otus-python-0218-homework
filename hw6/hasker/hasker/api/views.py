from django.db.models import F, Q, Count

from rest_framework import viewsets
from rest_framework import generics

from hasker.question.views import Question, Answer
from . import serializers


class QuestionListView(generics.ListAPIView):
    serializer_class = serializers.QuestionListSerializer
    queryset = Question.objects.all()

    sort_by_date = False
    search_phrase = ""

    def get_queryset(self):
        self.search_phrase = self.request.query_params.get("q", "")
        if self.search_phrase:
            questions = Question.objects.filter(
                Q(title__icontains=self.search_phrase) |
                Q(text__icontains=self.search_phrase)
            )
        else:
            questions = Question.objects.all()

        if not self.sort_by_date:
            questions = questions.annotate(
                likes=Count("likers"),
                dislikes=Count("dislikers"),
            ).order_by(F("dislikes") - F("likes"), "-published")

        return questions


class QuestionDetailView(generics.RetrieveAPIView):
    serializer_class = serializers.QuestionSerializer
    queryset = Question.objects.all()
    lookup_url_kwarg = "q_id"


class AnswerListView(generics.ListAPIView):
    serializer_class = serializers.AnswerSerializer
    queryset = Answer.objects.all()

    def get_queryset(self):
        q_id = self.kwargs.get("q_id")
        return Answer.objects.filter(question_id=q_id)
