import asyncio
import pandas as pd
from datetime import datetime
from binance.client import Client
from binance.exceptions import BinanceAPIException
from typing import Optional, Dict, List
import logging

from config import config
from database import db
from indicators import TechnicalIndicators

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TradingBot:
    def __init__(self):
        self.client = None
        self.indicators = TechnicalIndicators()
        self.is_running = False
        self.current_position = None
        
    def init_binance_client(self):
        """Initialise le client Binance, en mode réel ou testnet."""
        try:
            if config.is_demo:
                # Mode testnet
                self.client = Client(
                    config.binance_api_key,
                    config.binance_secret_key,
                    testnet=True
                )
                # 👉 Endpoint testnet
                self.client.API_URL = config.testnet_base_url.rstrip("/") + "/api"
                logger.debug(f"[DEBUG] Testnet API_URL défini sur {self.client.API_URL}")
            else:
                # Mode réel
                self.client = Client(
                    config.binance_api_key,
                    config.binance_secret_key
                )
                # 👉 Endpoint mainnet
                self.client.API_URL = "https://api.binance.com/api"
                logger.debug(f"[DEBUG] Mainnet API_URL défini sur {self.client.API_URL}")
            logger.debug(f"[DEBUG] Clés utilisées : {config.binance_api_key[:6]}… / {config.binance_secret_key[:6]}…")
            logger.debug(f"[DEBUG] API_URL après init : {self.client.API_URL}")

            # Test de connexion
            self.client.ping()
            logger.debug("[DEBUG] Ping OK, délai de réponse reçu")
            logger.info("Connexion Binance établie avec succès")
            return True

        except BinanceAPIException as e:
            logger.error(f"Erreur Binance API : {e.message}")
            return False
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation du client Binance : {str(e)}")
            return False
    
    def get_historical_data(self, symbol: str, interval: str, limit: int = 100) -> pd.DataFrame:
        """Récupère les données historiques"""
        try:
            klines = self.client.get_historical_klines(symbol, interval, f"{limit} hours ago UTC")
            
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])
            
            # Conversion des types
            numeric_columns = ['open', 'high', 'low', 'close', 'volume']
            for col in numeric_columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            return df
            
        except Exception as e:
            logger.error(f"Erreur récupération données: {e}")
            return pd.DataFrame()
    
    def get_account_balance(self) -> Dict:
        """Récupère le solde du compte"""
        try:
            account_info = self.client.get_account()
            # DEBUG : log brut pour vérifier qu'on est bien sur le « réel » et que l'API renvoie quelque chose
            logger.info(f"[DEBUG] account_info keys: {list(account_info.keys())}")
            if 'balances' not in account_info:
                logger.error(f"[DEBUG] réponse inattendue: {account_info}")

            for balance in account_info['balances']:
                if balance['asset'] == 'USDT':
                    return {
                        'free': float(balance['free']),
                        'locked': float(balance['locked']),
                        'total': float(balance['free']) + float(balance['locked'])
                    }
            
            return {'free': 0, 'locked': 0, 'total': 0}     
        except Exception as e:
            logger.error(f"Erreur récupération solde: {e}")
            return {'free': 0, 'locked': 0, 'total': 0}
    
    def calculate_position_size(self, entry_price: float, balance: float) -> float:
        """Calcule la taille de position basée sur le risk management"""
        risk_amount = balance * (config.risk_per_trade / 100)
        stop_loss_price = entry_price * (1 - config.stop_loss_pct / 100)
        risk_per_unit = entry_price - stop_loss_price
        
        if risk_per_unit > 0:
            position_size = risk_amount / risk_per_unit
            return round(position_size, 6)
        
        return 0
    
    def place_market_order(self, symbol: str, side: str, quantity: float) -> Optional[Dict]:
        """Place un ordre au marché"""
        try:
            order = self.client.order_market_buy(
                symbol=symbol,
                quantity=quantity
            ) if side == 'BUY' else self.client.order_market_sell(
                symbol=symbol,
                quantity=quantity
            )
            
            logger.info(f"Ordre placé: {order}")
            return order
            
        except BinanceAPIException as e:
            logger.error(f"Erreur placement ordre: {e}")
            return None
    
    def check_entry_conditions(self, df: pd.DataFrame) -> bool:
        """Vérifie les conditions d'entrée"""
        if len(df) < config.rsi_length + 1:
            return False
        
        # Vérifier si on est en bull market
        if not self.indicators.is_bull_market(df):
            return False
        
        # Calculer RSI-VWAP
        rsi_vwap = self.indicators.calculate_rsi_vwap(df, config.rsi_length)
        current_rsi = rsi_vwap.iloc[-1]
        
        # Condition d'entrée: RSI-VWAP < 10
        if current_rsi < config.rsi_entry_threshold:
            logger.info(f"Signal d'entrée détecté - RSI-VWAP: {current_rsi:.2f}")
            return True
        
        return False
    
    def check_exit_conditions(self, df: pd.DataFrame) -> bool:
        """Vérifie les conditions de sortie"""
        if len(df) < config.rsi_length + 1:
            return False
        
        # Calculer RSI-VWAP
        rsi_vwap = self.indicators.calculate_rsi_vwap(df, config.rsi_length)
        current_rsi = rsi_vwap.iloc[-1]
        
        # Condition de sortie: RSI-VWAP > 95
        if current_rsi > config.rsi_exit_threshold:
            logger.info(f"Signal de sortie détecté - RSI-VWAP: {current_rsi:.2f}")
            return True
        
        return False
    
    def open_position(self, symbol: str, df: pd.DataFrame) -> bool:
        """Ouvre une position"""
        try:
            balance = self.get_account_balance()
            current_price = float(df['close'].iloc[-1])
            
            if balance['free'] < 10:  # Minimum 10 USDT
                logger.warning("Solde insuffisant pour ouvrir une position")
                return False
            
            quantity = self.calculate_position_size(current_price, balance['free'])
            
            if quantity <= 0:
                logger.warning("Taille de position invalide")
                return False
            
            # Placer l'ordre
            order = self.place_market_order(symbol, 'BUY', quantity)
            
            if order:
                # Calculer RSI pour enregistrement
                rsi_vwap = self.indicators.calculate_rsi_vwap(df, config.rsi_length)
                current_rsi = rsi_vwap.iloc[-1]
                
                # Enregistrer le trade
                trade_data = {
                    'symbol': symbol,
                    'side': 'BUY',
                    'quantity': quantity,
                    'entry_price': current_price,
                    'status': 'OPEN',
                    'entry_time': datetime.now(),
                    'rsi_entry': current_rsi
                }
                
                trade_id = db.add_trade(trade_data)
                self.current_position = {'trade_id': trade_id, 'quantity': quantity, 'entry_price': current_price}
                
                logger.info(f"Position ouverte: {quantity} {symbol} à {current_price}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Erreur ouverture position: {e}")
            return False
    
    def close_position(self, symbol: str, df: pd.DataFrame) -> bool:
        """Ferme la position actuelle"""
        try:
            if not self.current_position:
                return False
            
            current_price = float(df['close'].iloc[-1])
            quantity = self.current_position['quantity']
            
            # Placer l'ordre de vente
            order = self.place_market_order(symbol, 'SELL', quantity)
            
            if order:
                # Calculer PnL
                entry_price = self.current_position['entry_price']
                pnl = (current_price - entry_price) * quantity
                
                # Calculer RSI pour enregistrement
                rsi_vwap = self.indicators.calculate_rsi_vwap(df, config.rsi_length)
                current_rsi = rsi_vwap.iloc[-1]
                
                # Mettre à jour le trade
                update_data = {
                    'exit_price': current_price,
                    'pnl': pnl,
                    'status': 'CLOSED',
                    'exit_time': datetime.now(),
                    'rsi_exit': current_rsi
                }
                
                db.update_trade(self.current_position['trade_id'], update_data)
                
                logger.info(f"Position fermée: {quantity} {symbol} à {current_price}, PnL: {pnl:.2f}")
                self.current_position = None
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Erreur fermeture position: {e}")
            return False
    
    async def trading_loop(self):
        """Boucle principale de trading"""
        self.is_running = True
        logger.info("Bot de trading démarré")
        
        while self.is_running and config.is_active:
            try:
                # Récupérer les données
                df = self.get_historical_data(config.symbol, config.timeframe, 200)
                
                if df.empty:
                    await asyncio.sleep(60)
                    continue
                
                # Vérifier les positions ouvertes
                if self.current_position is None:
                    # Pas de position, chercher signal d'entrée
                    if self.check_entry_conditions(df):
                        self.open_position(config.symbol, df)
                else:
                    # Position ouverte, chercher signal de sortie
                    if self.check_exit_conditions(df):
                        self.close_position(config.symbol, df)
                
                # Sauvegarder snapshot du capital
                balance = self.get_account_balance()
                db.save_capital_snapshot(balance['total'], balance['total'], 0)
                
                # Attendre avant la prochaine vérification
                await asyncio.sleep(60)  # Vérification chaque minute
                
            except Exception as e:
                logger.error(f"Erreur dans la boucle de trading: {e}")
                await asyncio.sleep(60)
    
    def start_trading(self):
        """Démarre le trading"""
        if self.init_binance_client():
            config.is_active = True
            # Récupérer les positions ouvertes de la DB
            open_trades = db.get_open_trades()
            if open_trades:
                self.current_position = {
                    'trade_id': open_trades[0]['id'],
                    'quantity': open_trades[0]['quantity'],
                    'entry_price': open_trades[0]['entry_price']
                }
            return True
        return False
    
    def stop_trading(self):
        """Arrête le trading"""
        self.is_running = False
        config.is_active = False

# Instance globale
trading_bot = TradingBot()
