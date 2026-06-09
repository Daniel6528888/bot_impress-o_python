import socket
import win32print

# Mude para o nome EXATO que aparece em "Impressoras e scâneres" no Windows
NOME_IMPRESSORA = "NOME DA IMPRESSORA" 

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# Permite reutilizar a porta imediatamente após reiniciar o script
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind(('0.0.0.0', 9100))
server.listen(1)

print("=" * 50)
print(f"PONTE TCP -> USB ATIVA (Porta 9100)")
print(f"Direcionando para: {NOME_IMPRESSORA}")
print("=" * 50)

while True:
    try:
        conn, addr = server.accept()
        dados = b""
        while True:
            chunk = conn.recv(1024)
            if not chunk: 
                break
            dados += chunk
        
        if dados:
            print(f"Pedido recebido do Docker ({len(dados)} bytes). Enviando para a Oasis USB...")
            
            # Abre a comunicação com o spooler do Windows
            hPrinter = win32print.OpenPrinter(NOME_IMPRESSORA)
            try:
                # Inicia um trabalho de impressão em modo RAW (dados puros ESC/POS)
                hJob = win32print.StartDocPrinter(hPrinter, 1, ("Pedido WhatsApp", None, "RAW"))
                win32print.StartPagePrinter(hPrinter)
                win32print.WritePrinter(hPrinter, dados)
                win32print.EndPagePrinter(hPrinter)
                win32print.EndDocPrinter(hPrinter)
                print("Impressão enviada com sucesso!")
            except Exception as e:
                print(f"Erro ao enviar para a impressora: {e}")
            finally:
                win32print.ClosePrinter(hPrinter)
                
        conn.close()
    except KeyboardInterrupt:
        print("\nDesligando ponte...")
        break
    except Exception as e:
        print(f"Erro na conexão: {e}")
