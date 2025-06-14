import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Optional

class Database:
    def __init__(self, db_path: str = "trading_bot.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialise la base de données"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Table des trades
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                quantity REAL NOT NULL,
                entry_price REAL NOT NULL,
                exit_price REAL,
                pnl REAL,
                status TEXT NOT NULL,
                entry_time TIMESTAMP NOT NULL,
                exit_time TIMESTAMP,
                rsi_entry REAL,
                rsi_exit REAL
            )
        """)
        
        # Table des paramètres utilisateur
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_settings (
                user_id INTEGER PRIMARY KEY,
                settings TEXT NOT NULL
            )
        """)
        
        # Table du capital
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS capital_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP NOT NULL,
                balance REAL NOT NULL,
                equity REAL NOT NULL,
                unrealized_pnl REAL NOT NULL
            )
        """)
        
        conn.commit()
        conn.close()
    
    def add_trade(self, trade_data: Dict):
        """Ajoute un trade à la base"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO trades (symbol, side, quantity, entry_price, exit_price, 
                              pnl, status, entry_time, exit_time, rsi_entry, rsi_exit)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            trade_data.get('symbol'),
            trade_data.get('side'),
            trade_data.get('quantity'),
            trade_data.get('entry_price'),
            trade_data.get('exit_price'),
            trade_data.get('pnl'),
            trade_data.get('status'),
            trade_data.get('entry_time'),
            trade_data.get('exit_time'),
            trade_data.get('rsi_entry'),
            trade_data.get('rsi_exit')
        ))
        
        conn.commit()
        trade_id = cursor.lastrowid
        conn.close()
        return trade_id
    
    def update_trade(self, trade_id: int, update_data: Dict):
        """Met à jour un trade"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        set_clause = ", ".join([f"{k} = ?" for k in update_data.keys()])
        values = list(update_data.values()) + [trade_id]
        
        cursor.execute(f"UPDATE trades SET {set_clause} WHERE id = ?", values)
        conn.commit()
        conn.close()
    
    def get_open_trades(self) -> List[Dict]:
        """Récupère les trades ouverts"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM trades WHERE status = 'OPEN'")
        trades = []
        for row in cursor.fetchall():
            trades.append({
                'id': row[0], 'symbol': row[1], 'side': row[2],
                'quantity': row[3], 'entry_price': row[4], 'exit_price': row[5],
                'pnl': row[6], 'status': row[7], 'entry_time': row[8],
                'exit_time': row[9], 'rsi_entry': row[10], 'rsi_exit': row[11]
            })
        
        conn.close()
        return trades
    
    def get_trading_stats(self) -> Dict:
        """Calcule les statistiques de trading"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Trades fermés
        cursor.execute("SELECT COUNT(*), SUM(pnl), AVG(pnl) FROM trades WHERE status = 'CLOSED'")
        total_trades, total_pnl, avg_pnl = cursor.fetchone()
        
        # Trades gagnants
        cursor.execute("SELECT COUNT(*) FROM trades WHERE status = 'CLOSED' AND pnl > 0")
        winning_trades = cursor.fetchone()[0]
        
        # Trades perdants
        cursor.execute("SELECT COUNT(*) FROM trades WHERE status = 'CLOSED' AND pnl < 0")
        losing_trades = cursor.fetchone()[0]
        
        conn.close()
        
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        return {
            'total_trades': total_trades or 0,
            'total_pnl': total_pnl or 0,
            'avg_pnl': avg_pnl or 0,
            'winning_trades': winning_trades or 0,
            'losing_trades': losing_trades or 0,
            'win_rate': win_rate
        }
    
    def save_capital_snapshot(self, balance: float, equity: float, unrealized_pnl: float):
        """Sauvegarde un snapshot du capital"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO capital_history (timestamp, balance, equity, unrealized_pnl)
            VALUES (?, ?, ?, ?)
        """, (datetime.now(), balance, equity, unrealized_pnl))
        
        conn.commit()
        conn.close()

# Instance globale
db = Database()
