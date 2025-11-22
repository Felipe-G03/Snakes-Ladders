from django.urls import path
from . import views

app_name = 'game'

urlpatterns = [
    path("", views.tela_inicial, name="tela_inicial"),
    path("instrucoes/", views.tela_instrucoes, name="tela_instrucoes"),

    # fluxo do jogo
    path("jogar/contra-maquina/", views.iniciar_contra_maquina, name="iniciar_contra_maquina"),
    path("jogo/novo/", views.novo_jogo, name="novo_jogo"),
    path("jogo/", views.tela_tabuleiro, name="tela_tabuleiro"),
    path("jogo/jogar/", views.jogar_rodada, name="jogar_rodada"),
    path("jogo/reiniciar/", views.reiniciar_jogo, name="reiniciar_jogo"),

    # login/perfil
    path("register/", views.register, name="register"),
    path("profile/", views.profile, name="profile"),

    # modo multiplayer
    path("multiplayer/", views.multiplayer_lobby, name="multiplayer_lobby"),
    path("multiplayer/create/", views.multiplayer_create, name="multiplayer_create"),
    path("multiplayer/join/", views.multiplayer_join, name="multiplayer_join"),
    path("multiplayer/room/<str:code>/", views.multiplayer_room, name="multiplayer_room"),

    # APIs para o JS
    path("api/room/<str:code>/state/", views.api_room_state, name="api_room_state"),
    path("api/room/<str:code>/move/", views.api_room_move, name="api_room_move"),

]