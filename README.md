# 🤖 WhatsApp Thermal Printer Bot (Evolution API + Docker)

Este projeto é um bot de automação focado no recebimento de pedidos/mensagens via WhatsApp, processamento inteligente de texto (via Regex) e envio automático para impressão em impressoras térmicas ESC/POS (como a Oasis OIA 8387 ou similares), mesmo que estejam conectadas via USB em uma máquina local Windows.

A arquitetura foi desenhada utilizando **Docker** para garantir resiliência e isolamento dos serviços, conectando-se internamente com a **Evolution API** e expondo a porta de entrada com segurança via **Ngrok**.

---

## 🚀 Como o Projeto Funciona                O NGROK NÃO SERÁ NECESSARIO POR SE TRATAR DE UM BOT INTERNO

O fluxo de comunicação foi estruturado para manter o tráfego o mais rápido, local e seguro possível:

1. **Entrada:** O cliente envia uma mensagem no WhatsApp. Os servidores da Evolution API recebem e disparam um Webhook.
2. **Tráfego Externo:** O **Ngrok** recebe essa requisição externa com segurança e a repassa para dentro do ambiente isolado do Docker.
3. **Filtro e Processamento (`main.py`):** A **Evolution API** envia o payload diretamente para o contêiner do bot através da rede interna do Docker (sem expor o bot para a internet). O script Flask valida a instância, aplica Expressões Regulares (Regex) para extrair os dados limpos do pedido e formata o layout em comandos puros `ESC/POS`.
4. **Impressão Local (`ponte_usb.py`):** O Docker envia os dados brutos de impressão para o sistema hospedeiro (Windows) através do gateway `host.docker.internal:9100`. O script de ponte local captura os bytes em modo `RAW` e faz o despacho direto para o spooler de impressão do Windows.

---

## 🛠️ Tecnologias Utilizadas

* **Python 3.13** (Flask, python-dotenv, escpos)
* **Docker & Docker Compose**
* **Evolution API v2** (Instância de conexão com WhatsApp)
* **PostgreSQL 13 & Redis** (Dados e cache da API)
* **Ngrok** (Tunelamento seguro)
* **PyWin32** (Para comunicação nativa com o Spooler do Windows)

---

## 📂 Estrutura de Arquivos Recomendada

Para rodar o projeto, sua estrutura de diretórios deve ser organizada assim:

```text
├── pedidos/               # Criado automaticamente (Logs de texto dos pedidos)
├── logs/                  # Criado automaticamente (Logs de erro/funcionamento)
├── .env                   # Arquivo de configuração local (NÃO enviar ao GitHub)
├── .env.example           # Modelo de configuração para novos usuários
├── .gitignore             # Arquivos ignorados pelo Git
├── docker-compose.yml     # Orquestração dos contêineres (API, DB, Redis, Bot, Ngrok)
├── main.py                # Servidor Flask que processa o Webhook e monta o layout ESC/POS
├── ponte_usb.py           # Script Windows que recebe o tráfego do Docker e manda para a USB
└── iniciar ponte.bat      # Executável facilitado para o cliente abrir a ponte USB
