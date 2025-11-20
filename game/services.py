# game/services.py
import random
from typing import Dict, Tuple
import math


def rolar_dado() -> int:
    """Retorna um valor inteiro entre 1 e 6."""
    return random.randint(1, 6)

def mapa_cobras_escadas(casa_final: int) -> Tuple[Dict[int, int], Dict[int, int]]:
    """
    Gera dicionários (cobras, escadas) de forma aleatória, justa e proporcional.
    
    Regras de Justiça:
    - Quantidade baseada na raiz quadrada do tabuleiro (ex: 100 casas ~ 10 cobras/10 escadas).
    - Distância mínima de movimento para evitar movimentos insignificantes.
    - Evita loops (cabeça da cobra não pode estar no topo de uma escada).
    """
    
    # 1. Determinar a "densidade" do tabuleiro
    # Para um tabuleiro 10x10 (100), teremos aprox 8-10 itens de cada.
    num_itens = int(math.sqrt(casa_final)) 
    
    # Ajuste fino para tabuleiros muito pequenos
    if casa_final <= 25:
        num_itens = 3  # Garante pelo menos 3 desafios em tabuleiros pequenos

    cobras: Dict[int, int] = {}
    escadas: Dict[int, int] = {}
    
    # Conjuntos para evitar conflitos
    ocupados_inicio: Set[int] = set() # Onde já existe uma boca de cobra ou base de escada
    destinos_escadas: Set[int] = set() # Onde as escadas terminam (para evitar loops)

    # Configuração de distância mínima (pelo menos 10% do tabuleiro ou 2 casas)
    min_dist = max(2, int(casa_final * 0.05))

    # --- 2. Gerar Escadas (Sobe: inicio < fim) ---
    tentativas = 0
    while len(escadas) < num_itens and tentativas < 1000:
        tentativas += 1
        
        # Escada começa do inicio até quase o fim
        inicio = random.randint(2, casa_final - min_dist - 1)
        # O fim deve ser maior que o inicio
        fim = random.randint(inicio + min_dist, casa_final - 1)
        
        if inicio not in ocupados_inicio:
            escadas[inicio] = fim
            ocupados_inicio.add(inicio)
            destinos_escadas.add(fim)

    # --- 3. Gerar Cobras (Desce: inicio > fim) ---
    # Resetamos tentativas para as cobras
    tentativas = 0
    while len(cobras) < num_itens and tentativas < 1000:
        tentativas += 1
        
        # Cobra começa um pouco a frente e não pode ser a última casa (vitoria)
        inicio = random.randint(min_dist + 2, casa_final - 1)
        # O fim deve ser menor que o inicio
        fim = random.randint(1, inicio - min_dist)
        
        # Validações de Robustez:
        # 1. Não pode ter algo começando ali já.
        # 2. O inicio da cobra não pode ser onde uma escada termina (evita loop: Sobe escada -> Cai na cobra -> Volta pra escada).
        if inicio not in ocupados_inicio and inicio not in destinos_escadas:
            cobras[inicio] = fim
            ocupados_inicio.add(inicio)

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
