from django.db import models
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
    likers = models.ManyToManyField(settings.AUTH_USER_MODEL)
    dislikers = models.ManyToManyField(settings.AUTH_USER_MODEL)

    class Meta:
        abstract = True
        ordering = ['-published']

    @property
    def votes(self):
        return self.likers.count() - self.dislikers.count()

    def vote(self, user, like=True):
        if like:
            self.dislikers.remove(user)
            if self.likers.filter(pk=user.pk).exists():
                self.likers.remove(user)
            else:
                self.likers.add(user)
        else:
            self.likers.remove(user)
            if self.dislikers.filter(pk=user.pk).exists():
                self.dislikers.remove(user)
            else:
                self.dislikers.add(user)


class Tag(models.Model):
    name = models.CharField("Тег", max_length=50, primary_key=True)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("question_tag_page", kwargs={'name': self.name})

    @property
    def url(self):
        return self.get_absolute_url()


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

    @property
    def url(self):
        return self.get_absolute_url()


class Answer(AbstractQA):
    text = models.TextField("Ваш ответ", max_length=5000)
    is_correct = models.BooleanField("Правильный ответ", default=False)

    question = models.ForeignKey(
        Question, related_name="answers", on_delete=models.CASCADE
    )
    likers = models.ManyToManyField(
        settings.AUTH_USER_MODEL, related_name="a_likes"
    )
    dislikers = models.ManyToManyField(
        settings.AUTH_USER_MODEL, related_name="a_dislikes"
    )
