# cliente.py
import socket
import threading
import tkinter as tk
from tkinter import simpledialog, scrolledtext, messagebox

HOST = '127.0.0.1'
PORT = 65432
BOARD_SIZE = 10
CELL_SIZE = 40

class HalmaClient:
    def __init__(self, master):
        self.master = master
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.board = [[0] * BOARD_SIZE for _ in range(BOARD_SIZE)]
        self.player_id = 0
        self.is_my_turn = False
        self.selected_piece = None

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
        
        self.forfeit_button = tk.Button(self.master, text="Desistir da Partida", command=self.forfeit_game, bg="red", fg="white")
        self.forfeit_button.pack(pady=5)

    def _setup_pieces(self):
        # Peças do Jogador 1
        initial_positions_p1 = [
            (0, 0), (1, 0), (2, 0), (3, 0), (0, 1), (1, 1), (2, 1), (0, 2), (1, 2), (0, 3)
        ]
        for r, c in initial_positions_p1:
            self.board[r][c] = 1
        # Peças do Jogador 2
        for r, c in initial_positions_p1:
            self.board[BOARD_SIZE - 1 - r][BOARD_SIZE - 1 - c] = 2
        self.draw_board()

    def _connect_to_server(self):
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((HOST, PORT))
            threading.Thread(target=self.receive_messages, daemon=True).start()
        except ConnectionRefusedError:
            messagebox.showerror("Erro", "Não foi possível conectar ao servidor.")
            self.master.destroy()

    def draw_board(self):
        self.canvas.delete("all")
        for r in range(BOARD_SIZE):
            for c in range(BOARD_SIZE):
                x1, y1 = c * CELL_SIZE, r * CELL_SIZE
                x2, y2 = x1 + CELL_SIZE, y1 + CELL_SIZE
                self.canvas.create_rectangle(x1, y1, x2, y2, outline="black", fill="white")
                
                player = self.board[r][c]
                if player != 0:
                    color = "black" if player == 1 else "grey"
                    if self.player_id == 2 and player == 2: color = "black"
                    if self.player_id == 1 and player == 1: color = "blue"

                    self.canvas.create_oval(x1+5, y1+5, x2-5, y2-5, fill=color, outline=color)

        if self.selected_piece:
            r, c = self.selected_piece
            x1, y1 = c * CELL_SIZE, r * CELL_SIZE
            self.canvas.create_oval(x1+2, y1+2, x1+CELL_SIZE-2, y1+CELL_SIZE-2, outline="red", width=3)


    def on_canvas_click(self, event):
        if not self.is_my_turn:
            return
        
        c = event.x // CELL_SIZE
        r = event.y // CELL_SIZE

        if self.selected_piece:
            from_pos = self.selected_piece
            to_pos = (r, c)
            self.send_message(f"MOVE:{from_pos[0]},{from_pos[1]}:{to_pos[0]},{to_pos[1]}")
            self.selected_piece = None
            self.draw_board()
        elif self.board[r][c] == self.player_id:
            self.selected_piece = (r, c)
            self.draw_board()

    def update_board(self, from_pos, to_pos):
        player = self.board[from_pos[0]][from_pos[1]]
        self.board[to_pos[0]][to_pos[1]] = player
        self.board[from_pos[0]][from_pos[1]] = 0
        self.draw_board()

    def send_message(self, message):
        try:
            self.client_socket.send(message.encode('utf-8'))
        except (BrokenPipeError, ConnectionResetError):
            self.handle_server_disconnect()
            
    def handle_server_disconnect(self):
        if not messagebox.showinfo("Desconectado", "A conexão com o servidor foi perdida."):
            self.master.destroy()
            
    def send_chat_message(self, event=None):
        message = self.chat_input.get()
        if message:
            self.send_message(f"CHAT:{message}")
            self.display_message(f"Eu: {message}")
            self.chat_input.delete(0, tk.END)
    
    def forfeit_game(self):
        if messagebox.askyesno("Confirmar", "Você tem certeza que deseja desistir?"):
            self.send_message("DESISTENCIA")

    def display_message(self, message):
        self.chat_display.config(state='normal')
        self.chat_display.insert(tk.END, message + "\n")
        self.chat_display.config(state='disabled')
        self.chat_display.yview(tk.END)

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
                    self.status_label.config(text=f"Você é o Jogador {self.player_id}. Aguardando oponente.")
                elif command == "INICIAR_JOGO":
                    self.status_label.config(text="Jogo iniciado!")
                elif command == "SEU_TURNO":
                    self.is_my_turn = True
                    self.status_label.config(text="É a sua vez!", fg="green")
                elif command == "UPDATE":
                    from_pos = tuple(map(int, parts[1].split(',')))
                    to_pos = tuple(map(int, parts[2].split(',')))
                    self.update_board(from_pos, to_pos)
                    # Se recebemos um update, não é mais nosso turno
                    self.is_my_turn = False
                    self.status_label.config(text="Vez do oponente.", fg="red")
                elif command == "CHAT":
                    sender_id, chat_msg = parts[1], ":".join(parts[2:])
                    self.display_message(f"Jogador {sender_id}: {chat_msg}")
                elif command == "VENCEDOR":
                    winner_id = int(parts[1])
                    self.is_my_turn = False
                    reason = " por desistência." if len(parts) > 2 else "."
                    if winner_id == self.player_id:
                        self.status_label.config(text="Você venceu!" + reason, fg="blue")
                        messagebox.showinfo("Fim de Jogo", "Parabéns, você venceu!")
                    else:
                        self.status_label.config(text="Você perdeu." + reason, fg="black")
                        messagebox.showinfo("Fim de Jogo", "Que pena, você perdeu.")
                elif command == "ERRO":
                    messagebox.showwarning("Aviso", parts[1])
                elif command == "OPONENTE_DESCONECTOU":
                    messagebox.showinfo("Aviso", "O oponente desconectou. O jogo terminou.")
                    self.status_label.config(text="Oponente desconectou.", fg="black")
                    self.is_my_turn = False


            except ConnectionResetError:
                self.handle_server_disconnect()
                break
                
    def on_closing(self):
        if self.client_socket:
            self.client_socket.close()
        self.master.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = HalmaClient(root)
    root.mainloop()