# 🤖 Bot Telegram SMM - Revenda Automatizada

Bot completo para Telegram em Python para revenda automatizada de serviços de marketing digital (seguidores, curtidas, visualizações), com integração à API do BaratoInsta e validação automática de pagamentos PIX via OCR.

## 📋 Índice

- [Funcionalidades](#-funcionalidades)
- [Pré-requisitos](#-pré-requisitos)
- [Instalação](#-instalação)
- [Configuração](#-configuração)
- [Como Executar](#-como-executar)
- [Estrutura do Projeto](#-estrutura-do-projeto)
- [Comandos do Bot](#-comandos-do-bot)
- [Sistema de Precificação](#-sistema-de-precificação)
- [Validação OCR](#-validação-ocr)
- [Painel Administrativo](#-painel-administrativo)
- [Deploy em Produção](#-deploy-em-produção)
- [Troubleshooting](#-troubleshooting)
- [Licença](#-licença)

## ✨ Funcionalidades

### Para Usuários
- 📦 **Catálogo de Serviços**: Navegação intuitiva por categorias (Instagram, TikTok, YouTube, etc.)
- 💳 **Pagamento PIX**: Geração automática de dados para pagamento
- 🔍 **Validação Automática**: OCR para validar comprovantes em segundos
- 📊 **Acompanhamento**: Consulta de status dos pedidos em tempo real
- 🔔 **Notificações**: Alertas sobre status dos pedidos

### Para Administradores
- ✅ **Aprovação Manual**: Interface para aprovar comprovantes suspeitos
- 📈 **Estatísticas**: Dashboard com métricas de vendas e lucro
- 🛡️ **Anti-Fraude**: Detecção de comprovantes duplicados
- 📝 **Logs**: Registro detalhado de todas as operações

### Técnicas
- 🔄 **Integração API**: Conexão completa com BaratoInsta
- 💰 **Precificação Inteligente**: Margens de lucro configuráveis
- 🗄️ **Banco de Dados**: SQLite para persistência de dados
- ⏰ **Jobs Automáticos**: Expiração de pedidos não pagos

## 📋 Pré-requisitos

### Sistema Operacional
- Linux (Ubuntu 20.04+ recomendado)
- Windows 10+ ou macOS 10.15+

### Software Necessário
- **Python 3.8+** (recomendado 3.10+)
- **Tesseract OCR** com suporte a português
- **pip** (gerenciador de pacotes Python)

### Instalação do Tesseract

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install tesseract-ocr tesseract-ocr-por
```

**macOS:**
```bash
brew install tesseract tesseract-lang
```

**Windows:**
1. Baixe o instalador em: https://github.com/UB-Mannheim/tesseract/wiki
2. Durante a instalação, selecione o idioma "Portuguese"
3. Adicione o caminho ao PATH ou configure no `.env`

## 🚀 Instalação

### 1. Clone ou baixe o projeto
```bash
git clone <url-do-repositorio>
cd bot_telegram_smm
```

### 2. Crie um ambiente virtual (recomendado)
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# ou
venv\Scripts\activate  # Windows
```

### 3. Instale as dependências
```bash
pip install -r requirements.txt
```

### 4. Configure as variáveis de ambiente
```bash
cp .env.example .env
nano .env  # ou use seu editor preferido
```

### 5. Crie o diretório de dados
```bash
mkdir -p data
```

## ⚙️ Configuração

### Arquivo `.env`

Edite o arquivo `.env` com suas credenciais:

```env
# Telegram
BOT_TOKEN=seu_token_do_botfather
ADMIN_ID=seu_chat_id

# API BaratoInsta
API_KEY_BARATOINSTA=sua_chave_api

# Pagamento PIX
CHAVE_PIX=sua_chave_pix
TIPO_CHAVE_PIX=email
NOME_BENEFICIARIO=Seu Nome
```

### Obtendo as Credenciais

#### Token do Bot (Telegram)
1. Abra o Telegram e procure por `@BotFather`
2. Envie `/newbot` e siga as instruções
3. Copie o token fornecido

#### Seu Chat ID (Admin)
1. Procure por `@userinfobot` no Telegram
2. Envie `/start`
3. Copie o número do seu ID

#### Chave API BaratoInsta
1. Acesse sua conta em baratoinsta.com
2. Vá em Configurações > API
3. Copie sua chave de API

## ▶️ Como Executar

### Modo Desenvolvimento
```bash
python bot.py
```

### Modo Produção (com logs)
```bash
python bot.py >> data/output.log 2>&1 &
```

### Verificar se está rodando
```bash
ps aux | grep bot.py
```

## 📁 Estrutura do Projeto

```
bot_telegram_smm/
├── bot.py              # Código principal do bot
├── config.py           # Configurações e constantes
├── database.py         # Funções de banco de dados
├── ocr_processor.py    # Processamento OCR de comprovantes
├── api_client.py       # Cliente da API BaratoInsta
├── pricing.py          # Lógica de precificação
├── utils.py            # Funções auxiliares
├── requirements.txt    # Dependências Python
├── .env.example        # Exemplo de configuração
├── .env                # Suas configurações (não commitar!)
├── README.md           # Esta documentação
└── data/
    ├── pedidos.db      # Banco de dados SQLite
    └── bot.log         # Arquivo de logs
```

## 🎮 Comandos do Bot

### Comandos para Usuários

| Comando | Descrição |
|---------|-----------|
| `/start` | Inicia o bot e mostra menu principal |
| `/pedido` | Inicia fluxo de novo pedido |
| `/servicos` | Lista todos os serviços disponíveis |
| `/status <ID>` | Consulta status de um pedido |
| `/meuspedidos` | Lista seus últimos pedidos |
| `/ajuda` | Mostra ajuda e suporte |
| `/cancelar` | Cancela operação em andamento |

### Comandos Administrativos

| Comando | Descrição |
|---------|-----------|
| `/admin` | Abre painel administrativo |
| `/stats` | Mostra estatísticas de vendas |

## 💰 Sistema de Precificação

O bot aplica margens de lucro automaticamente:

| Preço da API | Tipo de Margem | Exemplo |
|--------------|----------------|---------|
| < R$ 20,00 | Fixa (+R$ 4,00) | R$ 15,00 → R$ 19,00 |
| R$ 20,00 - R$ 99,99 | 25% | R$ 50,00 → R$ 62,50 |
| ≥ R$ 100,00 | 20% | R$ 150,00 → R$ 180,00 |

### Personalizar Margens

Edite no arquivo `.env`:
```env
MARGEM_FIXA=4.00
MARGEM_PERCENTUAL_MEDIO=0.25
MARGEM_PERCENTUAL_ALTO=0.20
```

## 🔍 Validação OCR

O sistema valida comprovantes PIX automaticamente verificando:

1. **Palavras-chave PIX**: "pix", "transferência", "comprovante"
2. **Valor correto**: Com tolerância de R$ 0,10
3. **Data recente**: Hoje ou ontem
4. **Status de confirmação**: "concluído", "aprovado", "realizado"

### Fluxo de Validação

```
Comprovante recebido
        ↓
   Pré-processamento (OpenCV)
        ↓
   Extração de texto (Tesseract)
        ↓
   Verificação de duplicata (MD5)
        ↓
┌───────┴───────┐
│               │
↓               ↓
Todas          Algumas
validações     validações
passam         falham
↓               ↓
Aprovação      Envio para
Automática     Admin
```

## 🔧 Painel Administrativo

### Aprovação de Comprovantes

Quando um comprovante é suspeito, o admin recebe:
- Foto do comprovante
- Dados do pedido
- Motivo da suspeita
- Botões de Aprovar/Rejeitar

### Estatísticas Disponíveis

- Total de usuários
- Total de pedidos
- Faturamento total e diário
- Lucro total
- Pedidos por status
- Saldo na API

## 🚀 Deploy em Produção

### Usando systemd (Linux)

1. Crie o arquivo de serviço:
```bash
sudo nano /etc/systemd/system/smm-bot.service
```

2. Adicione o conteúdo:
```ini
[Unit]
Description=Bot Telegram SMM
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/bot_telegram_smm
Environment=PATH=/home/ubuntu/bot_telegram_smm/venv/bin
ExecStart=/home/ubuntu/bot_telegram_smm/venv/bin/python bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

3. Ative e inicie o serviço:
```bash
sudo systemctl daemon-reload
sudo systemctl enable smm-bot
sudo systemctl start smm-bot
```

4. Verificar status:
```bash
sudo systemctl status smm-bot
```

### Usando PM2 (Node.js)

```bash
# Instalar PM2
npm install -g pm2

# Iniciar bot
pm2 start bot.py --interpreter python3 --name smm-bot

# Salvar configuração
pm2 save
pm2 startup
```

### Usando Docker

```dockerfile
FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-por \
    libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
CMD ["python", "bot.py"]
```

```bash
docker build -t smm-bot .
docker run -d --name smm-bot --env-file .env smm-bot
```

## 🔧 Troubleshooting

### Erro: "Tesseract not found"

**Linux:**
```bash
sudo apt install tesseract-ocr tesseract-ocr-por
```

**Windows:**
Configure o caminho no `.env`:
```env
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
```

### Erro: "cv2 not found"

```bash
pip install opencv-python-headless
```

### Bot não responde

1. Verifique se o token está correto
2. Verifique se o bot está rodando: `ps aux | grep bot.py`
3. Verifique os logs: `tail -f data/bot.log`

### OCR não reconhece texto

1. Verifique se o idioma português está instalado:
```bash
tesseract --list-langs
```

2. Se "por" não aparecer, instale:
```bash
sudo apt install tesseract-ocr-por
```

### Erro de conexão com API

1. Verifique sua chave API
2. Verifique sua conexão com internet
3. Verifique se a API está online

## 📊 Banco de Dados

### Tabelas

- **usuarios**: Dados dos usuários do bot
- **pedidos**: Todos os pedidos realizados
- **servicos_cache**: Cache dos serviços da API
- **comprovantes**: Hashes para detecção de duplicatas
- **logs**: Registro de operações

### Backup

```bash
# Backup manual
cp data/pedidos.db data/pedidos_backup_$(date +%Y%m%d).db

# Backup automático (cron)
0 0 * * * cp /home/ubuntu/bot_telegram_smm/data/pedidos.db /home/ubuntu/backups/pedidos_$(date +\%Y\%m\%d).db
```

## 🔒 Segurança

### Boas Práticas

1. **Nunca** commite o arquivo `.env`
2. Use senhas fortes para o servidor
3. Mantenha o sistema atualizado
4. Faça backups regulares
5. Monitore os logs

### Proteções Implementadas

- Limite de tentativas de comprovante
- Detecção de comprovantes duplicados
- Expiração automática de pedidos
- Validação de URLs e quantidades
- Logs de tentativas suspeitas

## 📝 Licença

Este projeto é fornecido "como está", sem garantias. Use por sua conta e risco.

## 🆘 Suporte

Para dúvidas ou problemas:
1. Verifique a seção de Troubleshooting
2. Consulte os logs em `data/bot.log`
3. Entre em contato com o desenvolvedor

---

**Desenvolvido com ❤️ para automatizar sua revenda SMM**
