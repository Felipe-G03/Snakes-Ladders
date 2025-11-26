from django.test import SimpleTestCase, TestCase, RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.auth.models import AnonymousUser
from django.urls import reverse
from django.contrib.auth.models import User
from unittest.mock import patch
import json

from .services import mover_peao, rolar_dado, mapa_cobras_escadas
from . import views
from .models import GameRoom, GamePlayer, Profile, FriendRequest


# --------------------------
# Helpers p/ testes de view
# --------------------------
def _add_session_to_request(request):
    """Acopla uma sessão ao request (para RequestFactory)."""
    middleware = SessionMiddleware(lambda r: None)
    middleware.process_request(request)
    request.session.save()
    return request


def _base_config(linhas=10, colunas=10, casa_final=100, total_jogadores=2):
    return {
        "modo": "contra_maquina",
        "linhas": linhas,
        "colunas": colunas,
        "casa_final": casa_final,
        "qtd_maquinas": total_jogadores - 1,
        "qtd_humanos": 1,
        "qtd_total_jogadores": total_jogadores,
    }


def _base_partida(config, posicoes=None, cobras=None, escadas=None):
    if posicoes is None:
        posicoes = [0] * config["qtd_total_jogadores"]
    if cobras is None:
        cobras = {}
    if escadas is None:
        escadas = {}

    return {
        "status": "andamento",
        "jogador_atual": 0,
        "posicoes": posicoes[:],
        "ultimo_dado": None,
        "mensagem": "Partida iniciada.",
        "cobras": cobras,
        "escadas": escadas,
        "streak_seis": [0] * len(posicoes),
        "log": ["Partida iniciada."],
        "rodada_atual": 1,
        "log_rodadas": [[{"jogador": None, "texto": "Partida iniciada."}]],
        "ultimo_movimento": None,
    }


# --------------------------
# Testes de serviço (unit)
# --------------------------
class ServicesRulesTest(SimpleTestCase):
    def test_mover_peao_aplica_escada(self):
        # está na 0 e rola 2 → cai na 2; escada 2→38
        dest = mover_peao(0, 2, 100, {}, {2: 38})
        self.assertEqual(dest, 38)

    def test_mover_peao_aplica_cobra(self):
        # está na 15 e rola 1 → cai na 16; cobra 16→6
        dest = mover_peao(15, 1, 100, {16: 6}, {})
        self.assertEqual(dest, 6)

    def test_mover_peao_sem_efeito(self):
        dest = mover_peao(10, 3, 100, {}, {})
        self.assertEqual(dest, 13)

    def test_rolar_dado_fica_entre_1_e_6(self):
        valores = [rolar_dado() for _ in range(100)]
        self.assertTrue(all(1 <= v <= 6 for v in valores))

    def test_mapa_cobras_escadas_sem_overlaps(self):
        cobras, escadas = mapa_cobras_escadas(100)
        # todas as casas envolvidas estão dentro do tabuleiro
        todas = []
        for origem, destino in cobras.items():
            todas.append(origem)
            todas.append(destino)
        for origem, destino in escadas.items():
            todas.append(origem)
            todas.append(destino)

        self.assertTrue(all(1 <= c < 100 for c in todas))

        # nenhuma casa se repete (sem overlaps de início/fim)
        usadas = set()
        for casa in todas:
            self.assertNotIn(casa, usadas)
            usadas.add(casa)


# --------------------------
# Testes de view (regras singleplayer)
# --------------------------
class ViewsRulesTest(TestCase):  # << TestCase (usa DB de teste)
    def setUp(self):
        self.rf = RequestFactory()

    def _post_to_jogar(self, session):
        req = self.rf.post("/game/jogar")
        _add_session_to_request(req)
        for k, v in session.items():
            req.session[k] = v
        req.user = AnonymousUser()
        return req

    @patch("game.views.rolar_dado", side_effect=[4])
    def test_bounce_back_rebate_e_aplica_cobra_ou_escada(self, _mock_dado):
        """
        Na casa 99 com dado=4: 99+4=103 → rebote p/ 97.
        Se existir cobra/escada em 97, deve aplicar.
        """
        config = _base_config(casa_final=100, total_jogadores=2)
        cobras = {97: 50}  # ao rebater em 97, desce p/ 50
        partida = _base_partida(config, posicoes=[99, 0], cobras=cobras, escadas={})

        session = {"configuracao_jogo": config, "partida": partida}
        req = self._post_to_jogar(session)

        resp = views.jogar_rodada(req)  # redirect esperado
        self.assertEqual(resp.status_code, 302)

        p = req.session["partida"]
        self.assertEqual(p["posicoes"][0], 50)  # rebate + cobra aplicada
        self.assertIn("desceu por cobra", p["mensagem"])
        self.assertIsNotNone(p["ultimo_movimento"])
        self.assertEqual(p["ultimo_movimento"]["pre_salto"], 97)

    @patch("game.views.rolar_dado", side_effect=[6])
    def test_turno_extra_ao_tirar_seis(self, _mock_dado):
        """
        Ao rolar 6, o jogador mantém a vez e a mensagem informa que joga novamente.
        """
        config = _base_config(casa_final=100, total_jogadores=2)
        escadas = {2: 38}
        partida = _base_partida(config, posicoes=[0, 0], cobras={}, escadas=escadas)

        session = {"configuracao_jogo": config, "partida": partida}
        req = self._post_to_jogar(session)

        resp = views.jogar_rodada(req)
        self.assertEqual(resp.status_code, 302)

        p = req.session["partida"]
        self.assertEqual(p["jogador_atual"], 0, "Deveria continuar sendo o jogador 0 (turno extra)")
        self.assertIn("joga novamente", p["mensagem"])

    @patch("game.views.rolar_dado", side_effect=[6, 6, 6])
    def test_penalidade_tres_seis_seguidos(self, _mock_dado):
        # - Após 3 seis seguidos, o jogador volta à casa 0 e a vez passa para o próximo.
        config = _base_config(casa_final=100, total_jogadores=2)
        partida = _base_partida(config, posicoes=[0, 0])
        # 1º 6
        req1 = self._post_to_jogar({"configuracao_jogo": config, "partida": partida})
        views.jogar_rodada(req1)
        p1 = req1.session["partida"]
        self.assertEqual(p1["jogador_atual"], 0)  # turno extra
        # 2º 6 (ainda jogador 0)
        req2 = self._post_to_jogar({"configuracao_jogo": config, "partida": p1})
        views.jogar_rodada(req2)
        p2 = req2.session["partida"]
        self.assertEqual(p2["jogador_atual"], 0)  # ainda turno extra
        # 3º 6 -> penalidade aplica e passa a vez
        req3 = self._post_to_jogar({"configuracao_jogo": config, "partida": p2})
        views.jogar_rodada(req3)
        p3 = req3.session["partida"]
        self.assertEqual(p3["posicoes"][0], 0, "Penalidade deveria resetar para a casa 0")
        self.assertEqual(p3["jogador_atual"], 1, "Após penalidade, deveria passar a vez")
        self.assertIn("foi penalizado", p3["mensagem"])

    @patch("game.views.rolar_dado", side_effect=[6])
    def test_vitoria_no_acerto_exato(self, _mock_dado):
        """
        Se destino_bruto == casa_final: vence (sem aplicar cobra/escada).
        """
        config = _base_config(casa_final=100, total_jogadores=2)
        # posicao 94 + dado 6 = 100
        partida = _base_partida(config, posicoes=[94, 0], cobras={100: 50}, escadas={100: 101})

        req = self._post_to_jogar({"configuracao_jogo": config, "partida": partida})
        views.jogar_rodada(req)
        p = req.session["partida"]

        self.assertEqual(p["posicoes"][0], 100)
        self.assertEqual(p["status"], "finalizado")
        self.assertIn("venceu", p["mensagem"].lower())
        # confirma que não “teleportou” na casa final
        self.assertIsNotNone(p["ultimo_movimento"])
        self.assertEqual(p["ultimo_movimento"]["pre_salto"], 100)

    @patch("game.views.rolar_dado", side_effect=[2])
    def test_movimento_normal_aplica_escada(self, _mock_dado):
        """
        Sem overshoot: move para pre_salto e depois aplica escada via mover_peao.
        """
        config = _base_config(casa_final=100, total_jogadores=2)
        escadas = {2: 38}
        partida = _base_partida(config, posicoes=[0, 0], cobras={}, escadas=escadas)

        req = self._post_to_jogar({"configuracao_jogo": config, "partida": partida})
        views.jogar_rodada(req)
        p = req.session["partida"]

        self.assertEqual(p["posicoes"][0], 38)
        self.assertEqual(p["ultimo_movimento"]["pre_salto"], 2)
        self.assertIn("subiu por escada", p["mensagem"])

    @patch("game.views.rolar_dado", side_effect=[3])
    def test_movimento_normal_aplica_cobra(self, _mock_dado):
        """
        Sem overshoot: move para pre_salto e depois aplica cobra via mover_peao.
        """
        config = _base_config(casa_final=100, total_jogadores=2)
        cobras = {3: 1}
        partida = _base_partida(config, posicoes=[0, 0], cobras=cobras, escadas={})

        req = self._post_to_jogar({"configuracao_jogo": config, "partida": partida})
        views.jogar_rodada(req)
        p = req.session["partida"]

        self.assertEqual(p["posicoes"][0], 1)
        self.assertEqual(p["ultimo_movimento"]["pre_salto"], 3)
        self.assertIn("desceu por cobra", p["mensagem"])


# --------------------------
# Testes de páginas básicas
# --------------------------
class BasicPagesTest(TestCase):
    def test_tela_inicial_responde_ok(self):
        resp = self.client.get(reverse("game:tela_inicial"))
        self.assertEqual(resp.status_code, 200)

    def test_tela_instrucoes_responde_ok(self):
        resp = self.client.get(reverse("game:tela_instrucoes"))
        self.assertEqual(resp.status_code, 200)


# --------------------------
# Fluxo singleplayer inteiro
# --------------------------
class SingleplayerFlowTest(TestCase):
    def test_iniciar_contra_maquina_cria_configuracao(self):
        data = {
            "tamanho_tabuleiro": "10x10",
            "qtd_maquinas": "2",
        }
        resp = self.client.post(reverse("game:iniciar_contra_maquina"), data)
        # redireciona para novo_jogo
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp["Location"].endswith(reverse("game:novo_jogo")), True)

        session = self.client.session
        config = session.get("configuracao_jogo")
        self.assertIsNotNone(config)
        self.assertEqual(config["casa_final"], 100)
        self.assertEqual(config["qtd_maquinas"], 2)
        self.assertEqual(config["qtd_total_jogadores"], 3)

    def test_novo_jogo_inicializa_partida_na_sessao(self):
        # primeiro precisa ter uma configuração ativa
        session = self.client.session
        config = _base_config()
        session["configuracao_jogo"] = config
        session.save()

        resp = self.client.get(reverse("game:novo_jogo"))
        # deve redirecionar para o tabuleiro
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp["Location"].endswith(reverse("game:tela_tabuleiro")), True)

        partida = self.client.session.get("partida")
        self.assertIsNotNone(partida)
        self.assertEqual(partida["status"], "andamento")
        self.assertEqual(len(partida["posicoes"]), config["qtd_total_jogadores"])


# --------------------------
# Cadastro / autenticação
# --------------------------
class RegisterViewTest(TestCase):
    def test_register_cria_usuario_e_profile(self):
        data = {
            "username": "jogador1",
            "email": "jogador1@example.com",
            "nickname": "Jogador 1",
            "password1": "SenhaForte123!",
            "password2": "SenhaForte123!",
        }
        resp = self.client.post(reverse("game:register"), data)
        # cadastro bem-sucedido redireciona para a tela inicial
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp["Location"].endswith(reverse("game:tela_inicial")), True)

        user = User.objects.get(username="jogador1")
        profile = Profile.objects.get(user=user)
        self.assertEqual(profile.nickname, "Jogador 1")


# --------------------------
# Multiplayer: criação e join
# --------------------------
class MultiplayerViewsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="host", password="abc12345")

    def test_multiplayer_create_cria_sala_e_jogador(self):
        self.client.login(username="host", password="abc12345")
        resp = self.client.post(reverse("game:multiplayer_create"))
        self.assertEqual(resp.status_code, 302)

        room = GameRoom.objects.get(host=self.user)
        self.assertEqual(room.status, "lobby")
        self.assertEqual(room.players.count(), 1)
        player = room.players.first()
        self.assertEqual(player.user, self.user)
        self.assertEqual(player.order, 0)

        # API básica de info da sala
        info_resp = self.client.get(reverse("game:api_room_info", args=[room.code]))
        self.assertEqual(info_resp.status_code, 200)
        payload = json.loads(info_resp.content.decode())
        self.assertEqual(payload["code"], room.code)
        self.assertEqual(len(payload["players"]), 1)
        self.assertEqual(payload["players"][0]["username"], "host")

    def test_multiplayer_join_adiciona_segundo_jogador(self):
        # cria sala já com host
        self.client.login(username="host", password="abc12345")
        room = GameRoom.objects.create(
            code="ABCD1234",
            host=self.user,
            status="lobby",
            is_active=True,
            board_size="10x10",
        )
        GamePlayer.objects.create(room=room, user=self.user, order=0)
        self.client.logout()

        # segundo usuário entra
        user2 = User.objects.create_user(username="guest", password="xyz98765")
        self.client.login(username="guest", password="xyz98765")
        resp = self.client.post(reverse("game:multiplayer_join"), {"code": room.code})
        self.assertEqual(resp.status_code, 302)

        room.refresh_from_db()
        self.assertEqual(room.players.count(), 2)
        usernames = sorted(p.user.username for p in room.players.all())
        self.assertEqual(usernames, ["guest", "host"])


# --------------------------
# Multiplayer: jogada via API
# --------------------------
class MultiplayerApiMoveTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="host", password="abc12345")
        self.client.login(username="host", password="abc12345")
        self.room = GameRoom.objects.create(
            code="ROOM123",
            host=self.user,
            status="active",
            is_active=True,
            board_size="10x10",
            snakes_map={},
            ladders_map={},
            current_turn=self.user,
        )
        self.player = GamePlayer.objects.create(
            room=self.room,
            user=self.user,
            order=0,
            position=0,
        )

    @patch("game.views.rolar_dado", return_value=3)
    def test_api_room_move_atualiza_posicao(self, _mock_dado):
        url = reverse("game:api_room_move", args=[self.room.code])
        resp = self.client.post(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(resp.status_code, 200)

        payload = json.loads(resp.content.decode())
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["dice"], 3)
        self.assertEqual(payload["new_position"], 3)

        self.player.refresh_from_db()
        self.assertEqual(self.player.position, 3)


# --------------------------
# Amigos
# --------------------------
class FriendsFlowTest(TestCase):
    def setUp(self):
        self.u1 = User.objects.create_user(username="alice", password="pw123456")
        self.u2 = User.objects.create_user(username="bob", password="pw123456")

    def test_friend_add_e_accept(self):
        # alice envia pedido para bob
        self.client.login(username="alice", password="pw123456")
        resp = self.client.post(reverse("game:friend_add"), {"username": "bob"})
        self.assertEqual(resp.status_code, 302)

        fr = FriendRequest.objects.get(requester=self.u1, addressee=self.u2)
        self.assertEqual(fr.status, "pending")

        # bob aceita
        self.client.logout()
        self.client.login(username="bob", password="pw123456")
        resp2 = self.client.get(reverse("game:friend_accept", args=[fr.pk]))
        self.assertEqual(resp2.status_code, 302)

        fr.refresh_from_db()
        self.assertEqual(fr.status, "accepted")
