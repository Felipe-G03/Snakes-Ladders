from django.db import models
from django.contrib.auth.models import User

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    nickname = models.CharField("Apelido", max_length=30, unique=True)
    avatar = models.ImageField(
        upload_to="avatars/", blank=True, null=True
    )

    def __str__(self):
        return self.nickname or self.user.username
