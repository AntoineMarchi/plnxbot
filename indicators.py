import pandas as pd
import numpy as np
from typing import Tuple

class TechnicalIndicators:
    @staticmethod
    def calculate_rsi_vwap(df: pd.DataFrame, length: int = 50) -> pd.Series:
        """
        Calcule le RSI-VWAP
        """
        # Calcul du VWAP
        df['typical_price'] = (df['high'] + df['low'] + df['close']) / 3
        df['volume_price'] = df['typical_price'] * df['volume']
        
        # VWAP sur période glissante
        vwap = df['volume_price'].rolling(window=length).sum() / df['volume'].rolling(window=length).sum()
        
        # RSI du VWAP
        delta = vwap.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=length).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=length).mean()
        
        rs = gain / loss
        rsi_vwap = 100 - (100 / (1 + rs))
        
        return rsi_vwap
    
    @staticmethod
    def calculate_rsi(series: pd.Series, length: int = 50) -> pd.Series:
        """Calcule le RSI classique"""
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=length).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=length).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    @staticmethod
    def is_bull_market(df: pd.DataFrame, ma_period: int = 200) -> bool:
        """Détermine si on est en bull market (prix > MA200)"""
        ma200 = df['close'].rolling(window=ma_period).mean()
        current_price = df['close'].iloc[-1]
        current_ma = ma200.iloc[-1]
        
        return current_price > current_ma
