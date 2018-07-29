from django import template
from django.db.models import F, Count
from question.models import Question

register = template.Library()


@register.simple_tag
def top_questions(num):
    questions = Question.objects.all().annotate(
        likes=Count("likers"),
        dislikes=Count("dislikers"),
    ).order_by(F("dislikes") - F("likes"), "-published")[:num]
    return questions
