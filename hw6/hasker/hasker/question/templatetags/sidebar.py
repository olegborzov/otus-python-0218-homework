from django import template
from django.conf import settings
from django.db.models import F, Count

from ..models import Question

register = template.Library()


@register.simple_tag
def top_questions():
    questions = Question.objects.all().annotate(
        likes=Count("likers"),
        dislikes=Count("dislikers"),
    ).order_by(
        F("dislikes") - F("likes"), "-published"
    )[:settings.PAGINATE_QUESTIONS]
    return questions
