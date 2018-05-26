import datetime

from django.db import models
from django.utils import timezone


# Create your models here

class Question(models.Model):
    text = models.CharField(max_length=200)
    pub_date = models.DateTimeField('date published')

    def __str__(self):
        return self.text

    def was_published_recently(self):
        now = timezone.now()
        day_ago = now - datetime.timedelta(days=1)
        return day_ago <= self.pub_date <= now


class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    text = models.CharField(max_length=200)
    votes = models.IntegerField(default=0)

    def __str__(self):
        return self.text
