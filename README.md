# Bot Trading Bitcoin Telegram

## 🚀 Installation Complète

### Prérequis

1. **Python 3.8+** installé sur votre système
2. **Compte Binance** (ou testnet pour les tests)
3. **Bot Telegram** créé via @BotFather

### Étape 1: Installation de Python et pip

#### Windows:
1. Téléchargez Python depuis https://python.org
2. Cochez "Add Python to PATH" lors de l'installation
3. Vérifiez: `python --version` dans cmd

#### Linux/Mac:
```bash
sudo apt update
sudo apt install python3 python3-pip


#Pour installer le bot il vous suffit de cloner le repo github https://github.com/AntoineMarchi/plnxbot avec la commande "git clone #ssh"
#Une fois cloné crée un venv
#Rentrez sur le venv: source venv/bin/activate
#Télécharger tous les requirements du fichiers requirements.txt
#Dans config.py rentrer votre Telegram ID: # to find your Telegram ID: @get_id_bot
#Puis se connecter:
For connect at Binance and Bot, execute this command:
export TELEGRAM_BOT_TOKEN=""
export BINANCE_API_KEY=""
export BINANCE_SECRET_KEY=""
#lancer le main: python ou python3 main.py

#Le bot est lancé!