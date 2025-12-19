# 📱 Guia Passo a Passo: Criando e Configurando o Bot no Telegram

Este guia detalha todo o processo de criação do bot no Telegram e integração com o código desenvolvido.

---

## 📋 Índice

1. [Criar o Bot no Telegram](#1-criar-o-bot-no-telegram)
2. [Descobrir seu Chat ID (Admin)](#2-descobrir-seu-chat-id-admin)
3. [Obter Chave da API BaratoInsta](#3-obter-chave-da-api-baratoinsta)
4. [Preparar o Servidor/Computador](#4-preparar-o-servidorcomputador)
5. [Instalar o Projeto](#5-instalar-o-projeto)
6. [Configurar o Arquivo .env](#6-configurar-o-arquivo-env)
7. [Executar o Bot](#7-executar-o-bot)
8. [Testar o Bot](#8-testar-o-bot)
9. [Manter o Bot Rodando 24/7](#9-manter-o-bot-rodando-247)

---

## 1. Criar o Bot no Telegram

### Passo 1.1: Abrir o BotFather

1. Abra o aplicativo **Telegram** no celular ou computador
2. Na barra de pesquisa, digite: `@BotFather`
3. Clique no resultado que tem o ícone ✓ azul (verificado)

![BotFather](https://i.imgur.com/botfather.png)

### Passo 1.2: Iniciar conversa com BotFather

1. Clique em **"Iniciar"** ou envie `/start`
2. O BotFather vai responder com uma lista de comandos

### Passo 1.3: Criar um novo bot

1. Envie o comando: `/newbot`
2. O BotFather vai perguntar: **"Alright, a new bot. How are we going to call it?"**
3. Digite o **nome de exibição** do seu bot (pode ter espaços e emojis)
   - Exemplo: `SMM Store Bot` ou `🚀 Seguidores Express`

### Passo 1.4: Definir o username do bot

1. O BotFather vai perguntar: **"Good. Now let's choose a username for your bot"**
2. Digite um **username único** que termine com `bot`
   - Exemplo: `smm_store_bot` ou `seguidores_express_bot`
   - ⚠️ O username deve ser único em todo o Telegram
   - ⚠️ Só pode conter letras, números e underscores
   - ⚠️ Deve terminar com `bot`

### Passo 1.5: Copiar o Token

1. Após criar, o BotFather vai enviar uma mensagem com o **Token**
2. A mensagem será algo como:

```
Done! Congratulations on your new bot. You will find it at t.me/seu_bot.
You can now add a description, about section and profile picture for your bot.

Use this token to access the HTTP API:
7123456789:AAHxxxxxxxxxxxxxxxxxxxxxxxxxxx

Keep your token secure and store it safely.
```

3. **COPIE O TOKEN** (a parte `7123456789:AAHxxxxxxxxxxxxxxxxxxxxxxxxxxx`)
4. **GUARDE EM LOCAL SEGURO** - Este token dá acesso total ao seu bot!

### Passo 1.6: Configurar o bot (Opcional mas recomendado)

Ainda no BotFather, você pode personalizar seu bot:

```
/setdescription - Definir descrição (aparece quando alguém abre o bot)
/setabouttext - Definir texto "Sobre" 
/setuserpic - Definir foto de perfil do bot
/setcommands - Definir lista de comandos
```

**Para definir os comandos, envie:**
```
/setcommands
```

Selecione seu bot e envie:
```
start - Iniciar o bot
pedido - Fazer novo pedido
servicos - Ver serviços disponíveis
meuspedidos - Ver meus pedidos
status - Consultar status de pedido
ajuda - Obter ajuda
cancelar - Cancelar operação
```

---

## 2. Descobrir seu Chat ID (Admin)

O Chat ID é necessário para você receber notificações de pedidos e aprovar comprovantes.

### Método 1: Usando @userinfobot

1. No Telegram, pesquise por: `@userinfobot`
2. Clique em **"Iniciar"** ou envie `/start`
3. O bot vai responder com suas informações:

```
@seuusername
Id: 123456789    ← Este é seu Chat ID
First: Seu Nome
Lang: pt-br
```

4. **Copie o número do ID** (ex: `123456789`)

### Método 2: Usando @getmyid_bot

1. Pesquise por: `@getmyid_bot`
2. Envie `/start`
3. Copie o número do "Your user ID"

### Método 3: Usando @RawDataBot

1. Pesquise por: `@RawDataBot`
2. Envie qualquer mensagem
3. Procure por `"id":` na resposta

---

## 3. Obter Chave da API BaratoInsta

### Passo 3.1: Criar conta no BaratoInsta

1. Acesse: **https://baratoinsta.com**
2. Clique em **"Registrar"** ou **"Criar Conta"**
3. Preencha seus dados e confirme o email

### Passo 3.2: Adicionar saldo (necessário para usar a API)

1. Faça login na sua conta
2. Vá em **"Adicionar Fundos"** ou **"Depositar"**
3. Adicione saldo via PIX ou outro método disponível

### Passo 3.3: Obter a chave API

1. Após fazer login, vá em **"Configurações"** ou **"API"**
2. Procure por **"Chave API"** ou **"API Key"**
3. Se não tiver uma chave, clique em **"Gerar Nova Chave"**
4. **Copie a chave API** (será algo como: `a1b2c3d4e5f6g7h8i9j0...`)

⚠️ **IMPORTANTE:** Guarde esta chave em segurança! Ela dá acesso à sua conta.

---

## 4. Preparar o Servidor/Computador

### Opção A: VPS Linux (Recomendado para produção)

Se você vai usar uma VPS (DigitalOcean, Vultr, Contabo, etc.):

```bash
# Conectar via SSH
ssh root@seu_ip_da_vps

# Atualizar sistema
sudo apt update && sudo apt upgrade -y

# Instalar Python 3 e pip
sudo apt install python3 python3-pip python3-venv -y

# Instalar Tesseract OCR com português
sudo apt install tesseract-ocr tesseract-ocr-por -y

# Verificar instalações
python3 --version
tesseract --version
```

### Opção B: Computador Windows

1. **Instalar Python:**
   - Acesse: https://www.python.org/downloads/
   - Baixe a versão mais recente (3.10+)
   - Durante instalação, marque ✅ **"Add Python to PATH"**

2. **Instalar Tesseract:**
   - Acesse: https://github.com/UB-Mannheim/tesseract/wiki
   - Baixe o instalador Windows
   - Durante instalação, selecione o idioma **"Portuguese"**
   - Anote o caminho de instalação (geralmente `C:\Program Files\Tesseract-OCR`)

### Opção C: Computador macOS

```bash
# Instalar Homebrew (se não tiver)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Instalar Python e Tesseract
brew install python3 tesseract tesseract-lang
```

---

## 5. Instalar o Projeto

### Passo 5.1: Baixar/Extrair os arquivos

1. Extraia o arquivo `bot_telegram_smm.zip` em uma pasta
2. Ou clone do repositório (se disponível)

### Passo 5.2: Abrir o terminal na pasta do projeto

**Windows:**
- Abra a pasta do projeto
- Segure Shift + clique direito
- Selecione "Abrir janela do PowerShell aqui"

**Linux/macOS:**
```bash
cd /caminho/para/bot_telegram_smm
```

### Passo 5.3: Criar ambiente virtual (recomendado)

```bash
# Criar ambiente virtual
python3 -m venv venv

# Ativar ambiente virtual
# Linux/macOS:
source venv/bin/activate

# Windows:
venv\Scripts\activate
```

Você verá `(venv)` no início da linha do terminal.

### Passo 5.4: Instalar dependências

```bash
pip install -r requirements.txt
```

Aguarde a instalação de todas as bibliotecas.

---

## 6. Configurar o Arquivo .env

### Passo 6.1: Criar o arquivo .env

```bash
# Linux/macOS:
cp .env.example .env

# Windows (PowerShell):
Copy-Item .env.example .env
```

### Passo 6.2: Editar o arquivo .env

Abra o arquivo `.env` com um editor de texto:

**Linux:**
```bash
nano .env
```

**Windows:**
- Abra com Bloco de Notas ou VS Code

### Passo 6.3: Preencher as configurações

Edite o arquivo com suas informações:

```env
# ==========================================
# TELEGRAM
# ==========================================
# Cole o token que você copiou do BotFather
BOT_TOKEN=7123456789:AAHxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Cole seu Chat ID (número que você copiou do @userinfobot)
ADMIN_ID=123456789

# ==========================================
# API BARATOINSTA
# ==========================================
# Cole sua chave API do BaratoInsta
API_KEY_BARATOINSTA=sua_chave_api_aqui

# ==========================================
# PAGAMENTO PIX
# ==========================================
# Sua chave PIX para receber pagamentos
CHAVE_PIX=seuemail@gmail.com

# Tipo da chave (email, cpf, telefone ou aleatoria)
TIPO_CHAVE_PIX=email

# Seu nome (aparece no comprovante)
NOME_BENEFICIARIO=Seu Nome Completo
```

### Passo 6.4: Salvar o arquivo

**nano:** Pressione `Ctrl+X`, depois `Y`, depois `Enter`
**Bloco de Notas:** `Ctrl+S`

### Exemplo de .env preenchido:

```env
BOT_TOKEN=7123456789:AAHdF8sK2mN9pQ4rT6uW8xZ0bC3eG5iJ7kL
ADMIN_ID=987654321
API_KEY_BARATOINSTA=abc123def456ghi789jkl012mno345pqr678
CHAVE_PIX=meuemail@gmail.com
TIPO_CHAVE_PIX=email
NOME_BENEFICIARIO=João da Silva
```

---

## 7. Executar o Bot

### Passo 7.1: Verificar se tudo está correto

```bash
# Verificar se o ambiente virtual está ativo
# Deve aparecer (venv) no início da linha

# Testar os módulos
python test_modules.py
```

Se todos os testes passarem (✅), você está pronto!

### Passo 7.2: Iniciar o bot

```bash
python bot.py
```

Você verá algo como:
```
2024-01-15 10:30:00 - __main__ - INFO - Iniciando Bot SMM...
2024-01-15 10:30:00 - database - INFO - Banco de dados inicializado com sucesso
2024-01-15 10:30:01 - __main__ - INFO - Bot iniciado com sucesso!
```

### Passo 7.3: Manter o terminal aberto

O bot só funciona enquanto o terminal estiver aberto e o script rodando.

---

## 8. Testar o Bot

### Passo 8.1: Abrir o bot no Telegram

1. No Telegram, pesquise pelo username do seu bot (ex: `@seu_bot`)
2. Ou acesse diretamente: `t.me/seu_bot`

### Passo 8.2: Testar comandos básicos

1. Envie `/start` - Deve aparecer o menu principal
2. Clique em "📦 Fazer Pedido" - Deve mostrar categorias
3. Envie `/ajuda` - Deve mostrar informações de ajuda

### Passo 8.3: Testar como Admin

1. Envie `/admin` - Deve abrir o painel administrativo
2. Envie `/stats` - Deve mostrar estatísticas

### Passo 8.4: Fazer um pedido de teste

1. Clique em "📦 Fazer Pedido"
2. Selecione uma categoria
3. Selecione um serviço
4. Envie um link de teste
5. Envie uma quantidade
6. Verifique se o resumo do pedido aparece corretamente

---

## 9. Manter o Bot Rodando 24/7

### Opção A: Usando Screen (Linux)

```bash
# Instalar screen
sudo apt install screen -y

# Criar uma sessão
screen -S smmbot

# Ativar ambiente virtual e iniciar bot
source venv/bin/activate
python bot.py

# Desconectar da sessão (bot continua rodando)
# Pressione: Ctrl+A, depois D

# Para voltar à sessão:
screen -r smmbot

# Para ver sessões ativas:
screen -ls
```

### Opção B: Usando systemd (Linux - Recomendado)

1. Criar arquivo de serviço:
```bash
sudo nano /etc/systemd/system/smmbot.service
```

2. Colar o conteúdo (ajuste os caminhos):
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

3. Ativar e iniciar:
```bash
sudo systemctl daemon-reload
sudo systemctl enable smmbot
sudo systemctl start smmbot
```

4. Verificar status:
```bash
sudo systemctl status smmbot
```

5. Ver logs:
```bash
sudo journalctl -u smmbot -f
```

### Opção C: Usando PM2 (Linux/Windows/macOS)

```bash
# Instalar Node.js primeiro (se não tiver)
# Depois instalar PM2
npm install -g pm2

# Iniciar o bot
pm2 start bot.py --interpreter python3 --name smmbot

# Salvar configuração
pm2 save
pm2 startup

# Comandos úteis:
pm2 status          # Ver status
pm2 logs smmbot     # Ver logs
pm2 restart smmbot  # Reiniciar
pm2 stop smmbot     # Parar
```

---

## 🔧 Solução de Problemas Comuns

### Erro: "Token inválido"
- Verifique se copiou o token corretamente do BotFather
- Não deve ter espaços antes ou depois do token

### Erro: "Tesseract not found"
- Linux: `sudo apt install tesseract-ocr tesseract-ocr-por`
- Windows: Adicione ao .env: `TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe`

### Bot não responde
- Verifique se o bot está rodando (terminal aberto)
- Verifique os logs em `data/bot.log`
- Certifique-se de que o token está correto

### Erro de permissão (Linux)
```bash
chmod +x bot.py
```

### Erro de conexão com API
- Verifique sua chave API do BaratoInsta
- Verifique se tem saldo na conta
- Teste a conexão com internet

---

## 📞 Resumo das Credenciais Necessárias

| Credencial | Onde Obter | Exemplo |
|------------|------------|---------|
| BOT_TOKEN | @BotFather no Telegram | `7123456789:AAHxxx...` |
| ADMIN_ID | @userinfobot no Telegram | `123456789` |
| API_KEY_BARATOINSTA | Painel do BaratoInsta | `abc123def456...` |
| CHAVE_PIX | Seu banco/app de pagamentos | `email@exemplo.com` |

---

## ✅ Checklist Final

- [ ] Bot criado no BotFather
- [ ] Token copiado
- [ ] Chat ID obtido
- [ ] Chave API do BaratoInsta obtida
- [ ] Python instalado
- [ ] Tesseract instalado
- [ ] Dependências instaladas (`pip install -r requirements.txt`)
- [ ] Arquivo .env configurado
- [ ] Bot testado e funcionando
- [ ] Bot configurado para rodar 24/7

---

**🎉 Parabéns! Seu bot está pronto para uso!**

Se tiver dúvidas, consulte o arquivo README.md ou os logs em `data/bot.log`.
