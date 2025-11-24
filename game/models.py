from django.db import models
from django.contrib.auth.models import User
from django.db.models import JSONField

# Modelo de Perfil
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    nickname = models.CharField("Apelido", max_length=30, unique=True)
    avatar = models.ImageField(
        upload_to="avatars/", blank=True, null=True
    )

    def __str__(self):
        return self.nickname or self.user.username

# -------------- Modo Multiplayer --------------
class GameRoom(models.Model):
    code = models.CharField(max_length=8, unique=True)
    host = models.ForeignKey(User, on_delete=models.CASCADE, related_name="rooms_hosted")
    board_size = models.CharField(max_length=10, default="10x10")
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    current_turn = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="turns"
    )

    snakes_map = JSONField(default=dict, blank=True)   # ex.: {"17": 7, "54": 34}
    ladders_map = JSONField(default=dict, blank=True)  # ex.: {"3": 22, "11": 26}

    log_rounds = models.JSONField(default=list, blank=True)   # [[{username,texto}], ...]
    round_number = models.IntegerField(default=1)

    def __str__(self):
        return f"Sala {self.code}"

class GamePlayer(models.Model):
    room = models.ForeignKey(GameRoom, on_delete=models.CASCADE, related_name="players")
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    order = models.PositiveIntegerField()  # ordem de jogo (0,1,2...)
    position = models.PositiveIntegerField(default=0)  # casa atual no tabuleiro

    def __str__(self):
        return f"{self.user.username} em {self.room.code}"