# tabuleiro.py
"""
Aqui é definido as regras e estado do jogo. Tabuleiro, tamanho dele, etc.
"""
class HalmaGame:
    def __init__(self, board_size=10):
        self.board_size = board_size
        self.board = [[0] * board_size for _ in range(board_size)]
        self.current_turn = 1  # o jogador 1 sempre começa(eu poderia botar um dado ou moeda para ver quem começa?)
        self.winner = None
        self._setup_pieces()

    def _setup_pieces(self):
        """Posiciona as peças iniciais para os dois jogadores."""
        # Peças do Jogador 1 (canto superior esquerdo) 
        # Embora, pudesse ser em um canto aleatório
        initial_positions_p1 = [
            (0, 0), (1, 0), (2, 0), (3, 0),
            (0, 1), (1, 1), (2, 1),
            (0, 2), (1, 2),
            (0, 3)
        ]

        #Para cada posição da matriz é adicionado um valor(1 ou 2) para saber qual peça é de qual jogador
        for r, c in initial_positions_p1:
            self.board[r][c] = 1

        # Peças do Jogador 2 (canto inferior direito)
        # Função para dispor as peças baseado nas peças do primeiro jogador usando espelhamento
        for r, c in initial_positions_p1:
            self.board[self.board_size - 1 - r][self.board_size - 1 - c] = 2

    def get_board(self):
        return self.board

    def is_valid_move(self, player, from_pos, to_pos, path):
        """Verifica se um movimento é válido (adjacente ou salto)."""
        from_r, from_c = from_pos
        to_r, to_c = to_pos

        # Validações básicas
        if not (0 <= to_r < self.board_size and 0 <= to_c < self.board_size):
            return False  # Fora do tabuleiro
        if self.board[to_r][to_c] != 0:
            return False  # Célula de destino não está vazia
        if self.board[from_r][from_c] != player:
            return False  # Não é sua peça

        # Movimento adjacente (só permitido se for o primeiro passo)
        is_adjacent = abs(from_r - to_r) <= 1 and abs(from_c - to_c) <= 1
        if is_adjacent and not path:
            return True

        # Movimento de salto
        jump_r = from_r + (to_r - from_r) // 2
        jump_c = from_c + (to_c - from_c) // 2

        is_jump = abs(from_r - to_r) in [0, 2] and abs(from_c - to_c) in [0, 2]
        if is_jump and self.board[jump_r][jump_c] != 0:
             # Não pode saltar sobre uma casa já visitada no mesmo movimento
            if to_pos not in path:
                return True

        return False

    def move_piece(self, player, from_pos, to_pos):
        """
        Executa o movimento e troca o turno.
        Assume que o movimento já foi validado.
        """
        if self.current_turn != player:
            return False, "Não é o seu turno."

        from_r, from_c = from_pos
        to_r, to_c = to_pos
        self.board[to_r][to_c] = player
        self.board[from_r][from_c] = 0

        self.check_win_condition()
        if not self.winner:
            self.current_turn = 3 - player  # Alterna entre 1 e 2
        
        return True, "Movimento realizado."

    def check_win_condition(self):
        """Verifica se algum jogador venceu."""
        # Zona de vitória do jogador 1 (canto inferior direito)
        p1_wins = True
        destination_p1 = [
            (self.board_size - 1 - r, self.board_size - 1 - c)
            for r, c in [
                (0, 0), (1, 0), (2, 0), (3, 0),
                (0, 1), (1, 1), (2, 1),
                (0, 2), (1, 2),
                (0, 3)
            ]
        ]
        for r, c in destination_p1:
            if self.board[r][c] != 1:
                p1_wins = False
                break
        if p1_wins:
            self.winner = 1

        # Zona de vitória do jogador 2 (canto superior esquerdo)
        p2_wins = True
        destination_p2 = [
            (0, 0), (1, 0), (2, 0), (3, 0),
            (0, 1), (1, 1), (2, 1),
            (0, 2), (1, 2),
            (0, 3)
        ]
        for r, c in destination_p2:
            if self.board[r][c] != 2:
                p2_wins = False
                break
        if p2_wins:
            self.winner = 2