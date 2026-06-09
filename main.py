from flask import Flask, request, jsonify
from escpos.printer import Network
from datetime import datetime
from dotenv import load_dotenv

import logging
import os
import re

# =========================================================
# BASE
# =========================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# =========================================================
# ENV
# =========================================================

load_dotenv(os.path.join(BASE_DIR, ".env"))

# =========================================================
# PASTAS
# =========================================================

PEDIDOS_DIR = os.path.join(BASE_DIR, "pedidos")
LOGS_DIR = os.path.join(BASE_DIR, "logs")

os.makedirs(PEDIDOS_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

# =========================================================
# LOG
# =========================================================

logging.basicConfig(
    filename=os.path.join(LOGS_DIR, "bot.log"),
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# =========================================================
# CONFIG
# =========================================================

MODO_TESTE = os.getenv("MODO_TESTE", "False").lower() == "true"

IMPRESSORA_IP = os.getenv("IMPRESSORA_IP")
IMPRESSORA_PORTA = int(os.getenv("IMPRESSORA_PORTA", "9100"))

INSTANCIA_AUTORIZADA = os.getenv(
    "INSTANCIA_AUTORIZADA",
    ""
).strip()

# =========================================================
# APP
# =========================================================

app = Flask(__name__)

ARQUIVO_PEDIDO = os.path.join(
    BASE_DIR,
    "ultimo_pedido.txt"
)

# =========================================================
# HEALTHCHECK
# =========================================================

@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "status": "online",
        "modo_teste": MODO_TESTE
    }), 200

# =========================================================
# NUMERO PEDIDO
# =========================================================

def gerar_numero_pedido():

    try:
        with open(
            ARQUIVO_PEDIDO,
            "r",
            encoding="utf-8"
        ) as f:
            numero = int(f.read().strip())

    except:
        numero = 1000

    numero += 1

    with open(
        ARQUIVO_PEDIDO,
        "w",
        encoding="utf-8"
    ) as f:
        f.write(str(numero))

    return numero

# =========================================================
# LIMPAR TEXTO
# =========================================================

def limpar_texto(texto):

    if not texto:
        return ""

    caracteres = [
        "�",
        "•",
        "🛎",
        "👤",
        "📍",
        "🍔",
        "💰",
        "💳",
        "📝",
        "🚚"
    ]

    for c in caracteres:
        texto = texto.replace(c, "")

    return texto.strip()

# =========================================================
# TEXTO DA MENSAGEM
# =========================================================

def obter_texto_mensagem(data):

    return (
        data.get("data", {})
            .get("message", {})
            .get("conversation")
        or
        data.get("data", {})
            .get("message", {})
            .get("extendedTextMessage", {})
            .get("text")
        or ""
    )

# =========================================================
# VALIDAR
# =========================================================

def validar_pedido(msg):

    return (
        "NOVO PEDIDO" in msg
        and "*Nome:*" in msg
        and "*Pedido:*" in msg
        and "*Total:*" in msg
        and "*Pagamento:*" in msg
    )

# =========================================================
# EXTRAIR
# =========================================================

def extrair_dados(msg):

    dados = {
        "nome": "",
        "endereco": "",
        "pedido": [],
        "total": "",
        "pagamento": "",
        "observacao": ""
    }

    def find(regex):
        m = re.search(regex, msg)
        return m.group(1).strip() if m else ""

    dados["nome"] = find(r"\*Nome:\*\s*(.*)")
    dados["endereco"] = find(r"\*Endereço:\*\s*(.*)")
    dados["total"] = find(r"\*Total:\*\s*R\$\s*(.*)")
    dados["pagamento"] = find(r"\*Pagamento:\*\s*(.*)")
    dados["observacao"] = find(
        r"\*Observação geral:\*\s*(.*)"
    )

    capturar = False

    for linha in msg.splitlines():

        if "*Pedido:*" in linha:
            capturar = True
            continue

        if capturar:

            if "*Total:*" in linha:
                break

            if linha.strip():
                dados["pedido"].append(
                    linha.strip()
                )

    return dados

# =========================================================
# TXT
# =========================================================

def salvar_txt(numero, conteudo):

    arquivo = os.path.join(
        PEDIDOS_DIR,
        f"pedido_{numero}.txt"
    )

    with open(
        arquivo,
        "w",
        encoding="utf-8"
    ) as f:
        f.write(conteudo)

# =========================================================
# IMPRESSAO
# =========================================================

def imprimir_pedido(dados):

    numero = gerar_numero_pedido()

    data_hora = datetime.now().strftime(
        "%d/%m/%Y %H:%M"
    )

    conteudo = f"""
================================
PEDIDO #{numero}
{data_hora}
================================

CLIENTE:
{dados['nome']}

ENDERECO:
{dados['endereco']}

--------------------------------
ITENS
--------------------------------
"""

    for item in dados["pedido"]:
        conteudo += item + "\n"

    conteudo += f"""

--------------------------------
TOTAL: R$ {dados['total']}
PAGAMENTO: {dados['pagamento']}
--------------------------------

OBSERVACOES:
{dados['observacao']}

================================
"""

    conteudo = limpar_texto(conteudo)

    salvar_txt(numero, conteudo)

    if MODO_TESTE:

        logging.info(
            f"Pedido {numero} salvo em modo teste"
        )

        print(conteudo)

        return

    if not IMPRESSORA_IP:

        logging.error(
            "IMPRESSORA_IP nao configurado"
        )

        return

    try:

        printer = Network(
            IMPRESSORA_IP,
            port=IMPRESSORA_PORTA
        )

        printer.text(conteudo)
        printer.cut()
        printer.close()

        logging.info(
            f"Pedido {numero} impresso"
        )

    except Exception as erro:

        logging.error(
            f"Erro impressao: {erro}"
        )

# =========================================================
# WEBHOOK
# =========================================================

# =========================================================
# WEBHOOK
# =========================================================

# =========================================================
# WEBHOOK
# =========================================================

@app.route("/webhook", methods=["POST"])
def webhook():

    try:
        data = request.get_json(silent=True) or {}

        # 1. Se for uma lista (comum em atualizações de status), ignora com 200
        if isinstance(data, list):
            return jsonify({"status": "ignorado_lista"}), 200

        # 2. FILTRO CRUCIAL: Só aceita se for o evento de NOVA MENSAGEM RECEBIDA
        # Ignora históricos, confirmações de leitura, entrega, etc.
        evento = data.get("event", "")
        if evento != "messages.upsert":
            return jsonify({"status": f"ignorado_evento_{evento}"}), 200

        instancia = data.get("instance", "")

        if (
            INSTANCIA_AUTORIZADA
            and
            instancia != INSTANCIA_AUTORIZADA
        ):
            return jsonify({
                "status": "ignorado_instancia"
            }), 200

        msg = obter_texto_mensagem(data)

        if not validar_pedido(msg):
            return jsonify({
                "status": "ignorado_conteudo"
            }), 200

        dados = extrair_dados(msg)

        imprimir_pedido(dados)

        return jsonify({
            "status": "ok"
        }), 200

    except Exception as erro:

        logging.error(
            f"Webhook erro: {erro}"
        )

        return jsonify({
            "status": "erro"
        }), 500

# =========================================================
# START
# =========================================================

if __name__ == "__main__":

    print("=" * 50)
    print("BOT DE IMPRESSAO INICIADO")
    print("Modo teste:", MODO_TESTE)
    print("IP Impressora:", IMPRESSORA_IP)
    print("Instancia:", INSTANCIA_AUTORIZADA)
    print("=" * 50)

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )
