# game/views.py
import json
from django.utils.safestring import mark_safe
from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST
from .services import rolar_dado, mapa_cobras_escadas, mover_peao

# ---------- FUNÇÃO AUXILIAR: ordem “serpentina” para o grid ----------
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

# --------- Fluxo do jogo ---------
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
    "cobras": cobras,
    "escadas": escadas,

    # --- logs ---
    "log": ["Partida iniciada."],       # mantém o legado (se quiser continuar exibindo em algum lugar)
    "rodada_atual": 1,                  # NOVO
    "log_rodadas": [                    # NOVO: lista de rodadas; cada rodada = lista de eventos
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
    json_posicoes      = mark_safe(json.dumps(partida.get("posicoes", [])))
    json_cobras        = mark_safe(json.dumps(partida.get("cobras", {})))
    json_escadas       = mark_safe(json.dumps(partida.get("escadas", {})))
    json_ultimo_mov    = mark_safe(json.dumps(partida.get("ultimo_movimento", None)))
    json_status        = mark_safe(json.dumps(partida.get("status", "andamento")))
    json_jogador_atual = mark_safe(json.dumps(partida.get("jogador_atual", 0)))
    json_casa_final    = mark_safe(json.dumps(config.get("casa_final", 100)))

    contexto = {
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

    destino_bruto = pos_atual + dado
    if destino_bruto > casa_final:
        destino_bruto = pos_atual  # regra: não passa da casa final

    destino_final = mover_peao(pos_atual, dado, casa_final, partida["cobras"], partida["escadas"])

    pre_salto = None
    if destino_final != destino_bruto:
        pre_salto = destino_bruto

    posicoes[i] = destino_final

    tipo_extra = ""
    if pre_salto is not None:
        if destino_final > pre_salto:
            tipo_extra = " (subiu por escada)"
        else:
            tipo_extra = " (desceu por cobra)"

    mensagem = f"Jogador {i+1} rolou {dado} e foi da casa {pos_atual} para {destino_final}{tipo_extra}."
    if destino_final == casa_final:
        partida["status"] = "finalizado"
        mensagem += f" Jogador {i+1} venceu!"

    partida["posicoes"] = posicoes
    partida["ultimo_dado"] = dado
    partida["mensagem"] = mensagem

    # Mantém log legado (se ainda utiliza)
    partida.setdefault("log", []).append(mensagem)

    # --- NOVO: log por rodadas (estruturado) ---
    partida.setdefault("log_rodadas", [])
    if not partida["log_rodadas"]:
        partida["log_rodadas"] = [[]]

    # adiciona evento na rodada atual (sempre no "último" subarray)
    partida["log_rodadas"][-1].append({
        "jogador": i,         # índice 0-based
        "texto": mensagem,    # texto completo
    })

    partida["ultimo_movimento"] = {
        "jogador": i,
        "de": pos_atual,
        "para": destino_final,
        "dado": dado,
        "pre_salto": pre_salto,
    }

    # alterna a vez (se não terminou)
    if partida["status"] != "finalizado":
        proximo = (i + 1) % len(posicoes)
        partida["jogador_atual"] = proximo

        # --- verifica se a rodada terminou (por ciclo dos jogadores) ---
        if proximo == 0:
            partida["rodada_atual"] = partida.get("rodada_atual", 1) + 1
            partida["log_rodadas"].append([])  # abre nova rodada

    request.session["partida"] = partida
    request.session.modified = True
    return redirect("game:tela_tabuleiro")

def reiniciar_jogo(request):
    if "partida" in request.session:
        del request.session["partida"]
    return redirect("game:novo_jogo")
