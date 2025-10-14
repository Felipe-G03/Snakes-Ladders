# game/services.py
import random
from typing import Dict, Tuple

def rolar_dado() -> int:
    """Retorna um valor inteiro entre 1 e 6."""
    return random.randint(1, 6)

def mapa_cobras_escadas(casa_final: int) -> Tuple[Dict[int, int], Dict[int, int]]:
    """
    Retorna dicionários (cobras, escadas) para o tamanho do tabuleiro.
    Para 100 casas (10x10) usa um conjunto clássico.
    Para 25 casas (5x5) usa um conjunto reduzido.
    """
    if casa_final == 25:
        # 5x5 (exemplo simples e equilibrado)
        cobras = {
            23: 8,   # quase no fim → volta bem
            19: 7,
            17: 4,
        }
        escadas = {
            2: 14,
            5: 12,
            9: 21,
        }
    else:
        # 10x10 (conjunto clássico)
        cobras = {
            16: 6, 47: 26, 49: 11, 56: 53,
            62: 19, 64: 60, 87: 24, 93: 73, 95: 75, 98: 78
        }
        escadas = {
            1: 38, 4: 14, 9: 31, 21: 42, 28: 84,
            36: 44, 51: 67, 71: 91, 80: 100
        }
    return cobras, escadas

def aplicar_cobras_escadas(posicao: int, cobras: Dict[int, int], escadas: Dict[int, int]) -> int:
    """Se cair em escada, sobe; se cair em cobra, desce; caso contrário, permanece."""
    if posicao in escadas:
        return escadas[posicao]
    if posicao in cobras:
        return cobras[posicao]
    return posicao

def mover_peao(pos_atual: int, dado: int, casa_final: int, cobras: dict, escadas: dict) -> int:
    # normaliza chaves (caso venham como strings)
    try:
        cobras  = {int(k): int(v) for k, v in cobras.items()}
        escadas = {int(k): int(v) for k, v in escadas.items()}
    except Exception:
        # se algo vier muito fora do esperado, não quebra o jogo
        pass

    destino = pos_atual + dado
    if destino > casa_final:
        # esta função pode assumir “final exato” (views tratam bounce)
        return pos_atual

    # aplica escada antes de cobra (ou vice-versa, conforme regra)
    if destino in escadas:
        return escadas[destino]
    if destino in cobras:
        return cobras[destino]
    return destino
