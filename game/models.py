from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from django.db import models
from django.utils import timezone

# Modelo de Perfil
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    nickname = models.CharField("Apelido", max_length=30, unique=True)
    avatar = models.ImageField(
        upload_to="avatars/", blank=True, null=True
    )
    
    total_games = models.PositiveIntegerField(default=0)
    wins = models.PositiveIntegerField(default=0)
    losses = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.nickname or self.user.username

    @property
    def win_rate(self):
        jogos_validos = self.wins + self.losses
        if jogos_validos == 0:
            return 0
        return round(self.wins * 100 / jogos_validos)

# -------------- Modo Multiplayer --------------
class GameRoom(models.Model):
    code = models.CharField(max_length=8, unique=True, db_index=True)
    host = models.ForeignKey(User, on_delete=models.CASCADE, related_name="hosted_rooms")
    # 'lobby' enquanto aguardando configurações/jogadores, 'active' durante a partida, 'finished' ao final
    status = models.CharField(max_length=16, default="lobby")
    is_active = models.BooleanField(default=True)  # mantém compatibilidade com seu código atual
    is_public = models.BooleanField(default=False)

    board_size = models.CharField(max_length=10, default="10x10")  # "10x10" | "5x5"
    current_turn = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="current_turn_rooms"
    )

    # Mapas fixados quando a partida é iniciada (todos os jogadores veem o mesmo)
    snakes_map = models.JSONField(null=True, blank=True, default=dict)
    ladders_map = models.JSONField(null=True, blank=True, default=dict)

    # Log no estilo do singleplayer (lista de rodadas, cada rodada é lista de eventos)
    # Evento: {"username": str|None, "order": int|None, "texto": str}
    log_rounds = models.JSONField(null=True, blank=True, default=list)
    round_number = models.IntegerField(default=1)

    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Room {self.code} ({self.status})"


class GamePlayer(models.Model):
    room = models.ForeignKey(GameRoom, related_name="players", on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=0)  # ordem de jogo
    position = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("room", "user")
        ordering = ("order", "id")

    def __str__(self):
        return f"{self.room.code} - {self.user} (ordem {self.order})"


# ---------------- Amigos & Convites ----------------

class FriendRequest(models.Model):
    requester = models.ForeignKey(User, related_name="friend_requests_sent", on_delete=models.CASCADE)
    addressee = models.ForeignKey(User, related_name="friend_requests_received", on_delete=models.CASCADE)
    status = models.CharField(max_length=16, default="pending")  # pending | accepted | declined
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ("requester", "addressee")

    def __str__(self):
        return f"{self.requester} -> {self.addressee} ({self.status})"


class RoomInvite(models.Model):
    room = models.ForeignKey(GameRoom, related_name="invites", on_delete=models.CASCADE)
    inviter = models.ForeignKey(User, related_name="room_invites_sent", on_delete=models.CASCADE)
    invitee = models.ForeignKey(User, related_name="room_invites_received", on_delete=models.CASCADE)
    status = models.CharField(max_length=16, default="pending")  # pending | accepted | declined
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ("room", "invitee")

    def __str__(self):
        return f"Invite {self.room.code}: {self.inviter} -> {self.invitee} ({self.status})"