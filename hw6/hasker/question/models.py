from django.db import models
from django.db.models import F
from django.urls import reverse

from django.conf import settings


# Create your models here.
class AbstractQA(models.Model):
    text = models.TextField("Содержимое", max_length=5000)
    published = models.DateTimeField("Дата публикации", auto_now_add=True)
    updated = models.DateTimeField("Дата изменения", auto_now=True)

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE
    )

    class Meta:
        abstract = True
        ordering = [F('dislikes') - F('likes'), '-published']


class Tag(models.Model):
    name = models.CharField("Тег", max_length=50, primary_key=True)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('tag_page', kwargs={'name': self.name})


class Question(AbstractQA):
    title = models.CharField("Заголовок", max_length=200)

    tags = models.ManyToManyField(Tag, blank=True, related_name="questions")
    likers = models.ManyToManyField(
        settings.AUTH_USER_MODEL, related_name="q_likes"
    )
    dislikers = models.ManyToManyField(
        settings.AUTH_USER_MODEL, related_name="q_dislikes"
    )

    def get_absolute_url(self):
        return reverse('question_page', kwargs={'id': self.pk})


class Answer(AbstractQA):
    is_correct = models.BooleanField("Правильный ответ")

    question = models.ForeignKey(
        Question, related_name="answers", on_delete=models.CASCADE
    )
    likers = models.ManyToManyField(
        settings.AUTH_USER_MODEL, related_name="a_likes"
    )
    dislikers = models.ManyToManyField(
        settings.AUTH_USER_MODEL, related_name="a_dislikes"
    )
