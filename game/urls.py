# game/urls.py
from django.urls import path
from . import views

app_name = "game"

urlpatterns = [
    # telas existentes
    path("", views.tela_inicial, name="tela_inicial"),
    path("instrucoes/", views.tela_instrucoes, name="tela_instrucoes"),

    # singleplayer
    path("iniciar/", views.iniciar_contra_maquina, name="iniciar_contra_maquina"),
    path("jogo/", views.novo_jogo, name="novo_jogo"),
    path("tabuleiro/", views.tela_tabuleiro, name="tela_tabuleiro"),
    path("jogar/", views.jogar_rodada, name="jogar_rodada"),
    path("reiniciar/", views.reiniciar_jogo, name="reiniciar_jogo"),

    # auth / perfil
    path("register/", views.register, name="register"),
    path("profile/", views.profile, name="profile"),

    # multiplayer — lobby global
    path("multiplayer/", views.multiplayer_lobby, name="multiplayer_lobby"),
    path("multiplayer/create/", views.multiplayer_create, name="multiplayer_create"),
    path("multiplayer/join/", views.multiplayer_join, name="multiplayer_join"),

    # sala
    path("room/<str:code>/", views.multiplayer_room, name="multiplayer_room"),
    path("room/<str:code>/config/", views.multiplayer_config, name="multiplayer_config"),
    path("room/<str:code>/invite/", views.multiplayer_invite, name="multiplayer_invite"),
    path("room/<str:code>/start/", views.multiplayer_start, name="multiplayer_start"),
    path("api/room/<str:code>/info/", views.api_room_info, name="api_room_info"),

    # APIs do jogo
    path("api/room/<str:code>/state/", views.api_room_state, name="api_room_state"),
    path("api/room/<str:code>/move/", views.api_room_move, name="api_room_move"),

    # Amigos
    path("friends/", views.friends_page, name="friends_page"),
    path("friends/add/", views.friend_add, name="friend_add"),
    path("friends/accept/<int:pk>/", views.friend_accept, name="friend_accept"),
]
