# servidor.py
import socket
import threading
from tabuleiro import HalmaGame

HOST = '127.0.0.1'
PORT = 65432
jogadores = []
player_map = {}
jogo = HalmaGame()
game_lock = threading.Lock()

def handle_jogador(conn, player_id):
    global jogo
    print(f"[JOGADOR {player_id}] Conectado de {conn.getpeername()}")

    while True:
        try:
            data = conn.recv(1024).decode('utf-8')
            if not data:
                break

            print(f"[JOGADOR {player_id}] Mensagem: {data}")
            parts = data.split(':')
            command = parts[0]

            with game_lock:
                if command == "MOVE":
                    if jogo.current_turn != player_id:
                        conn.send("ERRO: Calma lá, ainda não é o seu turno!.".encode('utf-8'))
                        continue
                    
                    from_pos = tuple(map(int, parts[1].split(',')))
                    to_pos = tuple(map(int, parts[2].split(',')))
                    
                    if jogo.is_valid_move(player_id, from_pos, to_pos, []):
                        jogo.move_piece(player_id, from_pos, to_pos)
                        broadcast(f"UPDATE:{from_pos[0]},{from_pos[1]}:{to_pos[0]},{to_pos[1]}")
                        
                        if jogo.winner:
                            broadcast(f"VENCEDOR:{jogo.winner}")
                        else: # Envia o turno para o próximo jogador
                             jogadores[jogo.current_turn-1].send(f"SEU_TURNO".encode('utf-8'))
                    else:
                        conn.send("ERRO:Movimento inválido.".encode('utf-8'))
                
                elif command == "CHAT":
                    message = parts[1]
                    broadcast(f"CHAT:{player_id}:{message}", sender_conn=conn)
                
                elif command == "DESISTENCIA":
                    winner = 3 - player_id
                    broadcast(f"VENCEDOR:{winner}:DESISTENCIA")

        except (ConnectionResetError, IndexError):
            break

    print(f"[JOGADOR {player_id}] Desconectado.")
    jogadores.remove(conn)
    conn.close()
    if len(jogadores) < 2 and not jogo.winner:
         broadcast("OPONENTE_DESCONECTOU")

def broadcast(message, sender_conn=None):
    for client_conn in jogadores:
        if client_conn != sender_conn:
            try:
                client_conn.send(message.encode('utf-8'))
            except Exception as e:
                print(f"Erro ao transmitir: {e}")

def start_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((HOST, PORT))
    server_socket.listen(2)
    print(f"[ESCUTANDO] Servidor em {HOST}:{PORT}")

    player_id_counter = 1
    while True:
        conn, addr = server_socket.accept()
        if len(jogadores) < 2:
            jogadores.append(conn)
            player_map[conn] = player_id_counter
            
            thread = threading.Thread(target=handle_jogador, args=(conn, player_id_counter))
            thread.start()
            
            conn.send(f"BEMVINDO:{player_id_counter}".encode('utf-8'))
            player_id_counter += 1

            if len(jogadores) == 2:
                print("Ambos os jogadores conectados. Iniciando o jogo.")
                broadcast("INICIAR_JOGO")
                # Envia o comando de turno para o primeiro jogador
                jogadores[0].send("SEU_TURNO".encode('utf-8'))
        else:
            conn.send("Poxa, a sala está cheia.".encode('utf-8'))
            conn.close()

if __name__ == "__main__":
    start_server()