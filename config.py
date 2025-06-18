import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class TradingConfig:
    # Paramètres de trading
    symbol: str = "BTCUSDT"
    timeframe: str = "15m"
    rsi_length: int = 50
    rsi_entry_threshold: float = 10.0
    rsi_exit_threshold: float = 95.0
    
    # Risk Management
    risk_per_trade: float = 2.0  # % du capital par trade
    max_positions: int = 1
    stop_loss_pct: float = 5.0  # % de stop loss
    
    # Trading settings
    is_demo: bool = False
    is_active: bool = False
    
    # API Keys (à remplir)
    binance_api_key: str = ""
    binance_secret_key: str = ""
    telegram_bot_token: str = ""
    
    # Testnet URLs
    testnet_base_url: str = "https://testnet.binance.vision/api"
    
    def __post_init__(self):
        # Charger depuis les variables d'environnement si disponibles
        self.binance_api_key = os.getenv("BINANCE_API_KEY", self.binance_api_key)
        self.binance_secret_key = os.getenv("BINANCE_SECRET_KEY", self.binance_secret_key)
        self.telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN",   self.telegram_bot_token)

# Configuration globale
config = TradingConfig()

# Liste des utilisateurs autorisés (à remplir avec vos chat_id)
AUTHORIZED_USERS = []  # Ex: [123456789, 987654321]
# to find your Telegram ID: @get_id_bot