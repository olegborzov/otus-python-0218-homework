from django.db import models
from django.urls import reverse
from django.contrib.auth.models import AbstractUser


# Create your models here.
class User(AbstractUser):
    registered = models.DateTimeField(auto_now_add=True)
    avatar = models.ImageField(
        verbose_name="Аватарка", upload_to="avatars",
        blank=True, null=True
    )

    def get_absolute_url(self):
        return reverse('user:profile', kwargs={'username': self.username})

    @property
    def url(self):
        return self.get_absolute_url()
