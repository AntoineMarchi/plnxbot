import asyncio
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
import matplotlib.pyplot as plt
import io
import base64

from config import config, AUTHORIZED_USERS
from trading_bot import trading_bot
from database import db

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def authorized_only(func):
    """Décorateur pour vérifier l'autorisation"""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if AUTHORIZED_USERS and user_id not in AUTHORIZED_USERS:
            await update.message.reply_text("❌ Accès non autorisé")
            return
        return await func(update, context)
    return wrapper

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Commande /start"""
    keyboard = [
        [InlineKeyboardButton("📊 Dashboard", callback_data="dashboard")],
        [InlineKeyboardButton("⚙️ Paramètres", callback_data="settings")],
        [InlineKeyboardButton("🚀 Start Trading", callback_data="start_trading"),
         InlineKeyboardButton("🛑 Stop Trading", callback_data="stop_trading")],
        [InlineKeyboardButton("💰 Solde", callback_data="balance")],
        [InlineKeyboardButton("📈 Positions", callback_data="positions")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_message = """
🤖 **Bot Trading Bitcoin**

Bienvenue dans votre bot de trading automatisé !

**Stratégie :**
• RSI-VWAP avec période 50
• Entrée : RSI < 10 
• Sortie : RSI > 95
• Timeframe : 15 minutes
• Uniquement positions LONG en bull market

Utilisez le menu ci-dessous pour naviguer.
    """
    
    await update.message.reply_text(welcome_message, reply_markup=reply_markup, parse_mode='Markdown')

@authorized_only
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gestionnaire des boutons inline"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "dashboard":
        await show_dashboard(query)
    elif query.data == "settings":
        await show_settings(query)
    elif query.data == "start_trading":
        await start_trading(query)
    elif query.data == "stop_trading":
        await stop_trading(query)
    elif query.data == "balance":
        await show_balance(query)
    elif query.data == "positions":
        await show_positions(query)
    elif query.data == "start":
        await show_main_menu(query)
    elif query.data.startswith("toggle_"):
        await toggle_setting(query)
    elif query.data == "modify_params":
        await modify_params(query)

async def show_main_menu(query):
    """Affiche le menu principal"""
    keyboard = [
        [InlineKeyboardButton("📊 Dashboard", callback_data="dashboard")],
        [InlineKeyboardButton("⚙️ Paramètres", callback_data="settings")],
        [InlineKeyboardButton("🚀 Start Trading", callback_data="start_trading"),
         InlineKeyboardButton("🛑 Stop Trading", callback_data="stop_trading")],
        [InlineKeyboardButton("💰 Solde", callback_data="balance")],
        [InlineKeyboardButton("📈 Positions", callback_data="positions")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_message = """
🤖 **Bot Trading Bitcoin**

Utilisez le menu ci-dessous pour naviguer.
    """
    
    await query.edit_message_text(welcome_message, reply_markup=reply_markup, parse_mode='Markdown')

async def show_dashboard(query):
    """Affiche le dashboard"""
    stats = db.get_trading_stats()
    balance = trading_bot.get_account_balance() if trading_bot.client else {'total': 0}
    
    status = "🟢 ACTIF" if config.is_active else "🔴 INACTIF"
    mode = "📈 DEMO" if config.is_demo else "💰 RÉEL"
    
    message = f"""
📊 **DASHBOARD**

**Status:** {status}
**Mode:** {mode}
**Symbol:** {config.symbol}

**💰 CAPITAL**
Balance: ${balance['total']:.2f}

**📈 STATISTIQUES**
Trades totaux: {stats['total_trades']}
PnL Total: ${stats['total_pnl']:.2f}
PnL Moyen: ${stats['avg_pnl']:.2f}
Trades gagnants: {stats['winning_trades']}
Trades perdants: {stats['losing_trades']}
Taux de réussite: {stats['win_rate']:.1f}%

**⚙️ PARAMÈTRES ACTUELS**
RSI Longueur: {config.rsi_length}
Entrée RSI: < {config.rsi_entry_threshold}
Sortie RSI: > {config.rsi_exit_threshold}
Risque par trade: {config.risk_per_trade}%
Stop Loss: {config.stop_loss_pct}%
    """
    
    keyboard = [[InlineKeyboardButton("🔄 Actualiser", callback_data="dashboard")],
                [InlineKeyboardButton("◀️ Retour", callback_data="start")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')

async def show_settings(query):
    """Affiche les paramètres"""
    demo_status = "✅" if config.is_demo else "❌"
    active_status = "✅" if config.is_active else "❌"
    
    message = f"""
⚙️ **PARAMÈTRES**

**Trading:**
Mode Demo: {demo_status}
Bot Actif: {active_status}

**Stratégie:**
Symbol: {config.symbol}
Timeframe: {config.timeframe}
RSI Longueur: {config.rsi_length}

**Risk Management:**
Risque/Trade: {config.risk_per_trade}%
Stop Loss: {config.stop_loss_pct}%
Max Positions: {config.max_positions}

**Signaux:**
RSI Entrée: < {config.rsi_entry_threshold}
RSI Sortie: > {config.rsi_exit_threshold}
    """
    
    keyboard = [
        [InlineKeyboardButton(f"Mode Demo {demo_status}", callback_data="toggle_demo")],
        [InlineKeyboardButton("🔧 Modifier Paramètres", callback_data="modify_params")],
        [InlineKeyboardButton("◀️ Retour", callback_data="start")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')

async def toggle_setting(query):
    """Toggle des paramètres"""
    if query.data == "toggle_demo":
        config.is_demo = not config.is_demo
        mode = "DEMO" if config.is_demo else "RÉEL"
        await query.answer(f"Mode changé vers: {mode}")
        await show_settings(query)

async def modify_params(query):
    """Interface de modification des paramètres"""
    message = """
🔧 **MODIFIER LES PARAMÈTRES**

Tapez la commande correspondante :

`/set_risk 2.5` - Définir le risque par trade (%)
`/set_rsi_entry 10` - Définir le seuil RSI d'entrée
`/set_rsi_exit 95` - Définir le seuil RSI de sortie  
`/set_rsi_length 50` - Définir la période RSI
`/set_stop_loss 5` - Définir le stop loss (%)

**Exemples :**
`/set_risk 3` → Risque de 3% par trade
`/set_rsi_entry 15` → Entrée quand RSI < 15
    """
    
    keyboard = [[InlineKeyboardButton("◀️ Retour Paramètres", callback_data="settings")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')

async def start_trading(query):
    """Démarre le trading"""
    if not config.binance_api_key or not config.binance_secret_key:
        await query.edit_message_text("❌ Veuillez configurer vos clés API Binance d'abord")
        return
    
    if trading_bot.start_trading():
        # Démarrer la boucle de trading en arrière-plan
        asyncio.create_task(trading_bot.trading_loop())
        
        message = "🚀 Trading démarré avec succès !\n\n"
        message += f"Mode: {'DEMO' if config.is_demo else 'RÉEL'}\n"
        message += f"Symbol: {config.symbol}\n"
        message += f"Timeframe: {config.timeframe}"
        
        keyboard = [[InlineKeyboardButton("📊 Dashboard", callback_data="dashboard")],
                   [InlineKeyboardButton("🛑 Arrêter", callback_data="stop_trading")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(message, reply_markup=reply_markup)
    else:
        await query.edit_message_text("❌ Erreur lors du démarrage du trading. Vérifiez vos paramètres API.")

async def stop_trading(query):
    """Arrête le trading"""
    trading_bot.stop_trading()
    
    message = "🛑 Trading arrêté.\n\n"
    message += "Toutes les nouvelles positions sont suspendues.\n"
    message += "Les positions ouvertes restent actives."
    
    keyboard = [[InlineKeyboardButton("🚀 Redémarrer", callback_data="start_trading")],
               [InlineKeyboardButton("📊 Dashboard", callback_data="dashboard")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(message, reply_markup=reply_markup)

async def show_balance(query): 
    balance = trading_bot.get_account_balance()
    
    if balance['total'] == 0 and not config.is_demo:
        text = "❌ Impossible de récupérer le solde réel. Vérifiez vos clés API."
    else:
        text = f"""
💰 **SOLDE DU COMPTE**
**USDT :**
Disponible: ${balance['free']:.2f}
Bloqué:    ${balance['locked']:.2f}
Total:     ${balance['total']:.2f}

Mode : {'DEMO (Testnet)' if config.is_demo else 'RÉEL'}
       """
    
    keyboard = [[InlineKeyboardButton("🔄 Actualiser", callback_data="balance")],
               [InlineKeyboardButton("◀️ Retour", callback_data="start")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def show_positions(query):
    """Affiche les positions ouvertes"""
    open_trades = db.get_open_trades()
    
    if not open_trades:
        message = "📈 **POSITIONS**\n\nAucune position ouverte actuellement."
    else:
        message = "📈 **POSITIONS OUVERTES**\n\n"
        
        for trade in open_trades:
            entry_time = datetime.fromisoformat(trade['entry_time']).strftime('%d/%m %H:%M')
            message += f"""
**Trade #{trade['id']}**
Symbol: {trade['symbol']}
Quantité: {trade['quantity']}
Prix d'entrée: ${trade['entry_price']:.2f}
RSI Entrée: {trade['rsi_entry']:.1f}
Date: {entry_time}
---
            """
    
    keyboard = [[InlineKeyboardButton("🔄 Actualiser", callback_data="positions")],
               [InlineKeyboardButton("◀️ Retour", callback_data="start")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')

# Commandes de configuration
@authorized_only
async def set_risk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Définir le risque par trade"""
    try:
        if not context.args:
            await update.message.reply_text("❌ Usage: /set_risk <pourcentage>\nExemple: /set_risk 2.5")
            return
        
        risk = float(context.args[0])
        if 0.1 <= risk <= 10:
            config.risk_per_trade = risk
            await update.message.reply_text(f"✅ Risque par trade défini à {risk}%")
        else:
            await update.message.reply_text("❌ Le risque doit être entre 0.1% et 10%")
    except ValueError:
        await update.message.reply_text("❌ Valeur invalide. Utilisez un nombre décimal.")

@authorized_only
async def set_rsi_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Définir le seuil RSI d'entrée"""
    try:
        if not context.args:
            await update.message.reply_text("❌ Usage: /set_rsi_entry <valeur>\nExemple: /set_rsi_entry 10")
            return
        
        threshold = float(context.args[0])
        if 1 <= threshold <= 30:
            config.rsi_entry_threshold = threshold
            await update.message.reply_text(f"✅ Seuil RSI d'entrée défini à {threshold}")
        else:
            await update.message.reply_text("❌ Le seuil doit être entre 1 et 30")
    except ValueError:
        await update.message.reply_text("❌ Valeur invalide. Utilisez un nombre.")

@authorized_only
async def set_rsi_exit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Définir le seuil RSI de sortie"""
    try:
        if not context.args:
            await update.message.reply_text("❌ Usage: /set_rsi_exit <valeur>\nExemple: /set_rsi_exit 95")
            return
        
        threshold = float(context.args[0])
        if 70 <= threshold <= 99:
            config.rsi_exit_threshold = threshold
            await update.message.reply_text(f"✅ Seuil RSI de sortie défini à {threshold}")
        else:
            await update.message.reply_text("❌ Le seuil doit être entre 70 et 99")
    except ValueError:
        await update.message.reply_text("❌ Valeur invalide. Utilisez un nombre.")

@authorized_only
async def set_rsi_length(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Définir la période RSI"""
    try:
        if not context.args:
            await update.message.reply_text("❌ Usage: /set_rsi_length <période>\nExemple: /set_rsi_length 50")
            return
        
        length = int(context.args[0])
        if 10 <= length <= 200:
            config.rsi_length = length
            await update.message.reply_text(f"✅ Période RSI définie à {length}")
        else:
            await update.message.reply_text("❌ La période doit être entre 10 et 200")
    except ValueError:
        await update.message.reply_text("❌ Valeur invalide. Utilisez un nombre entier.")

@authorized_only
async def set_stop_loss(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Définir le stop loss"""
    try:
        if not context.args:
            await update.message.reply_text("❌ Usage: /set_stop_loss <pourcentage>\nExemple: /set_stop_loss 5")
            return
        
        stop_loss = float(context.args[0])
        if 1 <= stop_loss <= 20:
            config.stop_loss_pct = stop_loss
            await update.message.reply_text(f"✅ Stop loss défini à {stop_loss}%")
        else:
            await update.message.reply_text("❌ Le stop loss doit être entre 1% et 20%")
    except ValueError:
        await update.message.reply_text("❌ Valeur invalide. Utilisez un nombre décimal.")

@authorized_only
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Affiche le status du bot"""
    status = "🟢 ACTIF" if config.is_active else "🔴 INACTIF"
    mode = "📈 DEMO" if config.is_demo else "💰 RÉEL"
    connected = "✅" if trading_bot.client else "❌"
    
    message = f"""
🤖 **STATUS DU BOT**

Status: {status}
Mode: {mode}
Connexion Binance: {connected}
Position ouverte: {'Oui' if trading_bot.current_position else 'Non'}

**Configuration actuelle:**
Symbol: {config.symbol}
Timeframe: {config.timeframe}
RSI Length: {config.rsi_length}
Risque/Trade: {config.risk_per_trade}%
    """
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Commande d'aide"""
    help_text = """
🤖 **AIDE - BOT TRADING BITCOIN**

**Commandes principales:**
/start - Menu principal
/status - Status du bot
/help - Cette aide

**Commandes de configuration:**
/set_risk <valeur> - Risque par trade (%)
/set_rsi_entry <valeur> - Seuil RSI entrée
/set_rsi_exit <valeur> - Seuil RSI sortie
/set_rsi_length <valeur> - Période RSI
/set_stop_loss <valeur> - Stop loss (%)

**Exemples:**
/set_risk 2.5
/set_rsi_entry 10
/set_rsi_exit 95

**Support:**
Pour toute question, contactez l'administrateur.
    """
    
    await update.message.reply_text(help_text, parse_mode='Markdown')

def main():
    """Fonction principale"""
    if not config.telegram_bot_token:
        print("❌ ERREUR: Token Telegram manquant!")
        print("Définissez TELEGRAM_BOT_TOKEN dans config.py ou comme variable d'environnement")
        return
    
    if not trading_bot.init_binance_client():
        print("❌ Impossible de se connecter à Binance avec ces clés.")
        return

    # Créer l'application
    application = Application.builder().token(config.telegram_bot_token).build()
    
    # Ajouter les gestionnaires
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("set_risk", set_risk))
    application.add_handler(CommandHandler("set_rsi_entry", set_rsi_entry))
    application.add_handler(CommandHandler("set_rsi_exit", set_rsi_exit))
    application.add_handler(CommandHandler("set_rsi_length", set_rsi_length))
    application.add_handler(CommandHandler("set_stop_loss", set_stop_loss))
    
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Démarrer le bot
    print("🚀 Bot Telegram démarré...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()