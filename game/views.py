# game/views.py
import json
import random
import string

from django.contrib.auth import login, get_user_model
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.safestring import mark_safe
from django.views.decorators.http import require_POST
from django.db.models import Q

from .forms import RegisterForm
from .models import GameRoom, GamePlayer, FriendRequest, RoomInvite, Profile
from .services import rolar_dado, mapa_cobras_escadas, mover_peao, gerar_cobras_escadas_sem_overlaps

User = get_user_model()

# ---------- util ----------
def _generate_code(size=6):
    chars = string.ascii_uppercase + string.digits
    return "".join(random.choice(chars) for _ in range(size))

def _celulas_serpentina(linhas: int, colunas: int):
    resultado = []
    for visual_row in range(linhas):
        row_from_bottom = linhas - 1 - visual_row
        even = (row_from_bottom % 2 == 0)
        for col in range(colunas):
            n = (row_from_bottom * colunas + (col + 1)) if even \
                else (row_from_bottom * colunas + (colunas - col))
            resultado.append(n)
    return resultado

# --------- telas simples ---------
def tela_inicial(request):
    return render(request, "game/tela_inicial.html")

def tela_instrucoes(request):
    return render(request, "game/instrucoes.html")

# --------- singleplayer ---------
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

def novo_jogo(request):
    config = request.session.get("configuracao_jogo")
    if not config:
        return redirect("game:tela_inicial")

    casa_final = config["casa_final"]
    cobras, escadas = mapa_cobras_escadas(casa_final)
    posicoes = [0] * config["qtd_total_jogadores"]

    request.session["partida"] = {
        "status": "andamento",
        "jogador_atual": 0,
        "posicoes": posicoes,
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
    request.session.modified = True
    return redirect("game:tela_tabuleiro")

def tela_tabuleiro(request):
    config = request.session.get("configuracao_jogo")
    partida = request.session.get("partida")
    if not config or not partida:
        return redirect("game:tela_inicial")

    celulas = _celulas_serpentina(config["linhas"], config["colunas"])

    contexto = {
        "modo": "single",
        "config": config,
        "partida": partida,
        "celulas": celulas,
        "eh_humano_a_vez": partida["jogador_atual"] == 0 and partida["status"] != "finalizado",
        "json_posicoes": mark_safe(json.dumps(partida.get("posicoes", []))),
        "json_cobras": mark_safe(json.dumps(partida.get("cobras", {}))),
        "json_escadas": mark_safe(json.dumps(partida.get("escadas", {}))),
        "json_ultimo_mov": mark_safe(json.dumps(partida.get("ultimo_movimento", None))),
        "json_status": mark_safe(json.dumps(partida.get("status", "andamento"))),
        "json_jogador_atual": mark_safe(json.dumps(partida.get("jogador_atual", 0))),
        "json_casa_final": mark_safe(json.dumps(config.get("casa_final", 100))),
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
    cobras = {int(k): int(v) for k, v in partida.get("cobras", {}).items()}
    escadas = {int(k): int(v) for k, v in partida.get("escadas", {}).items()}

    streak = partida.setdefault("streak_seis", [0] * len(posicoes))
    if dado == 6:
        streak[i] += 1
    else:
        streak[i] = 0

    if streak[i] >= 3:
        streak[i] = 0
        pre_salto = None
        posicoes[i] = 0
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
        partida["ultimo_movimento"] = {"jogador": i, "de": pos_atual, "para": destino_final, "dado": dado, "pre_salto": pre_salto}

        proximo = (i + 1) % len(posicoes)
        partida["jogador_atual"] = proximo
        if proximo == 0:
            partida["rodada_atual"] = partida.get("rodada_atual", 1) + 1
            partida["log_rodadas"].append([])

        request.session["partida"] = partida
        request.session.modified = True
        return redirect("game:tela_tabuleiro")

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

    tipo_extra = ""
    if pre_salto is not None and destino_final != pre_salto:
        tipo_extra = " (subiu por escada)" if destino_final > pre_salto else " (desceu por cobra)"

    mensagem = f"Jogador {i+1} rolou {dado} e foi da casa {pos_atual} para {destino_final}{tipo_extra}."
    if destino_final == casa_final:
        partida["status"] = "finalizado"
        mensagem += f" Jogador {i+1} venceu!"
        if request.user.is_authenticated:
            try:
                profile = request.user.profile
            except Profile.DoesNotExist:
                profile = Profile.objects.create(user=request.user, nickname=request.user.username)

            profile.total_games += 1
            if i == 0:
                profile.wins += 1
            else:
                profile.losses += 1
            profile.save()

    posicoes[i] = destino_final
    partida["posicoes"] = posicoes
    partida["ultimo_dado"] = dado
    partida["mensagem"] = mensagem
    partida.setdefault("log", []).append(mensagem)
    partida.setdefault("log_rodadas", [[]])
    if not partida["log_rodadas"]:
        partida["log_rodadas"] = [[]]
    partida["log_rodadas"][-1].append({"jogador": i, "texto": mensagem})

    partida["ultimo_movimento"] = {"jogador": i, "de": pos_atual, "para": destino_final, "dado": dado, "pre_salto": pre_salto}

    if partida["status"] != "finalizado":
        if dado == 6:
            partida["jogador_atual"] = i
            partida["mensagem"] += " Tirou 6 e joga novamente!"
        else:
            proximo = (i + 1) % len(posicoes)
            partida["jogador_atual"] = proximo
            if proximo == 0:
                partida["rodada_atual"] = partida.get("rodada_atual", 1) + 1
                partida["log_rodadas"].append([])

    request.session["partida"] = partida
    request.session.modified = True

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({
            "posicoes": partida["posicoes"],
            "ultimo_movimento": partida.get("ultimo_movimento"),
            "status": partida.get("status", "andamento"),
            "jogador_atual": partida.get("jogador_atual", 0),
            "ultimo_dado": partida.get("ultimo_dado"),
            "mensagem": partida.get("mensagem", ""),
            "rodada_atual": partida.get("rodada_atual", 1),
            "log_rodadas": partida.get("log_rodadas", []),
        })

    return redirect("game:tela_tabuleiro")


def reiniciar_jogo(request):
    if "partida" in request.session:
        del request.session["partida"]
    return redirect("game:novo_jogo")

# --------- registro/perfil ---------
def register(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("game:tela_inicial")
    else:
        form = RegisterForm()
    return render(request, "game/register.html", {"form": form})

@login_required
def profile(request):
    # Estatísticas
    profile = getattr(request.user, "profile", None)
    total = profile.total_games if profile else 0
    wins = profile.wins if profile else 0
    losses = profile.losses if profile else 0
    win_rate = profile.win_rate if profile else 0

    # Amigos / convites (mesma lógica de friends_page)
    incoming = FriendRequest.objects.filter(
        addressee=request.user,
        status="pending"
    ).select_related("requester")

    outgoing = FriendRequest.objects.filter(
        requester=request.user,
        status="pending"
    ).select_related("addressee")

    friends = FriendRequest.objects.filter(
        Q(requester=request.user) | Q(addressee=request.user),
        status="accepted"
    ).select_related("requester", "addressee")

    contexto = {
        "profile_obj": profile,
        "stats": {
            "total": total,
            "wins": wins,
            "losses": losses,
            "win_rate": win_rate,
        },
        "incoming": incoming,
        "outgoing": outgoing,
        "friends": friends,
    }
    return render(request, "game/profile.html", contexto)


# --------- multiplayer: lobby global ---------
@login_required
def multiplayer_lobby(request):
    # lista de salas públicas em lobby
    public_rooms = GameRoom.objects.filter(status="lobby", is_public=True).order_by("-created_at")[:30]
    return render(request, "game/multiplayer_lobby.html", {"public_rooms": public_rooms})

@login_required
def multiplayer_create(request):
    if request.method != "POST":
        return HttpResponseForbidden("Método inválido")
    code = _generate_code()
    room = GameRoom.objects.create(
        code=code,
        host=request.user,
        board_size="10x10",
        status="lobby",
        current_turn=None,  # só define quando iniciar
        log_rounds=[[{"username": None, "order": None, "texto": f"Sala criada por {request.user.username}."}]],
        round_number=1,
    )
    GamePlayer.objects.create(room=room, user=request.user, order=0)
    return redirect("game:multiplayer_room", code=code)

@login_required
def multiplayer_join(request):
    if request.method != "POST":
        return HttpResponseForbidden("Método inválido")
    code = (request.POST.get("code") or "").upper().strip()
    room = get_object_or_404(GameRoom, code=code, status__in=["lobby", "active"], is_active=True)
    if not room.players.filter(user=request.user).exists():
        order = room.players.count()
        GamePlayer.objects.create(room=room, user=request.user, order=order)
    return redirect("game:multiplayer_room", code=code)

@login_required
def multiplayer_room(request, code):
    room = get_object_or_404(GameRoom, code=code, is_active=True)

    # Enquanto em lobby, exibe tela de lobby da sala
    if room.status == "lobby":
        invites = room.invites.select_related("invitee").order_by("-created_at")
        players = room.players.select_related("user").order_by("order")
        return render(request, "game/multiplayer_room_lobby.html", {
            "room": room,
            "invites": invites,
            "players": players,
        })

    # Quando ativa, renderiza o mesmo tabuleiro do single, só que com 'modo=multi'
    linhas = colunas = 10 if room.board_size == "10x10" else 5
    casa_final = 100 if room.board_size == "10x10" else 25
    celulas = _celulas_serpentina(linhas, colunas)

    cobras = {int(k): int(v) for k, v in (room.snakes_map or {}).items()}
    escadas = {int(k): int(v) for k, v in (room.ladders_map or {}).items()}

    players = list(room.players.select_related("user").order_by("order"))
    posicoes = [p.position for p in players]
    try:
        idx_turno = next(i for i, p in enumerate(players) if room.current_turn_id == p.user_id)
    except StopIteration:
        idx_turno = 0

    contexto = {
        "modo": "multi",
        "room": room,
        "config": {"linhas": linhas, "colunas": colunas, "casa_final": casa_final},
        "celulas": celulas,
        "json_posicoes": mark_safe(json.dumps(posicoes)),
        "json_cobras": mark_safe(json.dumps(cobras)),
        "json_escadas": mark_safe(json.dumps(escadas)),
        "json_ultimo_mov": mark_safe(json.dumps(None)),
        "json_status": mark_safe(json.dumps("andamento")),
        "json_jogador_atual": mark_safe(json.dumps(idx_turno)),
        "json_casa_final": mark_safe(json.dumps(casa_final)),
        "log_rodadas": [],  # log é renderizado por JS via API
        "rodada_atual": 1,
    }
    return render(request, "game/tabuleiro.html", contexto)

# ----- configuração & convites -----
@login_required
@require_POST
def multiplayer_config(request, code):
    room = get_object_or_404(GameRoom, code=code, is_active=True)
    if room.host_id != request.user.id:
        return HttpResponseForbidden("Apenas o host pode configurar.")
    room.board_size = request.POST.get("board_size", room.board_size)
    room.is_public = bool(request.POST.get("is_public"))
    room.save()
    return redirect("game:multiplayer_room", code=code)

@login_required
@require_POST
def multiplayer_invite(request, code):
    room = get_object_or_404(GameRoom, code=code, is_active=True)
    if room.host_id != request.user.id:
        return HttpResponseForbidden("Apenas o host pode convidar.")
    username = (request.POST.get("username") or "").strip()
    try:
        invitee = User.objects.get(username=username)
    except User.DoesNotExist:
        raise Http404("Usuário não encontrado.")
    RoomInvite.objects.get_or_create(room=room, inviter=request.user, invitee=invitee)
    return redirect("game:multiplayer_room", code=code)

@login_required
@require_POST
def multiplayer_start(request, code):
    room = get_object_or_404(GameRoom, code=code, is_active=True)
    if room.host_id != request.user.id:
        return HttpResponseForbidden("Apenas o host pode iniciar.")

    if room.status != "lobby":
        return redirect("game:multiplayer_room", code=code)

    casa_final = 100 if room.board_size == "10x10" else 25
    cobras, escadas = gerar_cobras_escadas_sem_overlaps(casa_final, qtd_cobras=5, qtd_escadas=5)
    room.snakes_map = {str(k): int(v) for k, v in cobras.items()}
    room.ladders_map = {str(k): int(v) for k, v in escadas.items()}

    # define o turno inicial como o jogador de ordem 0
    first = room.players.order_by("order").first()
    room.current_turn = first.user if first else request.user
    room.status = "active"
    room.save()
    return redirect("game:multiplayer_room", code=code)

@login_required
def multiplayer_leave(request, code):
    room = get_object_or_404(GameRoom, code=code)

    # Remove o jogador desta sala
    GamePlayer.objects.filter(room=room, user=request.user).delete()

    # Se não sobrou ninguém, pode encerrar ou deletar a sala
    if not room.players.exists():   # se 'players' for related_name
        room.is_active = False
        room.status = "finished"
        room.save()

    return redirect("game:tela_inicial")


@login_required
def api_room_info(request, code):
    room = get_object_or_404(GameRoom, code=code, is_active=True)
    players = [{"username": p.user.username, "order": p.order} for p in room.players.select_related("user").order_by("order")]
    return JsonResponse({"status": room.status, "players": players, "code": room.code, "is_public": room.is_public})

# ----- APIs de estado e jogada (multi em jogo) -----
@login_required
def api_room_state(request, code):
    room = get_object_or_404(GameRoom, code=code, is_active=True)
    players = room.players.select_related("user").order_by("order")
    data = {
        "room_code": room.code,
        "current_turn": room.current_turn.username if room.current_turn else None,
        "players": [{"username": p.user.username, "position": p.position, "order": p.order} for p in players],
        "you": request.user.username,
        "is_active": room.is_active and room.status == "active",
        "log_rounds": room.log_rounds or [],
        "round_number": room.round_number,
    }
    return JsonResponse(data)

@login_required
def api_room_move(request, code):
    if request.method != "POST":
        return HttpResponseForbidden("Método inválido")
    room = get_object_or_404(GameRoom, code=code, is_active=True)
    if room.status != "active":
        return JsonResponse({"ok": False, "error": "A partida não está ativa."}, status=400)
    if room.current_turn != request.user:
        return HttpResponseForbidden("Não é seu turno!")

    player = room.players.get(user=request.user)

    casa_final = 25 if room.board_size == "5x5" else 100
    cobras = {int(k): int(v) for k, v in (room.snakes_map or {}).items()}
    escadas = {int(k): int(v) for k, v in (room.ladders_map or {}).items()}

    pos_atual = player.position
    dado = rolar_dado()

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

    player.position = destino_final
    player.save()

    # log
    log_rounds = room.log_rounds or [[{"username": None, "order": None, "texto": "Partida iniciada."}]]
    tipo_extra = ""
    if pre_salto is not None and destino_final != pre_salto:
        tipo_extra = " (subiu por escada)" if destino_final > pre_salto else " (desceu por cobra)"
    texto = f"{request.user.username} rolou {dado} e foi da casa {pos_atual} para {destino_final}{tipo_extra}."

    # identificamos a ordem do jogador para colorir no front
    order_map = {p.user_id: p.order for p in room.players.all()}
    log_rounds[-1].append({"username": request.user.username, "order": order_map.get(request.user.id, 0), "texto": texto})

    winner = None
    finished = False
    if destino_final == casa_final:
        finished = True
        winner = request.user.username
        room.status = "finished"
        log_rounds[-1].append({"username": None, "order": None, "texto": f"{winner} venceu!"})

        for gp in room.players.select_related("user"):
            user = gp.user
            try:
                profile = user.profile
            except Profile.DoesNotExist:
                profile = Profile.objects.create(user=user, nickname=user.username)

            profile.total_games += 1
            if user.username == winner:
                profile.wins += 1
            else:
                profile.losses += 1
            profile.save()

    next_turn_username = None
    if not finished:
        players = list(room.players.select_related("user").order_by("order"))
        current_index = [i for i, p in enumerate(players) if p.user_id == request.user.id][0]
        if dado == 6:
            next_player = player
        else:
            next_player = players[(current_index + 1) % len(players)]
            if next_player.order == 0:
                room.round_number = (room.round_number or 1) + 1
                log_rounds.append([])
        room.current_turn = next_player.user
        next_turn_username = next_player.user.username

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

# --------- amigos ---------
@login_required
def friends_page(request):
    incoming = FriendRequest.objects.filter(addressee=request.user, status="pending").select_related("requester")
    outgoing = FriendRequest.objects.filter(requester=request.user, status="pending").select_related("addressee")
    friends = FriendRequest.objects.filter(
        models.Q(requester=request.user) | models.Q(addressee=request.user),
        status="accepted"
    ).select_related("requester", "addressee")
    return render(request, "game/friends.html", {
        "incoming": incoming,
        "outgoing": outgoing,
        "friends": friends,
    })

@login_required
@require_POST
def friend_add(request):
    username = (request.POST.get("username") or "").strip()
    if not username:
        return redirect("game:profile")
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        return redirect("game:profile")
    if user.id == request.user.id:
        return redirect("game:profile")
    FriendRequest.objects.get_or_create(
        requester=request.user,
        addressee=user,
        defaults={"status": "pending"},
    )
    return redirect("game:profile")

@login_required
def friend_accept(request, pk):
    fr = get_object_or_404(
        FriendRequest,
        pk=pk,
        addressee=request.user,
        status="pending",
    )
    fr.status = "accepted"
    fr.save()
    return redirect("game:profile")

@login_required
def friend_request_accept(request, pk):
    fr = get_object_or_404(FriendRequest, pk=pk, addressee=request.user, status="pending")
    # cria relação de amizade
    fr.status = "accepted"
    fr.save()
    return redirect("game:profile")

@login_required
def friend_request_reject(request, pk):
    fr = get_object_or_404(FriendRequest, pk=pk, addressee=request.user, status="pending")
    fr.status = "rejected"
    fr.save()
    return redirect("game:profile")

@login_required
def room_invite_accept(request, pk):
    inv = get_object_or_404(RoomInvite, pk=pk, invitee=request.user, status="pending")
    room = inv.room
    # adiciona o usuário como jogador da sala
    GamePlayer.objects.get_or_create(room=room, user=request.user)
    inv.status = "accepted"
    inv.save()
    return redirect("game:multiplayer_room", code=room.code)

@login_required
def room_invite_reject(request, pk):
    inv = get_object_or_404(RoomInvite, pk=pk, invitee=request.user, status="pending")
    inv.status = "rejected"
    inv.save()
    return redirect("game:profile")