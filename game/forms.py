from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Profile

class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    nickname = forms.CharField(max_length=30, label="Apelido")

    class Meta:
        model = User
        fields = ("username", "email", "nickname", "password1", "password2")

    def save(self, commit=True):
        user = super().save(commit=commit)
        # cria o Profile ligado ao usuário
        Profile.objects.create(
            user=user,
            nickname=self.cleaned_data["nickname"],
        )
        return user
