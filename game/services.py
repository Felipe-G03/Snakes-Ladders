# game/services.py
import random
import math
from typing import Dict, Tuple, Set, Optional


def rolar_dado() -> int:
    """Retorna um valor inteiro entre 1 e 6."""
    return random.randint(1, 6)


# ---------------------------
# NOVO GERADOR (sem overlaps)
# ---------------------------
def gerar_cobras_escadas_sem_overlaps(
    casa_final: int,
    qtd_cobras: Optional[int] = None,
    qtd_escadas: Optional[int] = None,
    seed: Optional[int] = None,
) -> Tuple[Dict[int, int], Dict[int, int]]:
    """
    Gera dicionários (cobras, escadas) respeitando:
      - NÃO há mais de um item na mesma casa (nem cobra+escada, nem múltiplas do mesmo tipo),
      - não usa casas 0 e casa_final,
      - escada: base < topo,
      - cobra: cabeça > cauda.

    Estratégia:
      - Mantém um set 'ocupadas' com TODAS as casas já usadas (start ou end) para
        impedir sobreposição visual/funcional.
      - Tenta sortear pares válidos até preencher as quantidades desejadas.

    Retorna (cobras, escadas) como dict[int->int].
    """
    assert casa_final >= 10, "Tabuleiro muito pequeno para geração automática."

    rnd = random.Random(seed) if seed is not None else random

    # Densidade padrão (compatível com a sua lógica anterior)
    # sqrt(100)=10 -> ~10 de cada seria exagerado, então reduzimos um pouco.
    densidade = int(max(2, math.sqrt(casa_final) * 0.6))
    if casa_final <= 25:
        densidade = max(densidade, 3)  # pelo menos 3 em tabuleiros 5x5

    if qtd_cobras is None:
        qtd_cobras = densidade
    if qtd_escadas is None:
        qtd_escadas = densidade

    # Distância mínima entre início e fim (5% do tabuleiro, no mínimo 2)
    min_dist = max(2, int(casa_final * 0.05))

    cobras: Dict[int, int] = {}
    escadas: Dict[int, int] = {}
    ocupadas: Set[int] = set()  # qualquer casa já usada (start/end)

    def sorteia_escada() -> Tuple[int, int]:
        """Sorteia (base, topo) válidos para escada."""
        for _ in range(1000):
            base = rnd.randint(1, casa_final - 1 - min_dist)
            topo = rnd.randint(base + min_dist, casa_final - 1)

            if base in ocupadas or topo in ocupadas:
                continue
            if base == topo:
                continue
            return base, topo
        raise RuntimeError("Não foi possível gerar escada sem sobreposição.")

    def sorteia_cobra() -> Tuple[int, int]:
        """Sorteia (cabeca, cauda) válidos para cobra."""
        for _ in range(1000):
            cabeca = rnd.randint(1 + min_dist, casa_final - 1)
            cauda = rnd.randint(1, cabeca - min_dist)

            if cabeca in ocupadas or cauda in ocupadas:
                continue
            if cabeca == cauda:
                continue
            return cabeca, cauda
        raise RuntimeError("Não foi possível gerar cobra sem sobreposição.")

    # Gerar escadas primeiro (opcional, estética)
    tentativas = 0
    while len(escadas) < qtd_escadas and tentativas < 5000:
        tentativas += 1
        try:
            base, topo = sorteia_escada()
        except RuntimeError:
            break
        escadas[base] = topo
        ocupadas.add(base)
        ocupadas.add(topo)

    # Gerar cobras
    tentativas = 0
    while len(cobras) < qtd_cobras and tentativas < 5000:
        tentativas += 1
        try:
            cabeca, cauda = sorteia_cobra()
        except RuntimeError:
            break
        cobras[cabeca] = cauda
        ocupadas.add(cabeca)
        ocupadas.add(cauda)

    return cobras, escadas


# Mantemos o nome original, mas agora garante unicidade via função acima.
def mapa_cobras_escadas(casa_final: int) -> Tuple[Dict[int, int], Dict[int, int]]:
    """
    Wrapper para manter compatibilidade com o resto do código.
    Agora usa o gerador que evita sobreposição.
    """
    return gerar_cobras_escadas_sem_overlaps(casa_final)


def aplicar_cobras_escadas(posicao: int, cobras: Dict[int, int], escadas: Dict[int, int]) -> int:
    """Se cair em escada, sobe; se cair em cobra, desce; caso contrário, permanece."""
    if posicao in escadas:
        return escadas[posicao]
    if posicao in cobras:
        return cobras[posicao]
    return posicao


def mover_peao(pos_atual: int, dado: int, casa_final: int, cobras: dict, escadas: dict) -> int:
    """
    Aplica o movimento para frente (sem rebote aqui) e depois cobra/escada.
    Observação: a lógica de "bounce back" quando passa do fim
    é tratada nas views. Aqui, se estourar o fim, mantém a posição.
    """
    # normaliza chaves (caso venham como strings)
    try:
        cobras = {int(k): int(v) for k, v in cobras.items()}
        escadas = {int(k): int(v) for k, v in escadas.items()}
    except Exception:
        pass

    destino = pos_atual + dado
    if destino > casa_final:
        # esta função assume "final exato"; o rebote é tratado fora
        return pos_atual

    if destino in escadas:
        return escadas[destino]
    if destino in cobras:
        return cobras[destino]
    return destino
