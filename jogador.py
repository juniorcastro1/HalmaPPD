# jogador.py
import socket
import threading
import tkinter as tk
from tkinter import simpledialog, scrolledtext, messagebox

HOST = '127.0.0.1'
PORT = 65432
BOARD_SIZE = 10
CELL_SIZE = 40
P1_INITIAL_POSITIONS = [
    (0, 0), (1, 0), (2, 0), (3, 0), (0, 1), (1, 1), (2, 1), (0, 2), (1, 2), (0, 3)
]
P2_INITIAL_POSITIONS = [
    (BOARD_SIZE - 1 - r, BOARD_SIZE - 1 - c) for r, c in P1_INITIAL_POSITIONS
]

class HalmaClient:
    def __init__(self, master):
        self.master = master
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.board = [[0] * BOARD_SIZE for _ in range(BOARD_SIZE)]
        self.player_id = 0
        self.is_my_turn = False
        self.selected_piece = None
        self.possible_moves = []

        self.forfeit_pending = False # Para a confirmação de desistência
        self.last_status_message = "" # Para restaurar a mensagem de status
        self.scheduled_job = None # Para gerenciar o timer das notificações

        self._setup_ui()
        self._connect_to_server()
        self._setup_pieces()

    def _setup_ui(self):
        self.status_label = tk.Label(self.master, text="Conectando...", font=("Arial", 12))
        self.status_label.pack(pady=5)
        self.canvas = tk.Canvas(self.master, width=BOARD_SIZE*CELL_SIZE, height=BOARD_SIZE*CELL_SIZE, bg='beige')
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.chat_display = scrolledtext.ScrolledText(self.master, height=6, state='disabled')
        self.chat_display.pack(pady=5, padx=5, fill=tk.X)
        chat_frame = tk.Frame(self.master)
        chat_frame.pack(fill=tk.X, padx=5)
        self.chat_input = tk.Entry(chat_frame)
        self.chat_input.pack(side=tk.LEFT, expand=True, fill=tk.X)
        self.chat_input.bind("<Return>", self.send_chat_message)
        self.send_button = tk.Button(chat_frame, text="Enviar", command=self.send_chat_message)
        self.send_button.pack(side=tk.RIGHT)
        self.forfeit_button = tk.Button(self.master, text="Desistir da Partida", command=self.forfeit_game, bg="red", fg="white", activebackground="darkred")
        self.forfeit_button.pack(pady=5)

    def _connect_to_server(self):
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((HOST, PORT))
            threading.Thread(target=self.receive_messages, daemon=True).start()
        except ConnectionRefusedError:
            messagebox.showerror("Erro", "Não foi possível conectar ao servidor.")
            self.master.destroy()
    
    def set_status(self, message, color="black", permanent=False):
        """Define uma mensagem de status permanente."""
        self.status_label.config(text=message, fg=color)
        if permanent:
            self.last_status_message = message
        
    def show_notification(self, message, color="orange", duration=3000):
        """Mostra um aviso temporário no status label."""
        # Cancela qualquer notificação anterior agendada para evitar sobreposição
        if self.scheduled_job:
            self.master.after_cancel(self.scheduled_job)

        current_text = self.status_labelcget("text")
        current_color = self.status_labelcget("fg")
        self.status_label.config(text=message, fg=color)
        
        # Agenda a restauração da mensagem original
        self.scheduled_job = self.master.after(duration, lambda: self.status_label.config(text=current_text, fg=current_color))

    def forfeit_game(self):
        if not self.forfeit_pending:
            self.forfeit_pending = True
            self.forfeit_button.config(text="Confirmar Desistência?", bg="#FFA500") # Laranja
            # Agenda o cancelamento da confirmação
            self.master.after(4000, self.reset_forfeit_button)
        else:
            self.send_message("DESISTENCIA")
            self.reset_forfeit_button()

    def reset_forfeit_button(self):
        """Restaura o botão de desistência ao seu estado original."""
        self.forfeit_pending = False
        self.forfeit_button.config(text="Desistir da Partida", bg="red")

    def receive_messages(self):
        while True:
            try:
                message = self.client_socket.recv(1024).decode('utf-8')
                if not message: 
                    break
                
                parts = message.split(':')
                command = parts[0]

                if command == "BEMVINDO":
                    self.player_id = int(parts[1])
                    self.master.title(f"Halma - Jogador {self.player_id}")
                    self.set_status(f"Você é o Jogador {self.player_id}. Aguardando oponente.", permanent=True)
                elif command == "INICIAR_JOGO":
                    self.set_status("Jogo iniciado!", permanent=True)
                elif command == "SEU_TURNO":
                    self.is_my_turn = True
                    self.set_status("É a sua vez!", color="green", permanent=True)
                elif command == "UPDATE":
                    from_pos = tuple(map(int, parts[1].split(',')))
                    to_pos = tuple(map(int, parts[2].split(',')))
                    self.update_board(from_pos, to_pos)
                    self.is_my_turn = False
                    self.set_status("Vez do oponente.", color="darkred", permanent=True)
                elif command == "CHAT":
                    sender_id, chat_msg = parts[1], ":".join(parts[2:])
                    self.display_message(f"Jogador {sender_id}: {chat_msg}")
                elif command == "VENCEDOR":
                    winner_id = int(parts[1])
                    self.is_my_turn = False
                    reason = " Por desistência." if len(parts) > 2 else "."
                    if winner_id == self.player_id:
                        self.set_status("Você venceu!" + reason, color="blue", permanent=True)
                    else:
                        self.set_status("Você perdeu." + reason, color="black", permanent=True)
                elif command == "ERRO":
                    # Usa o novo sistema de notificação em vez de um messagebox
                    self.show_notification(f"Aviso: {parts[1]}")
                elif command == "OPONENTE_DESCONECTOU":
                    self.is_my_turn = False
                    self.set_status("Oponente desconectou. O jogo terminou.", permanent=True)
            except ConnectionResetError:
                messagebox.showerror("Desconectado", "A conexão com o servidor foi perdida.")
                break

    def _setup_pieces(self):
        for r, c in P1_INITIAL_POSITIONS: self.board[r][c] = 1
        for r, c in P2_INITIAL_POSITIONS: self.board[r][c] = 2
        self.draw_board()

    def draw_board(self):
        self.canvas.delete("all")
        for r in range(BOARD_SIZE):
            for c in range(BOARD_SIZE):
                x1, y1 = c * CELL_SIZE, r * CELL_SIZE
                fill_color = "white"
                if (r, c) in P1_INITIAL_POSITIONS: fill_color = "#E0E8FF"
                elif (r, c) in P2_INITIAL_POSITIONS: fill_color = "#FFE0E0"
                self.canvas.create_rectangle(x1, y1, x1 + CELL_SIZE, y1 + CELL_SIZE, outline="black", fill=fill_color)
        for r, c in self.possible_moves:
            x1, y1 = c * CELL_SIZE, r * CELL_SIZE
            self.canvas.create_oval(x1 + 15, y1 + 15, x1 + CELL_SIZE - 15, y1 + CELL_SIZE - 15, fill="#90EE90", outline="")
        for r in range(BOARD_SIZE):
            for c in range(BOARD_SIZE):
                player = self.board[r][c]
                if player != 0:
                    x1, y1 = c * CELL_SIZE, r * CELL_SIZE
                    piece_color = "blue" if player == self.player_id else "black"
                    self.canvas.create_oval(x1 + 5, y1 + 5, x1 + CELL_SIZE - 5, y1 + CELL_SIZE - 5, fill=piece_color, outline=piece_color)
        if self.selected_piece:
            r, c = self.selected_piece
            x1, y1 = c * CELL_SIZE, r * CELL_SIZE
            self.canvas.create_oval(x1 + 2, y1 + 2, x1 + CELL_SIZE - 2, y1 + CELL_SIZE - 2, outline="red", width=3)

    def on_canvas_click(self, event):
        if not self.is_my_turn: return
        c, r = event.x // CELL_SIZE, event.y // CELL_SIZE
        clicked_pos = (r, c)
        if self.selected_piece and clicked_pos in self.possible_moves:
            from_pos = self.selected_piece
            self.send_message(f"MOVE:{from_pos[0]},{from_pos[1]}:{clicked_pos[0]},{clicked_pos[1]}")
            self.selected_piece = None
            self.possible_moves = []
        elif self.board[r][c] == self.player_id:
            self.selected_piece = clicked_pos
            self.possible_moves = self.calculate_possible_moves(r, c)
        else:
            self.selected_piece = None
            self.possible_moves = []
        self.draw_board()

    def calculate_possible_moves(self, r, c):
        moves = set()
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                if dr == 0 and dc == 0: continue
                nr, nc = r + dr, c + dc
                if 0 <= nr < BOARD_SIZE and 0 <= nc < BOARD_SIZE and self.board[nr][nc] == 0:
                    moves.add((nr, nc))
        self._find_jumps_recursive((r, c), moves, set())
        return list(moves)

    def _find_jumps_recursive(self, current_pos, all_moves, visited_path):
        r, c = current_pos
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                if dr == 0 and dc == 0: continue
                jump_over_r, jump_over_c = r + dr, c + dc
                dest_r, dest_c = r + 2*dr, c + 2*dc
                if (0 <= dest_r < BOARD_SIZE and 0 <= dest_c < BOARD_SIZE and
                        self.board[dest_r][dest_c] == 0 and
                        self.board[jump_over_r][jump_over_c] != 0):
                    if (dest_r, dest_c) not in visited_path:
                        all_moves.add((dest_r, dest_c))
                        new_path = visited_path.copy()
                        new_path.add((dest_r, dest_c))
                        self._find_jumps_recursive((dest_r, dest_c), all_moves, new_path)

    def update_board(self, from_pos, to_pos):
        player = self.board[from_pos[0]][from_pos[1]]
        self.board[to_pos[0]][to_pos[1]] = player
        self.board[from_pos[0]][from_pos[1]] = 0
        self.draw_board()
        
    def send_message(self, message):
        try: 
            self.client_socket.send(message.encode('utf-8'))
        except (BrokenPipeError, ConnectionResetError): self.handle_server_disconnect()
            
    def handle_server_disconnect(self):
        if self.master.winfo_exists():
            messagebox.showerror("Desconectado", "A conexão com o servidor foi perdida.")
            self.master.destroy()
            
    def send_chat_message(self, event=None):
        message = self.chat_input.get()
        if message:
            self.send_message(f"CHAT:{message}")
            self.display_message(f"Eu: {message}")
            self.chat_input.delete(0, tk.END)
    
    def display_message(self, message):
        self.chat_display.config(state='normal')
        self.chat_display.insert(tk.END, message + "\n")
        self.chat_display.config(state='disabled')
        self.chat_display.yview(tk.END)
                
    def on_closing(self):
        if self.client_socket: self.client_socket.close()
        self.master.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = HalmaClient(root)
    root.mainloop()