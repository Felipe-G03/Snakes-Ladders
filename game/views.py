# game/views.py
import json
import random
import string

from django.utils.safestring import mark_safe
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden

from .services import rolar_dado, mapa_cobras_escadas, mover_peao
from .forms import RegisterForm
from .models import GameRoom, GamePlayer


# ---------- Função para a criação do tabuleiro ----------
def _celulas_serpentina(linhas: int, colunas: int):
    """
    Retorna uma lista com os números das casas (1..N) na ordem que o tabuleiro
    deve ser renderizado em grade, usando o padrão “serpentina”:
    - contamos as linhas de baixo (0) para cima (linhas-1)
    - linhas pares (a partir de baixo) vão da esquerda para a direita
    - linhas ímpares vão da direita para a esquerda
    """
    resultado = []
    for visual_row in range(linhas):
        row_from_bottom = linhas - 1 - visual_row  # 0 = linha de baixo
        even = (row_from_bottom % 2 == 0)
        for col in range(colunas):
            n = (row_from_bottom * colunas + (col + 1)) if even \
                else (row_from_bottom * colunas + (colunas - col))
            resultado.append(n)
    return resultado


# --------- Tela Inicial / Instruções ---------
def tela_inicial(request):
    return render(request, "game/tela_inicial.html")


def tela_instrucoes(request):
    return render(request, "game/instrucoes.html")


@require_POST
def iniciar_contra_maquina(request):
    tamanho_tabuleiro = request.POST.get("tamanho_tabuleiro", "10x10")
    qtd_maquinas = int(request.POST.get("qtd_maquinas", "1"))

    if tamanho_tabuleiro == "5x5":
        linhas = colunas = 5
        casa_final = 25
    else:
        linhas = colunas = 10
        casa_final = 100

    request.session["configuracao_jogo"] = {
        "modo": "contra_maquina",
        "linhas": linhas,
        "colunas": colunas,
        "casa_final": casa_final,
        "qtd_maquinas": qtd_maquinas,
        "qtd_humanos": 1,
        "qtd_total_jogadores": 1 + qtd_maquinas,
    }
    return redirect("game:novo_jogo")


# --------- Fluxo do jogo (single-player / contra máquina) ---------
def novo_jogo(request):
    config = request.session.get("configuracao_jogo")
    if not config:
        return redirect("game:tela_inicial")

    casa_final = config["casa_final"]
    cobras, escadas = mapa_cobras_escadas(casa_final)
    posicoes = [0] * config["qtd_total_jogadores"]

    request.session["partida"] = {
        "status": "andamento",          # andamento | finalizado
        "jogador_atual": 0,             # 0 = humano; 1..n-1 = máquinas
        "posicoes": posicoes,
        "ultimo_dado": None,
        "mensagem": "Partida iniciada.",
        # --- Regras ---
        "cobras": cobras,
        "escadas": escadas,
        "streak_seis": [0] * len(posicoes),   # contagem de 6 seguidos por jogador
        # --- logs ---
        "log": ["Partida iniciada."],
        "rodada_atual": 1,
        "log_rodadas": [
            [{"jogador": None, "texto": "Partida iniciada."}]
        ],
        # para animação no front
        "ultimo_movimento": None,  # { "jogador":int, "de":int, "para":int, "dado":int, "pre_salto":int|None }
    }
    request.session.modified = True
    return redirect("game:tela_tabuleiro")


def tela_tabuleiro(request):
    config = request.session.get("configuracao_jogo")
    partida = request.session.get("partida")
    if not config or not partida:
        return redirect("game:tela_inicial")

    celulas = _celulas_serpentina(config["linhas"], config["colunas"])

    # JSON válidos para o template
    json_posicoes = mark_safe(json.dumps(partida.get("posicoes", [])))
    json_cobras = mark_safe(json.dumps(partida.get("cobras", {})))
    json_escadas = mark_safe(json.dumps(partida.get("escadas", {})))
    json_ultimo_mov = mark_safe(json.dumps(partida.get("ultimo_movimento", None)))
    json_status = mark_safe(json.dumps(partida.get("status", "andamento")))
    json_jogador_atual = mark_safe(json.dumps(partida.get("jogador_atual", 0)))
    json_casa_final = mark_safe(json.dumps(config.get("casa_final", 100)))

    contexto = {
        "modo": "single",
        "config": config,
        "partida": partida,
        "celulas": celulas,
        "eh_humano_a_vez": partida["jogador_atual"] == 0 and partida["status"] != "finalizado",
        "json_posicoes": json_posicoes,
        "json_cobras": json_cobras,
        "json_escadas": json_escadas,
        "json_ultimo_mov": json_ultimo_mov,
        "json_status": json_status,
        "json_jogador_atual": json_jogador_atual,
        "json_casa_final": json_casa_final,
        "log_rodadas": partida.get("log_rodadas", []),
        "rodada_atual": partida.get("rodada_atual", 1),
    }
    return render(request, "game/tabuleiro.html", contexto)


@require_POST
def jogar_rodada(request):
    config = request.session.get("configuracao_jogo")
    partida = request.session.get("partida")
    if not config or not partida or partida.get("status") == "finalizado":
        return redirect("game:tela_inicial")

    casa_final = config["casa_final"]
    i = partida["jogador_atual"]
    dado = rolar_dado()

    posicoes = partida["posicoes"]
    pos_atual = posicoes[i]
    # normaliza chaves vindas da sessão (JSON -> str) para int
    cobras = {int(k): int(v) for k, v in partida.get("cobras", {}).items()}
    escadas = {int(k): int(v) for k, v in partida.get("escadas", {}).items()}

    # ----- controle de 6 seguidos -----
    streak = partida.setdefault("streak_seis", [0] * len(posicoes))
    if len(streak) != len(posicoes):
        # robustez: garante comprimento correto se configuração mudar
        novo = [0] * len(posicoes)
        for idx in range(min(len(streak), len(novo))):
            novo[idx] = streak[idx]
        partida["streak_seis"] = streak = novo

    if dado == 6:
        streak[i] += 1
    else:
        streak[i] = 0

    # penalidade ao tirar 6 três vezes seguidas
    if streak[i] >= 3:
        streak[i] = 0  # zera após a punição
        pre_salto = None
        posicoes[i] = 0  # volta ao início
        destino_final = 0

        mensagem = f"Jogador {i+1} tirou 6 três vezes seguidas e foi penalizado: volta ao início."
        partida["posicoes"] = posicoes
        partida["ultimo_dado"] = dado
        partida["mensagem"] = mensagem
        partida.setdefault("log", []).append(mensagem)
        partida.setdefault("log_rodadas", [[]])
        if not partida["log_rodadas"]:
            partida["log_rodadas"] = [[]]
        partida["log_rodadas"][-1].append({"jogador": i, "texto": mensagem})

        partida["ultimo_movimento"] = {
            "jogador": i, "de": pos_atual, "para": destino_final,
            "dado": dado, "pre_salto": pre_salto,
        }

        # passa a vez normalmente após a penalidade
        proximo = (i + 1) % len(posicoes)
        partida["jogador_atual"] = proximo
        if proximo == 0:
            partida["rodada_atual"] = partida.get("rodada_atual", 1) + 1
            partida["log_rodadas"].append([])

        request.session["partida"] = partida
        request.session.modified = True
        return redirect("game:tela_tabuleiro")

    # ----- movimento com 'bounce back' (rebote) + final exato -----
    destino_bruto = pos_atual + dado

    if destino_bruto == casa_final:
        # cravou exatamente a última casa: vence (sem cobra/escada)
        pre_salto = destino_bruto
        destino_final = destino_bruto

    elif destino_bruto < casa_final:
        # movimento normal: anda e depois aplica cobra/escada via serviço existente
        pre_salto = destino_bruto
        destino_final = mover_peao(
            pos_atual, dado, casa_final, cobras, escadas
        )

    else:
        # passou do fim -> rebate
        over = destino_bruto - casa_final
        bounced = casa_final - over
        pre_salto = bounced
        destino_final = bounced

        # aplicar cobra/escada MANUALMENTE na casa rebatida (evita erros após o rebote)
        if destino_final in escadas:
            destino_final = escadas[destino_final]
        elif destino_final in cobras:
            destino_final = cobras[destino_final]

    # ----- mensagem cobra/escada (cálculo único de tipo_extra) -----
    tipo_extra = ""
    if pre_salto is not None and destino_final != pre_salto:
        tipo_extra = " (subiu por escada)" if destino_final > pre_salto else " (desceu por cobra)"

    mensagem = f"Jogador {i+1} rolou {dado} e foi da casa {pos_atual} para {destino_final}{tipo_extra}."
    if destino_final == casa_final:
        partida["status"] = "finalizado"
        mensagem += f" Jogador {i+1} venceu!"

    posicoes[i] = destino_final
    partida["posicoes"] = posicoes
    partida["ultimo_dado"] = dado
    partida["mensagem"] = mensagem
    partida.setdefault("log", []).append(mensagem)
    partida.setdefault("log_rodadas", [[]])
    if not partida["log_rodadas"]:
        partida["log_rodadas"] = [[]]
    partida["log_rodadas"][-1].append({"jogador": i, "texto": mensagem})

    partida["ultimo_movimento"] = {
        "jogador": i, "de": pos_atual, "para": destino_final,
        "dado": dado, "pre_salto": pre_salto,
    }

    # ----- alternância de vez + regra do 6 -----
    if partida["status"] != "finalizado":
        if dado == 6:
            # mantém o mesmo jogador
            partida["jogador_atual"] = i
            partida["mensagem"] += " Tirou 6 e joga novamente!"
        else:
            proximo = (i + 1) % len(posicoes)
            partida["jogador_atual"] = proximo
            # fecha rodada se voltou ao jogador 0
            if proximo == 0:
                partida["rodada_atual"] = partida.get("rodada_atual", 1) + 1
                partida["log_rodadas"].append([])

    request.session["partida"] = partida
    request.session.modified = True
    return redirect("game:tela_tabuleiro")


def reiniciar_jogo(request):
    if "partida" in request.session:
        del request.session["partida"]
    return redirect("game:novo_jogo")


# ------------- Registro e Login --------------
def register(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)  # loga automaticamente após o cadastro
            return redirect("game:tela_inicial")
    else:
        form = RegisterForm()
    return render(request, "game/register.html", {"form": form})


@login_required
def profile(request):
    return render(request, "game/profile.html", {})


# ------------- Multiplayer -------------
def _generate_code(size=6):
    chars = string.ascii_uppercase + string.digits
    return "".join(random.choice(chars) for _ in range(size))


@login_required
def multiplayer_lobby(request):
    return render(request, "game/multiplayer_lobby.html")


@login_required
def multiplayer_create(request):
    if request.method == "POST":
        code = _generate_code()
        room = GameRoom.objects.create(
            code=code,
            host=request.user,
            board_size="10x10",
            current_turn=request.user,
            # inicia log com “Sala criada…”
            log_rounds=[[{"username": None, "texto": f"Sala criada por {request.user.username}."}]],
            round_number=1,
        )

        # mapa único da sala
        casa_final = 25 if room.board_size == "5x5" else 100
        from .services import gerar_cobras_escadas_sem_overlaps
        cobras, escadas = gerar_cobras_escadas_sem_overlaps(casa_final, qtd_cobras=5, qtd_escadas=5)
        room.snakes_map = {str(k): int(v) for k, v in cobras.items()}
        room.ladders_map = {str(k): int(v) for k, v in escadas.items()}
        room.save()

        GamePlayer.objects.create(room=room, user=request.user, order=0)
        return redirect("game:multiplayer_room", code=code)
    return HttpResponseForbidden("Método inválido")


@login_required
def multiplayer_join(request):
    if request.method == "POST":
        code = request.POST.get("code", "").upper()
        room = get_object_or_404(GameRoom, code=code, is_active=True)
        if not room.players.filter(user=request.user).exists():
            order = room.players.count()
            GamePlayer.objects.create(room=room, user=request.user, order=order)
        return redirect("game:multiplayer_room", code=code)
    return HttpResponseForbidden("Método inválido")


@login_required
def multiplayer_room(request, code):
    room = get_object_or_404(GameRoom, code=code, is_active=True)

    # Tamanho do tabuleiro (pode parametrizar depois)
    linhas = colunas = 10
    casa_final = 100

    celulas = _celulas_serpentina(linhas, colunas)

    # Mapas salvos (usados por todos os jogadores)
    cobras = {int(k): int(v) for k, v in (room.snakes_map or {}).items()}
    escadas = {int(k): int(v) for k, v in (room.ladders_map or {}).items()}

    # Posições iniciais puxadas do banco
    players_qs = room.players.select_related("user").order_by("order")
    players = list(players_qs)
    posicoes = [p.position for p in players]

    # Índice do jogador da vez (para preencher json_jogador_atual)
    try:
        idx_turno = next(i for i, p in enumerate(players) if p.user_id == room.current_turn_id)
    except StopIteration:
        idx_turno = 0

    contexto = {
        "modo": "multi",
        "room": room,
        "config": {"linhas": linhas, "colunas": colunas, "casa_final": casa_final},
        "celulas": celulas,

        # estes JSON agora têm dados reais; o tabuleiro.js consegue desenhar tudo
        "json_posicoes": mark_safe(json.dumps(posicoes)),
        "json_cobras":   mark_safe(json.dumps(cobras)),
        "json_escadas":  mark_safe(json.dumps(escadas)),
        "json_ultimo_mov": mark_safe(json.dumps(None)),
        "json_status":      mark_safe(json.dumps("andamento")),
        "json_jogador_atual": mark_safe(json.dumps(idx_turno)),
        "json_casa_final":   mark_safe(json.dumps(casa_final)),

        # o log do single não é usado no multi (fica vazio)
        "log_rodadas": [],
        "rodada_atual": 1,
    }
    return render(request, "game/tabuleiro.html", contexto)


# ---------------- APIs ----------------
@login_required
def api_room_state(request, code):
    room = get_object_or_404(GameRoom, code=code, is_active=True)
    players = room.players.select_related("user").order_by("order")
    data = {
        "room_code": room.code,
        "current_turn": room.current_turn.username if room.current_turn else None,
        "players": [
            {"username": p.user.username, "position": p.position, "order": p.order}
            for p in players
        ],
        "you": request.user.username,
        "is_active": room.is_active,

        # log multiplayer
        "log_rounds": room.log_rounds or [],
        "round_number": room.round_number,
    }
    return JsonResponse(data)


@login_required
def api_room_move(request, code):
    if request.method != "POST":
        return HttpResponseForbidden("Método inválido")

    room = get_object_or_404(GameRoom, code=code, is_active=True)

    if not room.is_active:
        return JsonResponse({"ok": False, "error": "Partida já finalizada."}, status=400)

    if room.current_turn != request.user:
        return HttpResponseForbidden("Não é seu turno!")

    player = room.players.get(user=request.user)

    # --- configuração do tabuleiro ---
    casa_final = 25 if room.board_size == "5x5" else 100
    cobras = {int(k): int(v) for k, v in (room.snakes_map or {}).items()}
    escadas = {int(k): int(v) for k, v in (room.ladders_map or {}).items()}

    pos_atual = player.position
    dado = rolar_dado()

    # ----- movimento com 'bounce back' + final exato -----
    destino_bruto = pos_atual + dado
    if destino_bruto == casa_final:
        pre_salto = destino_bruto
        destino_final = destino_bruto
    elif destino_bruto < casa_final:
        pre_salto = destino_bruto
        destino_final = mover_peao(pos_atual, dado, casa_final, cobras, escadas)
    else:
        over = destino_bruto - casa_final
        bounced = casa_final - over
        pre_salto = bounced
        destino_final = bounced
        if destino_final in escadas:
            destino_final = escadas[destino_final]
        elif destino_final in cobras:
            destino_final = cobras[destino_final]

    # atualiza posição do jogador
    player.position = destino_final
    player.save()

    # ---- escrever no log ----
    log_rounds = room.log_rounds or []
    if not log_rounds:
        log_rounds = [[{"username": None, "texto": "Partida iniciada."}]]

    tipo_extra = ""
    if pre_salto is not None and destino_final != pre_salto:
        tipo_extra = " (subiu por escada)" if destino_final > pre_salto else " (desceu por cobra)"

    texto = f"{request.user.username} rolou {dado} e foi da casa {pos_atual} para {destino_final}{tipo_extra}."
    # adiciona ao final da rodada atual
    log_rounds[-1].append({"username": request.user.username, "texto": texto})

    # verifica vitória
    winner = None
    finished = False
    if destino_final == casa_final:
        finished = True
        winner = request.user.username
        room.is_active = False
        log_rounds[-1].append({"username": None, "texto": f"{winner} venceu!"})

    # alternância de turno + regra do 6
    next_turn_username = None
    if not finished:
        players = list(room.players.select_related("user").order_by("order"))
        current_index = [i for i, p in enumerate(players) if p.user == request.user][0]

        if dado == 6:
            next_player = player  # mesma pessoa joga de novo
        else:
            next_player = players[(current_index + 1) % len(players)]
            # se virou a rodada (voltou para order=0), abre nova rodada no log
            if next_player.order == 0:
                room.round_number = (room.round_number or 1) + 1
                log_rounds.append([])

        room.current_turn = next_player.user
        next_turn_username = next_player.user.username

    # salva log e estado
    room.log_rounds = log_rounds
    room.save()

    return JsonResponse({
        "ok": True,
        "dice": dado,
        "new_position": destino_final,
        "pre_jump": pre_salto,
        "finished": finished,
        "winner": winner,
        "next_turn": next_turn_username,
    })
