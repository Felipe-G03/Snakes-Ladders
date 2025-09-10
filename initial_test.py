import random

class Tabuleiro:
    def __init__(self, tamanho=100):
        self.tamanho = tamanho
        self.eventos = self.gerar_eventos_balanceados()

    def gerar_eventos_balanceados(self):
        eventos = {}
        
        # tabuleiro de 100 casas -> 20 eventos (10 escadas e 10 cobras)
        num_total_events = self.tamanho // 5
        num_ladders = num_total_events // 2
        num_snakes = num_total_events - num_ladders
        
        
        min_jump = self.tamanho // 20

        for _ in range(num_ladders):
            while True:
                #
                start = random.randint(2, self.tamanho - min_jump)
                end = random.randint(start + min_jump, self.tamanho)
                if start not in eventos and end not in eventos and start != end:
                    eventos[start] = end
                    break

        for _ in range(num_snakes):
            while True:
                start = random.randint(min_jump + 1, self.tamanho)
                end = random.randint(1, start - min_jump)
                if start not in eventos and end not in eventos and start != end:
                    eventos[start] = end
                    break
        
        return eventos

    def get_evento(self, posicao):
        return self.eventos.get(posicao, None)


class Jogador:
    def __init__(self, nome):
        self.nome = nome
        self.posicao = 0

    def mover(self, passos):
        self.posicao += passos
        print(f"Você tirou {passos} e se moveu para a casa {self.posicao}.")


class Jogo:
    def __init__(self):
        board_size = self.get_board_size()
        num_jogadores = self.get_player_count()
        self.tabuleiro = Tabuleiro(board_size)
        self.jogadores = [Jogador(f'Jogador {i+1}') for i in range(num_jogadores)]

    def get_player_count(self):
        while True:
            try:
                num = int(input("Quantos jogadores vão participar? "))
                if num > 0:
                    return num
                else:
                    print("O número de jogadores deve ser maior que zero.")
            except ValueError:
                print("Entrada inválida. Por favor, digite um número.")

    def get_board_size(self):
        while True:
            try:
                size = int(input("Escolha o tamanho do tabuleiro (múltiplo de 10, a partir de 50): "))
                # Nova validação: tamanho deve ser >= 50, múltiplo de 10 e maior que zero
                if size >= 50 and size % 10 == 0:
                    return size
                else:
                    print("Tamanho inválido. Por favor, insira um múltiplo de 10 a partir de 50.")
            except ValueError:
                print("Entrada inválida. Por favor, digite um número.")

    def rolar_dado(self):
        return random.randint(1, 6)

    def iniciar_partida(self):
        print("\n--- Snakes & Ladders! ---")
        vencedor = None
        while not vencedor:
            for jogador in self.jogadores:
                input(f"\n{jogador.nome}, é a sua vez. Pressione Enter para rolar o dado...")
                
                dice_roll = self.rolar_dado()
                
                nova_posicao = jogador.posicao + dice_roll
                
                if nova_posicao > self.tabuleiro.tamanho:
                    print(f"Você tirou {dice_roll}, mas precisa de um valor exato para chegar ao final. Você permanece em {jogador.posicao}.")
                    continue
                
                jogador.mover(dice_roll)

                evento_posicao = self.tabuleiro.get_evento(jogador.posicao)
                if evento_posicao:
                    if evento_posicao > jogador.posicao:
                        print(f"🎉 Subiu a escada! Você foi para a posição {evento_posicao}.")
                    else:
                        print(f"🐍 Desceu na cobra paizão lá ele 1000 vezes! Você foi para a posição {evento_posicao}.")
                    jogador.posicao = evento_posicao

                print(f"Posição atual de {jogador.nome}: {jogador.posicao}.")

                if jogador.posicao >= self.tabuleiro.tamanho:
                    vencedor = jogador.nome
                    break
        
        print(f"\n🏆 Parabéns, {vencedor}! Você venceu o jogo!")


if __name__ == "__main__":
    jogo = Jogo()
    jogo.iniciar_partida()
    
