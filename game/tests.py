# game/tests.py
from django.test import SimpleTestCase, TestCase, RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
from unittest.mock import patch

from .services import mover_peao
from . import views


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


# --------------------------
# Testes de view (fluxo real)
# --------------------------
class ViewsRulesTest(TestCase):  # << TestCase (usa DB de teste)
    def setUp(self):
        self.rf = RequestFactory()

    def _post_to_jogar(self, session):
        req = self.rf.post("/game/jogar")
        _add_session_to_request(req)
        for k, v in session.items():
            req.session[k] = v
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
        """
        Após 3 seis seguidos, o jogador volta à casa 0 e a vez passa para o próximo.
        """
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
