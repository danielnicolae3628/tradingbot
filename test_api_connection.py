#!/usr/bin/env python3
"""
KuCoin API Connection Diagnostic Tool
Tests your API credentials and connection
"""

import os
from dotenv import load_dotenv
from kucoin.client import Market, Trade, Margin

# Load environment
load_dotenv()

def test_env_variables():
    """Check if environment variables are loaded"""
    print("=" * 60)
    print("1. CHECKING ENVIRONMENT VARIABLES")
    print("=" * 60)
    
    api_key = os.getenv("KUCOIN_API_KEY")
    api_secret = os.getenv("KUCOIN_API_SECRET")
    api_passphrase = os.getenv("KUCOIN_API_PASSPHRASE")
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    telegram_chat = os.getenv("TELEGRAM_CHAT_ID")
    
    print(f"✓ KUCOIN_API_KEY: {'Present' if api_key else '❌ MISSING'}")
    if api_key:
        print(f"  Length: {len(api_key)} characters")
        print(f"  Preview: {api_key[:10]}...{api_key[-4:]}")
    
    print(f"✓ KUCOIN_API_SECRET: {'Present' if api_secret else '❌ MISSING'}")
    if api_secret:
        print(f"  Length: {len(api_secret)} characters")
    
    print(f"✓ KUCOIN_API_PASSPHRASE: {'Present' if api_passphrase else '❌ MISSING'}")
    if api_passphrase:
        print(f"  Length: {len(api_passphrase)} characters")
    
    print(f"✓ TELEGRAM_BOT_TOKEN: {'Present' if telegram_token else '❌ MISSING (optional)'}")
    print(f"✓ TELEGRAM_CHAT_ID: {'Present' if telegram_chat else '❌ MISSING (optional)'}")
    print()
    
    if not api_key or not api_secret or not api_passphrase:
        print("❌ ERROR: Missing required KuCoin API credentials!")
        print("\nPlease create a .env file with:")
        print("KUCOIN_API_KEY=your_key_here")
        print("KUCOIN_API_SECRET=your_secret_here")
        print("KUCOIN_API_PASSPHRASE=your_passphrase_here")
        return False
    
    return True

def test_market_client():
    """Test Market client (public data)"""
    print("=" * 60)
    print("2. TESTING MARKET CLIENT (Public Data)")
    print("=" * 60)
    
    try:
        # Try without credentials first (public endpoint)
        market = Market()
        
        # Test 1: Server timestamp
        print("Testing server connection...")
        timestamp = market.get_server_timestamp()
        print(f"✅ Server timestamp: {timestamp}")
        
        # Test 2: Get BTC-USDT price
        print("\nTesting market data...")
        ticker = market.get_ticker('BTC-USDT')
        print(f"✅ BTC-USDT price: ${float(ticker['price']):,.2f}")
        
        # Test 3: Get candles
        print("\nTesting candle data...")
        candles = market.get_kline('BTC-USDT', kline_type='5min')
        print(f"✅ Retrieved {len(candles)} candles")
        
        return True
        
    except Exception as e:
        print(f"❌ Market client error: {e}")
        print(f"Error type: {type(e).__name__}")
        return False

def test_authenticated_clients():
    """Test authenticated clients"""
    print("\n" + "=" * 60)
    print("3. TESTING AUTHENTICATED CLIENTS")
    print("=" * 60)
    
    api_key = os.getenv("KUCOIN_API_KEY")
    api_secret = os.getenv("KUCOIN_API_SECRET")
    api_passphrase = os.getenv("KUCOIN_API_PASSPHRASE")
    
    try:
        # Initialize clients
        print("Initializing authenticated clients...")
        
        market = Market(
            key=api_key,
            secret=api_secret,
            passphrase=api_passphrase
        )
        
        trade = Trade(
            key=api_key,
            secret=api_secret,
            passphrase=api_passphrase
        )
        
        margin = Margin(
            key=api_key,
            secret=api_secret,
            passphrase=api_passphrase
        )
        
        print("✅ Clients initialized")
        
        # Test market data with auth
        print("\nTesting authenticated market data...")
        symbols = market.get_symbol_list()
        print(f"✅ Retrieved {len(symbols)} trading symbols")
        
        # Test account access
        print("\nTesting account access...")
        try:
            accounts = trade.get_account_list()
            print(f"✅ Account access working - Found {len(accounts)} accounts")
            
            # Show USDT balance
            for acc in accounts:
                if acc['currency'] == 'USDT' and acc['type'] == 'trade':
                    balance = float(acc['balance'])
                    print(f"   USDT Spot Balance: ${balance:.2f}")
                    
        except Exception as e:
            print(f"⚠️  Account access error: {e}")
            print("   This might mean insufficient API permissions")
        
        # Test margin account
        print("\nTesting margin account access...")
        try:
            margin_account = margin.get_margin_account()
            print(f"✅ Margin account access working")
            
            if 'accounts' in margin_account:
                accounts = margin_account['accounts']
                print(f"   Found {len(accounts)} margin accounts")
                
                # Show margin balances
                for acc in accounts:
                    if acc['currency'] == 'USDT':
                        available = float(acc['available'])
                        print(f"   USDT Margin Available: ${available:.2f}")
                        
        except Exception as e:
            print(f"⚠️  Margin account error: {e}")
            print("   Make sure margin trading is enabled for your API key")
        
        return True
        
    except Exception as e:
        print(f"❌ Authentication error: {e}")
        print(f"Error type: {type(e).__name__}")
        print("\nPossible issues:")
        print("1. API credentials are incorrect")
        print("2. API key doesn't have required permissions")
        print("3. API key is IP-restricted and you're connecting from wrong IP")
        print("4. API key is disabled or deleted")
        return False

def test_trading_pair():
    """Test a specific trading pair"""
    print("\n" + "=" * 60)
    print("4. TESTING TRADING PAIR (BTC-USDT)")
    print("=" * 60)
    
    try:
        market = Market()
        
        # Get 24h stats
        stats = market.get_24h_stats('BTC-USDT')
        print(f"✅ 24h Volume: ${float(stats['volValue']):,.0f}")
        print(f"✅ Last Price: ${float(stats['last']):,.2f}")
        print(f"✅ 24h Change: {float(stats['changeRate']) * 100:+.2f}%")
        
        # Get ticker
        ticker = market.get_ticker('BTC-USDT')
        print(f"✅ Best bid: ${float(ticker['bestBid']):,.2f}")
        print(f"✅ Best ask: ${float(ticker['bestAsk']):,.2f}")
        
        return True
        
    except Exception as e:
        print(f"❌ Trading pair error: {e}")
        return False

def main():
    print("\n" + "🔍" * 30)
    print("KUCOIN API DIAGNOSTIC TOOL")
    print("🔍" * 30 + "\n")
    
    results = []
    
    # Test 1: Environment variables
    results.append(("Environment Variables", test_env_variables()))
    
    if not results[0][1]:
        print("\n" + "=" * 60)
        print("❌ CANNOT CONTINUE WITHOUT API CREDENTIALS")
        print("=" * 60)
        return
    
    # Test 2: Market client (public)
    results.append(("Market Client", test_market_client()))
    
    # Test 3: Authenticated clients
    results.append(("Authenticated Access", test_authenticated_clients()))
    
    # Test 4: Trading pair
    results.append(("Trading Pair", test_trading_pair()))
    
    # Summary
    print("\n" + "=" * 60)
    print("DIAGNOSTIC SUMMARY")
    print("=" * 60)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print("\n" + "=" * 60)
    
    all_passed = all(result[1] for result in results)
    
    if all_passed:
        print("✅ ALL TESTS PASSED!")
        print("\nYour API connection is working correctly.")
        print("You can now run the trading bot with:")
        print("  python trading_bot_improved.py")
    else:
        print("❌ SOME TESTS FAILED")
        print("\nPlease fix the issues above before running the bot.")
        print("\nCommon solutions:")
        print("1. Check your .env file exists and has correct credentials")
        print("2. Verify API key permissions on KuCoin (Settings > API Management)")
        print("3. Make sure API is not IP-restricted")
        print("4. Enable margin trading if needed")
    
    print("=" * 60 + "\n")

if __name__ == "__main__":
    main()