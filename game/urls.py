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
    
    # Páginas de login/perfil
    path("register/", views.register, name="register"),
    path("profile/", views.profile, name="profile"),
]