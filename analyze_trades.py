#!/usr/bin/env python3
"""
Trading Bot Performance Analyzer
Analyzes trade_log.csv to show bot performance metrics
"""

import pandas as pd
import numpy as np
from datetime import datetime
import sys

def analyze_trades(log_file='trade_log.csv'):
    """Analyze trading performance from log file"""
    
    try:
        # Read trade log
        df = pd.read_csv(log_file, 
            names=['timestamp', 'symbol', 'action', 'side', 'price', 'size', 'pnl'],
            parse_dates=['timestamp'])
        
        print("=" * 60)
        print("TRADING BOT PERFORMANCE ANALYSIS")
        print("=" * 60)
        print()
        
        # Basic statistics
        total_trades = df[df['action'] == 'open'].shape[0]
        closed_trades = df[df['action'] == 'close'].shape[0]
        open_positions = total_trades - closed_trades
        
        print(f"📊 TRADE STATISTICS")
        print(f"   Total Trades: {total_trades}")
        print(f"   Closed Trades: {closed_trades}")
        print(f"   Open Positions: {open_positions}")
        print()
        
        if closed_trades == 0:
            print("⚠️  No closed trades yet. Run the bot longer for analysis.")
            return
        
        # PnL analysis
        closed_df = df[df['action'] == 'close'].copy()
        closed_df['pnl'] = pd.to_numeric(closed_df['pnl'], errors='coerce')
        
        # Remove any NaN values
        closed_df = closed_df[closed_df['pnl'].notna()]
        
        if len(closed_df) == 0:
            print("⚠️  No valid PnL data available.")
            return
        
        winning_trades = closed_df[closed_df['pnl'] > 0]
        losing_trades = closed_df[closed_df['pnl'] < 0]
        
        total_pnl = closed_df['pnl'].sum()
        avg_pnl = closed_df['pnl'].mean()
        win_rate = (len(winning_trades) / len(closed_df)) * 100
        
        print(f"💰 PROFIT & LOSS")
        print(f"   Total PnL: {total_pnl*100:.2f}%")
        print(f"   Average PnL: {avg_pnl*100:.2f}%")
        print(f"   Win Rate: {win_rate:.1f}%")
        print()
        
        # Win/Loss details
        if len(winning_trades) > 0:
            avg_win = winning_trades['pnl'].mean()
            max_win = winning_trades['pnl'].max()
            print(f"✅ WINNING TRADES ({len(winning_trades)})")
            print(f"   Average Win: {avg_win*100:.2f}%")
            print(f"   Largest Win: {max_win*100:.2f}%")
            print()
        
        if len(losing_trades) > 0:
            avg_loss = losing_trades['pnl'].mean()
            max_loss = losing_trades['pnl'].min()
            print(f"❌ LOSING TRADES ({len(losing_trades)})")
            print(f"   Average Loss: {avg_loss*100:.2f}%")
            print(f"   Largest Loss: {max_loss*100:.2f}%")
            print()
        
        # Risk metrics
        if len(winning_trades) > 0 and len(losing_trades) > 0:
            profit_factor = abs(winning_trades['pnl'].sum() / losing_trades['pnl'].sum())
            risk_reward = abs(avg_win / avg_loss)
            
            print(f"📈 RISK METRICS")
            print(f"   Profit Factor: {profit_factor:.2f}")
            print(f"   Risk/Reward Ratio: {risk_reward:.2f}:1")
            print()
        
        # By symbol
        print(f"📊 PERFORMANCE BY SYMBOL")
        for symbol in closed_df['symbol'].unique():
            symbol_df = closed_df[closed_df['symbol'] == symbol]
            symbol_pnl = symbol_df['pnl'].sum()
            symbol_trades = len(symbol_df)
            symbol_wins = len(symbol_df[symbol_df['pnl'] > 0])
            symbol_wr = (symbol_wins / symbol_trades * 100) if symbol_trades > 0 else 0
            
            print(f"   {symbol}")
            print(f"      Trades: {symbol_trades}, PnL: {symbol_pnl*100:.2f}%, WR: {symbol_wr:.1f}%")
        print()
        
        # Daily performance
        closed_df['date'] = closed_df['timestamp'].dt.date
        daily_pnl = closed_df.groupby('date')['pnl'].sum()
        
        print(f"📅 DAILY PERFORMANCE")
        for date, pnl in daily_pnl.items():
            daily_trades = len(closed_df[closed_df['date'] == date])
            print(f"   {date}: {pnl*100:.2f}% ({daily_trades} trades)")
        print()
        
        # Streaks
        closed_df['win'] = closed_df['pnl'] > 0
        
        current_streak = 0
        max_win_streak = 0
        max_loss_streak = 0
        current_streak_type = None
        
        for win in closed_df['win']:
            if current_streak_type == win:
                current_streak += 1
            else:
                if current_streak_type == True:
                    max_win_streak = max(max_win_streak, current_streak)
                elif current_streak_type == False:
                    max_loss_streak = max(max_loss_streak, current_streak)
                current_streak = 1
                current_streak_type = win
        
        # Final streak
        if current_streak_type == True:
            max_win_streak = max(max_win_streak, current_streak)
        elif current_streak_type == False:
            max_loss_streak = max(max_loss_streak, current_streak)
        
        print(f"🔥 STREAKS")
        print(f"   Max Winning Streak: {max_win_streak}")
        print(f"   Max Losing Streak: {max_loss_streak}")
        print()
        
        # Recommendations
        print("💡 RECOMMENDATIONS")
        if win_rate < 50:
            print("   ⚠️  Win rate below 50% - Consider tightening entry signals")
        if win_rate > 65:
            print("   ✅ Excellent win rate - Strategy is working well")
        
        if len(winning_trades) > 0 and len(losing_trades) > 0:
            if risk_reward < 1.5:
                print("   ⚠️  Risk/Reward below 1.5 - Consider wider take profits")
            if profit_factor < 1.5:
                print("   ⚠️  Profit factor below 1.5 - Review strategy parameters")
            if profit_factor > 2.0:
                print("   ✅ Excellent profit factor!")
        
        if total_pnl > 0.01:
            print(f"   ✅ Profitable! Total gain: {total_pnl*100:.2f}%")
        elif total_pnl < -0.02:
            print(f"   ⚠️  Significant loss: {total_pnl*100:.2f}% - Review parameters")
        
        print()
        print("=" * 60)
        
    except FileNotFoundError:
        print(f"❌ Trade log file '{log_file}' not found.")
        print("   Make sure the bot has been running and creating trades.")
    except Exception as e:
        print(f"❌ Error analyzing trades: {e}")

def show_recent_trades(log_file='trade_log.csv', n=10):
    """Show the most recent trades"""
    try:
        df = pd.read_csv(log_file, 
            names=['timestamp', 'symbol', 'action', 'side', 'price', 'size', 'pnl'],
            parse_dates=['timestamp'])
        
        print("\n" + "=" * 60)
        print(f"LAST {n} TRADES")
        print("=" * 60)
        
        recent = df.tail(n)
        for _, row in recent.iterrows():
            pnl_str = f"{float(row['pnl'])*100:.2f}%" if pd.notna(row['pnl']) else "N/A"
            print(f"{row['timestamp']} | {row['symbol']:12} | {row['action']:6} | "
                  f"{row['side']:5} | ${float(row['price']):10.4f} | PnL: {pnl_str}")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Error showing recent trades: {e}")

if __name__ == "__main__":
    log_file = sys.argv[1] if len(sys.argv) > 1 else 'trade_log.csv'
    
    analyze_trades(log_file)
    show_recent_trades(log_file)
    
    print("\n💡 Tip: Run 'python analyze_trades.py' anytime to see updated statistics")
