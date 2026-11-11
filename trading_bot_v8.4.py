"""
╔══════════════════════════════════════════════════════════════════╗
║     ELITE CRYPTO TRADING BOT — v8.4 "Volume"                    ║
║                                                                    ║
║  v8.4 "Volume" (aggressive profile -- UNVALIDATED, live test):    ║
║   More trades/day, smaller targets: conf>=55, ADX<=45, no hour    ║
║   filter, 15 movers, 25 trades/day, loss-streak pause 5.          ║
║   SL 2xATR (min 0.7%), TPs 1.8/3.0/4.5 ATR split 40/35/25,        ║
║   early break-even at +0.45%, 2h time exit.                       ║
║   Sizing follows LIVE equity (was fixed 10), 30%/trade, 1% risk.  ║
║   Guards: -3% daily loss, drawdown pause at -10% from peak.       ║
║   Untracked coins are ALERT-ONLY (v8.3.3 auto-sold user coins).   ║
║   Rotating 20MB log, hourly CSV/state backup to ~/trade_backups.  ║
║                                                                    ║
║  v8.3.3 fixes (from review of the v8.3.2 live trade log):         ║
║   • WALLET AUDIT: independent check of EVERY non-zero balance     ║
║     against tracked positions, not just symbols the bot BELIEVES  ║
║     are open. Runs forced on startup, then every                  ║
║     WALLET_AUDIT_INTERVAL seconds, plus on demand via /audit.     ║
║     Untracked non-dust holdings are logged to a separate audit    ║
║     CSV, alerted immediately, and "adopted" (protective stop      ║
║     placed right away) so they're never naked again.              ║
║     This is the fix for TAO-USDT-style ghosts: two OPENs, zero    ║
║     exits, ever -- almost certainly a state_file load failure     ║
║     that silently dropped a real open position from tracking      ║
║     while the coins stayed in the wallet, unmanaged.              ║
║   • load_state() failures no longer just log a warning and        ║
║     continue with an empty (wrong) position dict -- they set      ║
║     state_load_ok=False, which forces the startup audit above     ║
║     to run before the bot does anything else.                     ║
║   • Stop-loss exits try the REAL fill via get_fill_details() on   ║
║     the stop order id first (same lookup already used for         ║
║     regular orders) instead of always booking at the stop         ║
║     trigger price -- a triggered stop-market order can slip in    ║
║     a fast move, so the trigger price was only ever an estimate.  ║
║   • Trade-log CSV columns pnl_gross/pnl_net renamed to             ║
║     pnl_gross_pct/pnl_net_pct. They were ALWAYS percentage         ║
║     returns (already multiplied by 100), never dollars -- the     ║
║     unlabeled names read like currency and caused a real           ║
║     misdiagnosis reviewing this log externally. realized_usd and   ║
║     fee_usd remain the only dollar columns; no values changed,     ║
║     just the header.                                               ║
║                                                                    ║
║  v8.3.2 fixes (from first live week's incident review):           ║
║   • HOLDINGS VERIFIER: the wallet balance is the ground truth.    ║
║     If the coins are gone (stop filled / manual sell), the trade  ║
║     is finalized and BOOKED (estimated at stop price) -- no more  ║
║     phantom "open" positions or unbooked stop-loss exits.         ║
║     CRITICAL: last week's stop-outs were never booked, so the     ║
║     stats only counted winners. Fixed.                            ║
║   • DUST HANDLING: holdings worth < $0.30 or below lot size ->    ║
║     trade is finalized once, with the dust noted. No more         ║
║     "too low to sell" alert loops. TP tranches that floor to      ║
║     zero skip the level instead of spamming.                      ║
║   • DUST PREVENTION: entries whose TP1 tranche would be below     ║
║     the lot minimum are skipped up front.                         ║
║   • FUNNEL v2: global gates (hour, positions full, ...) count     ║
║     once per CYCLE; daily_limits split into named reasons.        ║
║     x12321 "daily_limits" is now e.g. "max_positions_open x64".   ║
║   • /close SYMBOL command to force-close/clear stuck positions.   ║
║   • Sell-failure alerts throttled to once per hour per symbol.    ║
║   • Capacity raised: MAX_OPEN_POSITIONS 2->3, MAX_DAILY_TRADES    ║
║     6->10 (the funnel showed capacity was the binding gate while  ║
║     completed ladders were clean).                                ║
║                                                                    ║
║  v8.3.1 changes (merge of v8.3 + best of 8.1/8.2):                ║
║   • HYBRID UNIVERSE: 9 core coins always scanned + top movers     ║
║     by 24h $ volume from the full USDT universe (liquidity floor, ║
║     no stables / leveraged tokens). More trades -> more data.     ║
║   • FILTER FUNNEL: every entry filter counts its rejections;      ║
║     /filters shows exactly which gate is strangling trade flow.   ║
║   • Blended RR gate (30/40/30-weighted, from 8.1) — the honest    ║
║     risk:reward math instead of measuring against TP3 only.       ║
║   • Returns-based correlation blocker (from 8.2) replaces the     ║
║     hardcoded groups; works for coins we didn't anticipate.       ║
║   • /calendar with daily win/loss counters (from 8.1).            ║
║   • Per-leg dollar equity curve -> truthful drawdown shape.       ║
║                                                                    ║
║  Carries forward from v8.3 (unchanged):                           ║
║   exchange-side stops, real fills & fees, dollar accounting,      ║
║   persisted stats, live precision rules, stop reconciliation.     ║
║                                                                    ║
║  v8.3 changes (fixes #0-#5 from professional review):             ║
║                                                                    ║
║  #0 FIXED: vol_ma20 / vol_ratio KeyError (bot crashed on every    ║
║     symbol in v8 — indicators referenced columns never created)   ║
║  #1 NEW: Exchange-side STOP-MARKET orders on KuCoin.              ║
║     SL survives VM reboot / network loss / loop hang.             ║
║     Stop is cancel/replaced on break-even move and trailing.      ║
║  #2 FIXED: PnL accounting is now in DOLLARS, booked at EVERY      ║
║     fill (partial exits included — v8 silently dropped them).     ║
║     30/40/30 split computed from ORIGINAL size (v8 sold 28%       ║
║     at TP2 instead of 40%).                                       ║
║  #3 NEW: Real fill prices + real fees fetched from the exchange   ║
║     after every order. SL/TP recomputed from actual entry fill.   ║
║  #4 REMOVED: News sentiment module (dead/paywalled endpoints).    ║
║     Weights rebalanced: Tech 45 / Regime 22 / Volume 16 / Mom 17. ║
║  #5 FIXED: Confidence sizing no longer inert — position cap now   ║
║     scales with the confidence multiplier. Tiers aligned with     ║
║     MIN_CONFIDENCE (62-69 small / 70-84 normal / 85+ large).      ║
║                                                                    ║
║  Bonus: trade_results & equity_curve now persist across restarts; ║
║         lot sizes + price increments loaded live from KuCoin.     ║
║                                                                    ║
║  NOTE: state file (bot_state_v83.json) and trade log              ║
║  (elite_trades_v83.csv) are unchanged from v8.3.2/v8.3.1.         ║
║  New in v8.3.3: wallet_audit_v83.csv.                             ║
╚══════════════════════════════════════════════════════════════════╝
"""

import warnings
warnings.filterwarnings("ignore")

import os
import time
import json
import uuid
import hmac
import base64
import hashlib
import logging
import datetime
import csv
import math
import shutil
import requests
import pandas as pd
import numpy as np
from typing import Optional, Tuple
from collections import deque
from dotenv import load_dotenv

try:
    from kucoin.client import Market, Trade, User
    USE_OLD_API = False
except ImportError:
    from kucoin.client import Client
    USE_OLD_API = True

from ta.momentum import RSIIndicator, StochasticOscillator
from ta.trend import EMAIndicator, MACD, ADXIndicator
from ta.volatility import BollingerBands, AverageTrueRange

load_dotenv()

KC_BASE = "https://api.kucoin.com"

# ═══════════════════════════════════════════════════════════════
#  UNIVERSE — data-proven winners only (278-trade analysis)
#  NOTE: treat per-coin WR as a HYPOTHESIS until validated
#  out-of-sample in the backtester (small sample sizes!)
# ═══════════════════════════════════════════════════════════════
SYMBOLS = [
    {"symbol": "SUI-USDT",  "base": "SUI",  "quote": "USDT"},
    {"symbol": "NEAR-USDT", "base": "NEAR", "quote": "USDT"},
    {"symbol": "DOGE-USDT", "base": "DOGE", "quote": "USDT"},
    {"symbol": "ATOM-USDT", "base": "ATOM", "quote": "USDT"},
    {"symbol": "DOT-USDT",  "base": "DOT",  "quote": "USDT"},
    {"symbol": "POL-USDT",  "base": "POL",  "quote": "USDT"},
    {"symbol": "FIL-USDT",  "base": "FIL",  "quote": "USDT"},
    {"symbol": "LTC-USDT",  "base": "LTC",  "quote": "USDT"},
    {"symbol": "TRX-USDT",  "base": "TRX",  "quote": "USDT"},
]

# ═══ HYBRID UNIVERSE (v8.3.1) ═══
USE_DYNAMIC_UNIVERSE   = True
QUOTE_CURRENCY         = "USDT"
UNIVERSE_REFRESH_HOURS = 24
TOP_MOVERS_N           = 15
MIN_24H_DOLLAR_VOLUME  = 3_000_000
LEVERAGED_SUFFIXES     = ("3L", "3S", "5L", "5S", "2L", "2S")
STABLE_BASES           = {"USDC", "USDT", "DAI", "TUSD", "USDD", "FDUSD", "PYUSD", "BUSD", "EUR"}
EXCLUDE_BASES          = {"BTC", "ETH"}

CORRELATION_THRESHOLD  = 0.85
CORR_CANDLE_TTL        = 120

LOT_RULES = {
    "SUI-USDT":  (0.1,   0.1),
    "NEAR-USDT": (0.01,  0.01),
    "DOGE-USDT": (1.0,   1.0),
    "ATOM-USDT": (0.01,  0.01),
    "DOT-USDT":  (0.01,  0.01),
    "POL-USDT":  (0.1,   0.1),
    "FIL-USDT":  (0.01,  0.01),
    "LTC-USDT":  (0.001, 0.001),
    "TRX-USDT":  (1.0,   1.0),
}

PRICE_INCREMENTS = {}

PRICE_SANITY = {
    "SUI-USDT":  (0.1,   50.0),
    "NEAR-USDT": (0.1,   50.0),
    "DOGE-USDT": (0.001, 5.0),
    "ATOM-USDT": (0.5,   100.0),
    "DOT-USDT":  (0.1,   100.0),
    "POL-USDT":  (0.01,  10.0),
    "FIL-USDT":  (0.1,   100.0),
    "LTC-USDT":  (10.0,  1000.0),
    "TRX-USDT":  (0.01,  5.0),
}

SYMBOL_MAX_SL = {
    "NEAR-USDT": 0.012,
    "FIL-USDT":  0.012,
    "SUI-USDT":  0.010,
}

# ═══════════════════════════════════════════════════════════════
#  RISK MANAGEMENT
# ═══════════════════════════════════════════════════════════════
PORTFOLIO_SIZE         = 10
MAX_RISK_PER_TRADE     = 0.01
MAX_OPEN_POSITIONS     = 3
MAX_PORTFOLIO_HEAT     = 0.30
MAX_DAILY_TRADES       = 25
MAX_DAILY_LOSS         = -0.03
DAILY_PROFIT_TARGET    = 0.12
MIN_CONFIDENCE         = 55
MIN_RR_RATIO           = 1.3
MAX_CONSECUTIVE_LOSSES = 5
MAX_SYMBOL_DAILY_LOSSES= 2
KUCOIN_FEE_RATE        = 0.001

BASE_ALLOCATION_PCT    = 0.30

# ── v8.4 additions ──
USE_DYNAMIC_EQUITY     = True    # size trades off the REAL balance, not the fixed 10
MIN_EQUITY             = 5.0     # floor for the sizing base
MAX_POSITION_PCT       = 0.40    # hard cap: one position <= 40% of equity
MAX_DRAWDOWN_PAUSE     = 0.10    # pause entries if equity is 10% below its peak (/resume to reset)
EARLY_BE_TRIGGER       = 0.0045  # once +0.45% in profit (before TP1) ...
EARLY_BE_LOCK          = 0.0020  # ... move the stop to +0.20% (covers round-trip fees)
TIME_EXIT_SECONDS      = 7200    # flat trades are recycled after 2h (was 4h)
ADOPT_UNTRACKED        = False   # NEVER trade coins the bot didn't open; alert only
BACKUP_DIR             = os.path.expanduser("~/trade_backups")

# ═══════════════════════════════════════════════════════════════
#  CONFIDENCE WEIGHTS (must sum to 1.00)
# ═══════════════════════════════════════════════════════════════
CONF_WEIGHT_TECHNICAL  = 0.45
CONF_WEIGHT_REGIME     = 0.22
CONF_WEIGHT_VOLUME     = 0.16
CONF_WEIGHT_MOMENTUM   = 0.17

# ═══════════════════════════════════════════════════════════════
#  REGIME FILTER
# ═══════════════════════════════════════════════════════════════
MAX_ADX_FOR_ENTRY      = 45
MAX_ATR_PCT_FOR_ENTRY  = 0.035
MIN_BB_WIDTH_FOR_ENTRY = 0.005
MAX_BB_WIDTH_FOR_ENTRY = 0.08

# ═══════════════════════════════════════════════════════════════
#  DYNAMIC SL/TP — 30% / 40% / 30% split (of ORIGINAL size)
# ═══════════════════════════════════════════════════════════════
ATR_SL_MULTIPLIER    = 2.0
ATR_TP1_MULTIPLIER   = 1.8
ATR_TP2_MULTIPLIER   = 3.0
ATR_TP3_MULTIPLIER   = 4.5
ATR_TRAIL_MULTIPLIER = 1.0
MIN_SL_PCT           = 0.007
MAX_SL_PCT           = 0.02

TP1_SELL_PCT         = 0.40
TP2_SELL_PCT         = 0.35

# ═══════════════════════════════════════════════════════════════
#  EXCHANGE-SIDE STOP ORDERS
# ═══════════════════════════════════════════════════════════════
STOP_SYNC_INTERVAL   = 60
STOP_SYNC_MIN_DELTA  = 0.002
STOP_CHECK_INTERVAL  = 45
DUST_USD             = 0.30

# ═══════════════════════════════════════════════════════════════
#  SIGNAL THRESHOLDS
# ═══════════════════════════════════════════════════════════════
RSI_OVERSOLD   = 35
RSI_OVERBOUGHT = 65
ADX_TRENDING   = 20
MIN_VOLUME_24H = 500_000

# ═══════════════════════════════════════════════════════════════
#  FEAR & GREED
# ═══════════════════════════════════════════════════════════════
FNG_MAX_SCORE     = 65
FNG_EXTREME_FEAR  = 30
FNG_CACHE_SECONDS = 3600

# ═══════════════════════════════════════════════════════════════
#  FUNDING RATE
# ═══════════════════════════════════════════════════════════════
FUNDING_NEGATIVE_BONUS   = -0.0001
FUNDING_POSITIVE_PENALTY =  0.0005
FUNDING_CACHE_SECONDS    = 300

# ═══════════════════════════════════════════════════════════════
#  TIME FILTER
# ═══════════════════════════════════════════════════════════════
USE_TIME_FILTER = False
AVOID_HOURS_UTC = {1, 4, 6, 9, 13, 14, 15, 22}

# ═══════════════════════════════════════════════════════════════
#  TIMING
# ═══════════════════════════════════════════════════════════════
LOOP_INTERVAL          = 15
COOLDOWN_PERIOD        = 180
HTF_REFRESH_INTERVAL   = 300
GHOST_CHECK_INTERVAL   = 60
MANUAL_CLOSE_THRESHOLD = 0.10
TG_POLL_INTERVAL       = 15

# ═══════════════════════════════════════════════════════════════
#  WEEKLY REPORT
# ═══════════════════════════════════════════════════════════════
WEEKLY_REPORT_DAY  = 4
WEEKLY_REPORT_HOUR = 18

# ═══════════════════════════════════════════════════════════════
#  FILES
# ═══════════════════════════════════════════════════════════════
STATE_FILE      = "bot_state_v83.json"
TRADE_LOG_FILE  = "elite_trades_v83.csv"
WALLET_LOG_FILE = "wallet_audit_v83.csv"   # NEW in v8.3.3

# ═══════════════════════════════════════════════════════════════
#  LOGGING
# ═══════════════════════════════════════════════════════════════
from logging.handlers import RotatingFileHandler
logging.root.handlers = []
_sh = logging.StreamHandler()
_sh.setLevel(logging.WARNING)          # stdout/nohup only gets warnings+ (was 148MB of INFO)
_fh = RotatingFileHandler("elite_bot.log", maxBytes=20 * 1024 * 1024, backupCount=3)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[_sh, _fh]
)
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════
#  GLOBAL STATE
# ═══════════════════════════════════════════════════════════════
daily_pnl           = 0.0
daily_trades        = 0
last_reset_date     = datetime.date.today()
trade_results       = deque(maxlen=200)
equity_curve        = deque(maxlen=500)
htf_cache           = {}
cb_triggered        = False
cb_reason           = ""
client              = None
fng_cache           = {"score": None, "label": None, "timestamp": 0}
funding_cache       = {}
btc_cache           = {"bias": None, "timestamp": 0}
last_ghost_check    = 0.0
last_tg_poll        = 0.0
consecutive_losses  = 0
last_weekly_report  = None
symbol_daily_losses = {}
weekly_pnl          = 0.0
weekly_trades       = 0
weekly_wins         = 0
weekly_losses       = 0
weekly_best_trade   = {"symbol": "", "pnl": 0.0}
weekly_worst_trade  = {"symbol": "", "pnl": 0.0}
daily_log           = {}
tg_max_daily_trades = MAX_DAILY_TRADES
tg_trading_paused   = False
tg_last_update_id   = 0

pnl_calendar        = {}
daily_wins          = 0
daily_losses        = 0
universe            = []
last_universe_build = 0.0
filter_rejects      = {}
corr_cache          = {}

# ── v8.3.3 additions ──
state_load_ok         = True   # False if load_state() hit an exception --
                                # forces a startup wallet audit instead of
                                # trusting an (possibly wrong) empty state
last_wallet_audit      = 0.0
# ── v8.4 globals ──
portfolio_size        = float(PORTFOLIO_SIZE)   # live equity used for sizing/risk (refresh_equity)
equity_peak           = 0.0
last_equity_refresh   = 0.0
dd_alerted            = False
last_backup           = 0.0
audit_alerted         = {}                      # currency -> last alert ts (alert-only mode)
WALLET_AUDIT_INTERVAL   = 300   # seconds between full-wallet untracked-holdings audits

_cycle_bumped = set()

def begin_cycle():
    """Called once per main-loop cycle so global gates only count once."""
    _cycle_bumped.clear()

def bump_filter(name, once_per_cycle=False):
    """Count a filter rejection so /filters shows the funnel."""
    if once_per_cycle:
        if name in _cycle_bumped:
            return
        _cycle_bumped.add(name)
    filter_rejects[name] = filter_rejects.get(name, 0) + 1

# ═══════════════════════════════════════════════════════════════
#  CLIENT INITIALIZATION
# ═══════════════════════════════════════════════════════════════
def initialize_client():
    global client
    api_key        = os.getenv("KUCOIN_API_KEY")
    api_secret     = os.getenv("KUCOIN_API_SECRET")
    api_passphrase = os.getenv("KUCOIN_API_PASSPHRASE")
    if not all([api_key, api_secret, api_passphrase]):
        raise ValueError("Missing API credentials in .env")
    if USE_OLD_API:
        client = Client(api_key, api_secret, api_passphrase)
    else:
        client = {
            "market": Market(key=api_key, secret=api_secret, passphrase=api_passphrase),
            "trade":  Trade(key=api_key,  secret=api_secret, passphrase=api_passphrase),
            "user":   User(key=api_key,   secret=api_secret, passphrase=api_passphrase),
        }
    logger.info("KuCoin client initialized")

try:
    initialize_client()
except Exception as e:
    logger.critical("Cannot start -- client init failed: {}".format(e))
    exit(1)

# ═══════════════════════════════════════════════════════════════
#  SIGNED RAW REQUESTS
# ═══════════════════════════════════════════════════════════════
def kucoin_signed_request(method, endpoint, body=None):
    api_key        = os.getenv("KUCOIN_API_KEY")
    api_secret     = os.getenv("KUCOIN_API_SECRET")
    api_passphrase = os.getenv("KUCOIN_API_PASSPHRASE")
    now_ms   = str(int(time.time() * 1000))
    body_str = json.dumps(body) if body else ""
    str_to_sign = now_ms + method.upper() + endpoint + body_str
    signature = base64.b64encode(
        hmac.new(api_secret.encode(), str_to_sign.encode(), hashlib.sha256).digest()
    ).decode()
    passphrase = base64.b64encode(
        hmac.new(api_secret.encode(), api_passphrase.encode(), hashlib.sha256).digest()
    ).decode()
    headers = {
        "KC-API-KEY":         api_key,
        "KC-API-SIGN":        signature,
        "KC-API-TIMESTAMP":   now_ms,
        "KC-API-PASSPHRASE":  passphrase,
        "KC-API-KEY-VERSION": "2",
        "Content-Type":       "application/json",
    }
    resp = requests.request(
        method.upper(), KC_BASE + endpoint, headers=headers,
        data=body_str if body else None, timeout=10)
    return resp.json()

# ═══════════════════════════════════════════════════════════════
#  UNIVERSE BUILDER
# ═══════════════════════════════════════════════════════════════
def build_universe():
    global universe, last_universe_build
    try:
        resp = requests.get(KC_BASE + "/api/v2/symbols", timeout=10).json()
        new_uni = []
        for s in resp.get("data", []):
            sym  = s.get("symbol", "")
            base = s.get("baseCurrency", "")
            if s.get("quoteCurrency") != QUOTE_CURRENCY:              continue
            if not s.get("enableTrading", False):                     continue
            if base in STABLE_BASES or base in EXCLUDE_BASES:         continue
            if any(base.endswith(suf) for suf in LEVERAGED_SUFFIXES): continue
            try:
                mn  = float(s.get("baseMinSize", 0)  or 0)
                inc = float(s.get("baseIncrement", 0) or 0)
                pin = float(s.get("priceIncrement", 0) or 0)
            except Exception:
                continue
            if inc <= 0 or pin <= 0:
                continue
            LOT_RULES[sym]        = (mn, inc)
            PRICE_INCREMENTS[sym] = pin
            new_uni.append({"symbol": sym, "base": base, "quote": QUOTE_CURRENCY})
        if new_uni:
            universe            = new_uni
            last_universe_build = time.time()
            logger.info("Universe built: {} tradeable {} pairs (precision rules loaded)".format(
                len(universe), QUOTE_CURRENCY))
    except Exception as e:
        logger.warning("Universe build failed, using fallback rules: {}".format(e))

def get_scan_list():
    core = [i["symbol"] for i in SYMBOLS]
    if not USE_DYNAMIC_UNIVERSE or not universe:
        return core
    try:
        data    = client["market"].get_all_tickers() if not USE_OLD_API else client.get_all_tickers()
        tickers = data.get("ticker", []) if isinstance(data, dict) else (data or [])
    except Exception as e:
        logger.error("Ticker bulk fetch failed: {}".format(e))
        return core
    usyms  = {u["symbol"] for u in universe}
    ranked = []
    for t in tickers:
        sym = t.get("symbol")
        if sym not in usyms or sym in core:
            continue
        try:
            vv = float(t.get("volValue", 0) or 0)
        except Exception:
            vv = 0
        if vv >= MIN_24H_DOLLAR_VOLUME:
            ranked.append((sym, vv))
    ranked.sort(key=lambda x: x[1], reverse=True)
    movers = [s for s, _ in ranked[:TOP_MOVERS_N]]
    return core + movers

def format_price(symbol, price):
    inc = PRICE_INCREMENTS.get(symbol)
    if not inc or inc <= 0:
        return "{:.6f}".format(price)
    ticks = math.floor(price / inc + 1e-9)
    p     = ticks * inc
    decimals = max(0, -int(math.floor(math.log10(inc)))) if inc < 1 else 0
    return "{:.{}f}".format(p, decimals)

# ═══════════════════════════════════════════════════════════════
#  PRICE SANITY CHECK
# ═══════════════════════════════════════════════════════════════
def sanitize_price(symbol, price):
    if symbol not in PRICE_SANITY:
        return price
    lo, hi = PRICE_SANITY[symbol]
    if lo <= price <= hi:
        return price
    for factor in [10000, 1000, 100]:
        corrected = price / factor
        if lo <= corrected <= hi:
            logger.warning("Price bug corrected for {}: {:.4f} -> {:.6f} (/{})".format(
                symbol, price, corrected, factor))
            return corrected
    logger.error("Cannot sanitize price for {}: {:.4f} (range {}-{})".format(
        symbol, price, lo, hi))
    return price

# ═══════════════════════════════════════════════════════════════
#  POSITION STATE
# ═══════════════════════════════════════════════════════════════
def make_state():
    return {
        "position":            None,
        "entry_price":         None,
        "entry_fill_price":    None,
        "entry_fee":           None,
        "original_size":       None,
        "remaining_size":      None,
        "funds_used":          None,
        "realized_usd":        0.0,
        "fees_usd":            0.0,
        "stop_loss":           None,
        "stop_order_id":       None,
        "exchange_stop_price": None,
        "last_stop_sync":      0.0,
        "last_stop_check":     0.0,
        "last_sell_fail_alert": 0.0,
        "tp1":                 None,
        "tp2":                 None,
        "tp3":                 None,
        "trailing_stop":       None,
        "tp1_hit":             False,
        "tp2_hit":             False,
        "highest_price":       None,
        "atr_at_entry":        None,
        "confidence":          None,
        "conf_breakdown":      None,
        "last_close_time":     None,
        "open_time":           None,
        "regime_at_entry":     None,
        "adopted":             False,  # v8.3.3: True if recovered by the
                                        # untracked-holdings audit rather than
                                        # opened normally -- entry is an ESTIMATE.
    }

positions = {info["symbol"]: make_state() for info in SYMBOLS}

# ═══════════════════════════════════════════════════════════════
#  STATE PERSISTENCE
# ═══════════════════════════════════════════════════════════════
def save_state():
    try:
        state = {
            "positions":          positions,
            "daily_pnl":          daily_pnl,
            "daily_trades":       daily_trades,
            "last_reset_date":    str(last_reset_date),
            "consecutive_losses": consecutive_losses,
            "symbol_daily_losses":symbol_daily_losses,
            "weekly_pnl":         weekly_pnl,
            "weekly_trades":      weekly_trades,
            "weekly_wins":        weekly_wins,
            "weekly_losses":      weekly_losses,
            "weekly_best_trade":  weekly_best_trade,
            "weekly_worst_trade": weekly_worst_trade,
            "daily_log":          daily_log,
            "tg_max_daily_trades":tg_max_daily_trades,
            "tg_last_update_id":  tg_last_update_id,
            "trade_results":      list(trade_results),
            "equity_curve":       list(equity_curve),
            "pnl_calendar":       pnl_calendar,
            "daily_wins":         daily_wins,
            "daily_losses":       daily_losses,
            "filter_rejects":     filter_rejects,
            "equity_peak":        equity_peak,
        }
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        logger.warning("State save failed: {}".format(e))

def load_state():
    global positions, daily_pnl, daily_trades, last_reset_date
    global consecutive_losses, symbol_daily_losses
    global weekly_pnl, weekly_trades, weekly_wins, weekly_losses
    global weekly_best_trade, weekly_worst_trade, daily_log
    global tg_max_daily_trades, tg_last_update_id
    global trade_results, equity_curve
    global pnl_calendar, daily_wins, daily_losses, filter_rejects
    global state_load_ok, equity_peak

    if not os.path.exists(STATE_FILE):
        # v8.3.3: a missing state file is itself worth flagging loudly --
        # if this VM has ever traded before, real holdings may now be
        # completely untracked. Force the caller to run a wallet audit.
        logger.warning("No state file found ({}) -- starting fresh. If this "
                       "VM has traded before, real holdings may be untracked "
                       "-- startup audit will check.".format(STATE_FILE))
        state_load_ok = False
        return
    try:
        with open(STATE_FILE, "r") as f:
            state = json.load(f)
        for sym, s in state.get("positions", {}).items():
            positions.setdefault(sym, make_state()).update(s)
        if state.get("last_reset_date") == str(datetime.date.today()):
            daily_pnl           = state.get("daily_pnl", 0.0)
            daily_trades        = state.get("daily_trades", 0)
            consecutive_losses  = state.get("consecutive_losses", 0)
            symbol_daily_losses = state.get("symbol_daily_losses", {})
            tg_max_daily_trades = state.get("tg_max_daily_trades", MAX_DAILY_TRADES)
            daily_wins          = state.get("daily_wins", 0)
            daily_losses        = state.get("daily_losses", 0)
            filter_rejects      = state.get("filter_rejects", {})
        tg_last_update_id  = state.get("tg_last_update_id", 0)
        equity_peak        = float(state.get("equity_peak", 0.0) or 0.0)
        weekly_pnl         = state.get("weekly_pnl", 0.0)
        weekly_trades      = state.get("weekly_trades", 0)
        weekly_wins        = state.get("weekly_wins", 0)
        weekly_losses      = state.get("weekly_losses", 0)
        weekly_best_trade  = state.get("weekly_best_trade", {"symbol": "", "pnl": 0.0})
        weekly_worst_trade = state.get("weekly_worst_trade", {"symbol": "", "pnl": 0.0})
        daily_log          = state.get("daily_log", {})
        pnl_calendar       = state.get("pnl_calendar", {})
        trade_results      = deque(state.get("trade_results", []), maxlen=200)
        eq_raw             = state.get("equity_curve", [])
        if eq_raw and max(eq_raw) < 2.0:
            eq_raw = [v * PORTFOLIO_SIZE for v in eq_raw]
        equity_curve       = deque(eq_raw, maxlen=500)
        state_load_ok       = True
        logger.info("State restored -- PnL: {:.2f}% | Streak: {} | History: {} trades".format(
            daily_pnl * 100, consecutive_losses, len(trade_results)))
    except Exception as e:
        # v8.3.3: this used to just warn and silently continue with
        # positions == defaults (i.e. "no open positions"). If the bot
        # actually HAD open positions on the exchange at that moment,
        # they become true ghosts. state_load_ok=False forces an
        # immediate full-wallet audit in main() instead of trusting
        # the empty position dict.
        logger.error("STATE LOAD FAILED -- treating as UNKNOWN holdings, not empty: {}".format(e))
        state_load_ok = False

# ═══════════════════════════════════════════════════════════════
#  TELEGRAM
# ═══════════════════════════════════════════════════════════════
def send_telegram(msg):
    token   = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return
    try:
        requests.post(
            "https://api.telegram.org/bot{}/sendMessage".format(token),
            data={"chat_id": chat_id, "text": msg},
            timeout=8,
        )
    except Exception as e:
        logger.warning("Telegram send failed: {}".format(e))

def handle_telegram_command(text):
    global tg_max_daily_trades, tg_trading_paused, cb_triggered, cb_reason
    global equity_peak, consecutive_losses, dd_alerted
    text = text.strip().lower()

    if text == "/help":
        send_telegram(
            "Elite Bot v8.4 Commands\n\n"
            "/status - bot overview\n"
            "/positions - open positions detail\n"
            "/scan - top opportunities now\n"
            "/risk - current risk exposure\n"
            "/performance - win rate and stats\n"
            "/calendar - daily PnL history\n"
            "/filters - today's filter rejection funnel\n"
            "/audit - full wallet vs tracked-positions check\n"
            "/close SYMBOL - force-close/clear a position\n"
            "/trades N - set max daily trades\n"
            "/stop - pause entries\n"
            "/resume - resume entries\n"
            "/coins - scan list + status"
        )

    elif text == "/status":
        usdt_bal    = get_balance("USDT")
        fng, fl     = get_fear_and_greed()
        btc_bias    = get_btc_bias()
        regime      = get_market_regime()
        perf        = calculate_performance()
        open_count  = open_position_count()
        exposure    = total_portfolio_heat() * 100
        send_telegram(
            "ELITE BOT v8.4 STATUS\n\n"
            "Trading: {}\n"
            "Balance: ${:.2f} USDT\n"
            "Open Positions: {}/{}\n"
            "Exposure: {:.1f}%\n"
            "Today PnL: {:.2f}% ({}/{})\n"
            "Loss streak: {}\n\n"
            "Market Regime: {}\n"
            "BTC: {}\n"
            "Fear+Greed: {}/100 ({})\n\n"
            "Win Rate: {:.1f}% ({} trades)\n"
            "Profit Factor: {:.2f}".format(
                "PAUSED" if tg_trading_paused else "ACTIVE",
                usdt_bal,
                open_count, MAX_OPEN_POSITIONS,
                exposure,
                daily_pnl * 100, daily_trades, tg_max_daily_trades,
                consecutive_losses,
                regime, btc_bias,
                fng, fl,
                perf.get("win_rate", 0), perf.get("trades", 0),
                perf.get("profit_factor", 0),
            )
        )

    elif text == "/positions":
        lines = []
        for sym in [s for s in positions if positions[s].get("position")]:
            state = positions[sym]
            base_cur = sym.split("-")[0]
            entry = state["entry_fill_price"] or state["entry_price"]
            try:
                ticker = client["market"].get_ticker(sym) if not USE_OLD_API else client.get_ticker(sym)
                price  = sanitize_price(sym, float(ticker.get("price", entry)))
                pnl    = (price - entry) / entry * 100
                time_open = (time.time() - state["open_time"]) / 3600 if state["open_time"] else 0
                lines.append(
                    "{}{}\nFill: ${:.6f} | Now: ${:.6f}\n"
                    "Unrealized: {:.2f}% | Banked: ${:.3f}\n"
                    "Remaining: {:.4f} {} | Fees: ${:.3f}\n"
                    "SL: ${:.6f} ({}) | TP1: ${:.6f}\n"
                    "Conf: {} | Regime: {}\n"
                    "Open: {:.1f}h".format(
                        sym, " [ADOPTED -- estimated entry]" if state.get("adopted") else "",
                        entry, price,
                        pnl, state.get("realized_usd") or 0,
                        state.get("remaining_size") or 0, base_cur,
                        state.get("fees_usd") or 0,
                        state["stop_loss"],
                        "on-exchange" if state.get("stop_order_id") else "SOFTWARE ONLY",
                        state["tp1"],
                        state["confidence"], state.get("regime_at_entry", "N/A"),
                        time_open,
                    )
                )
            except Exception:
                lines.append("{}: open @ ${:.6f}".format(sym, entry or 0))
        send_telegram("OPEN POSITIONS\n\n" + ("\n\n".join(lines) if lines else "No open positions"))

    elif text == "/scan":
        send_telegram("Scanning markets... (check log in ~30s)")
        results = []
        for sym in get_scan_list():
            try:
                df = get_candles(sym)
                if df is None or len(df) < 60:
                    continue
                df = add_indicators(df)
                regime   = detect_regime(df)
                htf_bias = get_htf_bias(sym)
                conf, reasons, breakdown = calculate_confidence_weighted(df, sym, regime, htf_bias)
                if conf >= 50:
                    results.append((sym, conf, reasons[:3]))
            except Exception:
                pass
        results.sort(key=lambda x: x[1], reverse=True)
        lines = ["TOP OPPORTUNITIES\n"]
        for sym, conf, reasons in results[:5]:
            lines.append("{}\nScore: {}/100\n{}\n".format(
                sym, conf, "\n".join(reasons[:3])))
        send_telegram("\n".join(lines) if len(lines) > 1 else "No strong setups right now")

    elif text == "/risk":
        heat     = total_portfolio_heat() * 100
        usdt_bal = get_balance("USDT")
        open_pos = [(s, positions[s]) for s in positions if positions[s]["position"]]
        lines    = ["RISK EXPOSURE\n\n"
                    "Portfolio Heat: {:.1f}% / {:.0f}%\n"
                    "USDT Available: ${:.2f}\n"
                    "Open Trades: {}/{}\n"
                    "Daily Loss Used: {:.2f}% / {:.0f}%\n"
                    "Consecutive Losses: {}/{}".format(
                        heat, MAX_PORTFOLIO_HEAT*100,
                        usdt_bal,
                        len(open_pos), MAX_OPEN_POSITIONS,
                        abs(min(daily_pnl*100, 0)), abs(MAX_DAILY_LOSS*100),
                        consecutive_losses, MAX_CONSECUTIVE_LOSSES,
                    )]
        for sym, state in open_pos:
            entry = state["entry_fill_price"] or state["entry_price"]
            if entry and state["stop_loss"]:
                risk_pct = abs(entry - state["stop_loss"]) / entry * 100
                sl_kind  = "exchange" if state.get("stop_order_id") else "software"
                lines.append("\n{}: risk {:.2f}% ({} SL)".format(sym, risk_pct, sl_kind))
        send_telegram("\n".join(lines))

    elif text == "/performance":
        perf = calculate_performance()
        if not perf:
            send_telegram("No completed trades yet")
            return
        send_telegram(
            "PERFORMANCE STATS\n\n"
            "Total Trades: {}\n"
            "Win Rate: {:.1f}%\n"
            "Profit Factor: {:.2f}\n"
            "Avg Win: +{:.3f}%\n"
            "Avg Loss: {:.3f}%\n"
            "Sharpe Ratio: {:.2f}\n"
            "Max Drawdown: {:.2f}%\n"
            "Total PnL: {:.2f}%\n\n"
            "Weekly PnL: {:.2f}%\n"
            "This week trades: {}".format(
                perf.get("trades",0),
                perf.get("win_rate",0),
                perf.get("profit_factor",0),
                perf.get("avg_win_pct",0),
                perf.get("avg_loss_pct",0),
                perf.get("sharpe",0),
                perf.get("max_drawdown",0),
                perf.get("total_pnl_pct",0),
                weekly_pnl*100,
                weekly_trades,
            )
        )

    elif text == "/coins":
        core = {i["symbol"] for i in SYMBOLS}
        scan = get_scan_list()
        open_syms = [s for s in positions if positions[s].get("position")]
        lines = ["SCAN LIST ({} core + {} movers)\n".format(
            len(core), max(0, len(scan) - len(core)))]
        for sym in list(dict.fromkeys(scan + open_syms)):
            dl  = symbol_daily_losses.get(sym, 0)
            st  = positions.get(sym)
            has_pos = bool(st and st.get("position"))
            status = "IN TRADE" if has_pos else ("BLOCKED" if dl >= MAX_SYMBOL_DAILY_LOSSES else "ready")
            tag = "core" if sym in core else "mover"
            lines.append("{} [{}]: {}".format(sym, tag, status))
        send_telegram("\n".join(lines))

    elif text == "/calendar":
        today  = str(datetime.date.today())
        merged = dict(pnl_calendar)
        merged[today] = {"pnl": daily_pnl, "trades": daily_trades,
                         "wins": daily_wins, "losses": daily_losses, "live": True}
        keys = sorted(merged.keys())[-30:]
        if not keys:
            send_telegram("No PnL history yet"); return
        lines = ["PNL CALENDAR (last {} days)\n".format(len(keys))]
        cur_month = today[:7]; mtd = 0.0; best = worst = None
        for k in keys:
            d    = merged[k]
            sign = "+" if d["pnl"] >= 0 else ""
            star = " *live" if d.get("live") else ""
            wl   = " ({}W {}L)".format(d.get("wins", 0), d.get("losses", 0)) if d.get("trades", 0) else ""
            lines.append("{}  {}{:.2f}%  {}t{}{}".format(
                k, sign, d["pnl"] * 100, d.get("trades", 0), wl, star))
            if k[:7] == cur_month: mtd += d["pnl"]
            if best  is None or d["pnl"] > merged[best]["pnl"]:  best  = k
            if worst is None or d["pnl"] < merged[worst]["pnl"]: worst = k
        total = sum(merged[k]["pnl"] for k in keys)
        lines.append("\nMonth-to-date: {:+.2f}%".format(mtd * 100))
        lines.append("Shown total:   {:+.2f}%".format(total * 100))
        lines.append("Best:  {} {:+.2f}%".format(best,  merged[best]["pnl"] * 100))
        lines.append("Worst: {} {:+.2f}%".format(worst, merged[worst]["pnl"] * 100))
        send_telegram("\n".join(lines))

    elif text == "/filters":
        if not filter_rejects:
            send_telegram("No filter rejections recorded today yet")
            return
        total = sum(filter_rejects.values())
        lines = ["FILTER FUNNEL today ({} rejections)\n".format(total)]
        for name, cnt in sorted(filter_rejects.items(), key=lambda x: -x[1]):
            pct = cnt / total * 100 if total else 0
            lines.append("{}: {} ({:.0f}%)".format(name, cnt, pct))
        lines.append("\nEntries today: {}".format(daily_trades))
        lines.append("The top line is the gate strangling trade flow.")
        send_telegram("\n".join(lines))

    elif text == "/audit":
        send_telegram("Running full wallet audit (checking every balance against tracked positions)...")
        report = audit_untracked_holdings(force=True, notify_if_clean=True)
        send_telegram(report)

    elif text.startswith("/close"):
        parts = text.split()
        if len(parts) != 2:
            send_telegram("Usage: /close ZEC-USDT (or /close zec)")
            return
        raw = parts[1].upper()
        sym = raw if "-" in raw else raw + "-" + QUOTE_CURRENCY
        state = positions.get(sym)
        if not state or not state.get("position"):
            send_telegram("{}: no open position tracked".format(sym))
            return
        info = {"symbol": sym, "base": sym.split("-")[0], "quote": QUOTE_CURRENCY}
        if state.get("stop_order_id"):
            cancel_exchange_stop(state["stop_order_id"])
            state["stop_order_id"] = None
            state["exchange_stop_price"] = None
        bal      = get_balance(info["base"])
        sellable = adjust_size_to_lot(sym, bal)
        try:
            ticker = client["market"].get_ticker(sym) if not USE_OLD_API else client.get_ticker(sym)
            px = sanitize_price(sym, float(ticker.get("price", 0)))
        except Exception:
            px = state.get("entry_fill_price") or 0
        if sellable > 0 and px and sellable * px >= DUST_USD:
            fill = execute_market_sell(sym, sellable, px)
            if fill:
                send_telegram("Force-closing {} -- sold {:.6f} @ ${:.6f}".format(
                    sym, fill["size"], fill["avg_price"]))
                finalize_close(sym, state, fill["size"], fill["avg_price"],
                               fill["fee"], "Manual /close command")
            else:
                send_telegram("{}: market sell FAILED -- check exchange manually".format(sym))
        else:
            verify_position_holdings(sym, info, state, price_hint=px or None, force=True)
            send_telegram("{}: nothing sellable (dust/empty) -- position finalized and cleared".format(sym))

    elif text.startswith("/trades"):
        parts = text.split()
        if len(parts) == 2 and parts[1].isdigit():
            n = int(parts[1])
            if 1 <= n <= 20:
                tg_max_daily_trades = n
                save_state()
                send_telegram("Max daily trades set to {}".format(n))
            else:
                send_telegram("Use 1-20")
        else:
            send_telegram("Usage: /trades 10\nCurrent: {}".format(tg_max_daily_trades))

    elif text == "/stop":
        tg_trading_paused = True
        send_telegram("Bot PAUSED -- open positions still managed\nSend /resume to restart")

    elif text == "/resume":
        tg_trading_paused = False
        cb_triggered      = False
        cb_reason         = ""
        consecutive_losses = 0
        equity_peak       = portfolio_size   # reset drawdown baseline
        dd_alerted        = False
        send_telegram("Bot RESUMED -- trades {}/{}".format(daily_trades, tg_max_daily_trades))

    else:
        send_telegram("Unknown command. Send /help")

def poll_telegram_commands():
    global tg_last_update_id, last_tg_poll
    now = time.time()
    if now - last_tg_poll < TG_POLL_INTERVAL:
        return
    last_tg_poll = now
    token   = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return
    try:
        resp = requests.get(
            "https://api.telegram.org/bot{}/getUpdates".format(token),
            params={"offset": tg_last_update_id + 1, "timeout": 0},
            timeout=5,
        )
        for update in resp.json().get("result", []):
            tg_last_update_id = update["update_id"]
            msg  = update.get("message", {})
            if str(msg.get("chat", {}).get("id", "")) != str(chat_id):
                continue
            text = msg.get("text", "")
            if text.startswith("/"):
                logger.info("Telegram command: {}".format(text))
                handle_telegram_command(text)
    except Exception as e:
        logger.warning("Telegram poll error: {}".format(e))

# ═══════════════════════════════════════════════════════════════
#  WEEKLY REPORT
# ═══════════════════════════════════════════════════════════════
def check_weekly_report():
    global last_weekly_report
    global weekly_pnl, weekly_trades, weekly_wins, weekly_losses
    global weekly_best_trade, weekly_worst_trade, daily_log

    now   = datetime.datetime.utcnow()
    today = datetime.date.today()
    if now.weekday() != WEEKLY_REPORT_DAY: return
    if now.hour != WEEKLY_REPORT_HOUR:     return
    if last_weekly_report == today:        return
    last_weekly_report = today

    win_rate  = (weekly_wins / weekly_trades * 100) if weekly_trades > 0 else 0
    day_lines = ""
    for d_str in sorted(daily_log.keys()):
        d    = daily_log[d_str]
        sign = "+" if d["pnl"] >= 0 else ""
        day_lines += "{}{} {:.2f}% | {} trades ({}W {}L)\n".format(
            sign, d_str, d["pnl"] * 100, d["trades"], d["wins"], d["losses"])

    send_telegram(
        "WEEKLY REPORT {}\n\n"
        "PnL: {:.2f}%\n"
        "Trades: {} | W:{} L:{} | WR:{:.1f}%\n"
        "Best: {} +{:.2f}%\n"
        "Worst: {} {:.2f}%\n\n"
        "DAY BY DAY:\n{}".format(
            today, weekly_pnl * 100,
            weekly_trades, weekly_wins, weekly_losses, win_rate,
            weekly_best_trade.get("symbol","N/A"), weekly_best_trade.get("pnl",0)*100,
            weekly_worst_trade.get("symbol","N/A"), weekly_worst_trade.get("pnl",0)*100,
            day_lines or "No trades",
        )
    )
    weekly_pnl = 0.0; weekly_trades = 0; weekly_wins = 0; weekly_losses = 0
    weekly_best_trade = {"symbol": "", "pnl": 0.0}
    weekly_worst_trade = {"symbol": "", "pnl": 0.0}
    daily_log = {}
    save_state()

# ═══════════════════════════════════════════════════════════════
#  EXTERNAL DATA
# ═══════════════════════════════════════════════════════════════
def get_fear_and_greed():
    now = time.time()
    if fng_cache["score"] is not None and (now - fng_cache["timestamp"]) < FNG_CACHE_SECONDS:
        return fng_cache["score"], fng_cache["label"]
    try:
        resp  = requests.get("https://api.alternative.me/fng/?limit=1", timeout=8)
        score = int(resp.json()["data"][0]["value"])
        label = resp.json()["data"][0]["value_classification"]
        fng_cache.update({"score": score, "label": label, "timestamp": now})
        return score, label
    except Exception:
        return fng_cache.get("score") or 50, fng_cache.get("label") or "Neutral"

def get_funding_rate(symbol):
    now   = time.time()
    cache = funding_cache.get(symbol)
    if cache and (now - cache["timestamp"]) < FUNDING_CACHE_SECONDS:
        return cache["rate"]
    try:
        futures_symbol = symbol.replace("-", "") + "M"
        resp = requests.get(
            "https://api-futures.kucoin.com/api/v1/funding-rate/{}/current".format(futures_symbol),
            timeout=8)
        rate = float(resp.json()["data"]["value"])
        funding_cache[symbol] = {"rate": rate, "timestamp": now}
        return rate
    except Exception:
        return 0.0

# ═══════════════════════════════════════════════════════════════
#  TIME FILTER
# ═══════════════════════════════════════════════════════════════
def is_good_trading_time():
    if not USE_TIME_FILTER:
        return True
    hour = datetime.datetime.utcnow().hour
    if hour in AVOID_HOURS_UTC:
        logger.info("Blocked UTC {}:xx (historically unprofitable)".format(hour))
        return False
    return True

# ═══════════════════════════════════════════════════════════════
#  5-STATE MARKET REGIME
# ═══════════════════════════════════════════════════════════════
def get_market_regime():
    try:
        klines = client["market"].get_kline("BTC-USDT", "1hour") if not USE_OLD_API else client.get_kline_data("BTC-USDT", "1hour")
        df = pd.DataFrame(klines)
        df.columns = ["time", "open", "close", "high", "low", "volume", "turnover"]
        df = df.astype(float).sort_values("time").tail(50)
        close = df["close"]

        ema50     = EMAIndicator(close, window=50).ema_indicator().iloc[-1]
        ema200    = EMAIndicator(close, window=200).ema_indicator().iloc[-1] if len(df) >= 200 else ema50
        rsi       = RSIIndicator(close, window=14).rsi().iloc[-1]
        macd_diff = MACD(close).macd_diff().iloc[-1]
        atr_pct   = AverageTrueRange(df["high"], df["low"], close, window=14).average_true_range().iloc[-1] / close.iloc[-1]
        bb_width  = (BollingerBands(close, window=20).bollinger_hband().iloc[-1] -
                     BollingerBands(close, window=20).bollinger_lband().iloc[-1]) / close.iloc[-1]

        if atr_pct > 0.03 or bb_width > 0.08:
            return "HIGH_VOLATILITY"

        bull_signals = sum([
            close.iloc[-1] > ema50,
            close.iloc[-1] > ema200,
            rsi > 55,
            macd_diff > 0,
        ])

        if bull_signals == 4:   return "STRONG_BULL"
        elif bull_signals >= 3: return "BULL"
        elif bull_signals <= 1: return "BEAR"
        else:                   return "SIDEWAYS"

    except Exception:
        return "SIDEWAYS"

def get_btc_bias():
    now = time.time()
    if btc_cache["bias"] is not None and (now - btc_cache["timestamp"]) < 300:
        return btc_cache["bias"]
    try:
        regime = get_market_regime()
        if regime in ("STRONG_BULL", "BULL"):   bias = "BULLISH"
        elif regime == "BEAR":                  bias = "BEARISH"
        else:                                   bias = "NEUTRAL"
        btc_cache.update({"bias": bias, "timestamp": now})
        return bias
    except Exception:
        return "NEUTRAL"

# ═══════════════════════════════════════════════════════════════
#  LOT SIZE
# ═══════════════════════════════════════════════════════════════
def adjust_size_to_lot(symbol, size):
    min_qty, increment = LOT_RULES.get(symbol, (0.001, 0.001))
    adjusted = math.floor(size / increment + 1e-9) * increment
    adjusted = round(adjusted, 8)
    if adjusted < min_qty:
        return 0.0
    return adjusted

# ═══════════════════════════════════════════════════════════════
#  FILL DETAILS — real prices & fees from the exchange
# ═══════════════════════════════════════════════════════════════
def get_fill_details(order_id, retries=6):
    """
    Fetch actual execution details for a filled order.
    Returns {"avg_price", "size", "funds", "fee"} or None.
    v8.3.3: also used for triggered STOP orders -- KuCoin gives
    stop orders a regular orderId once triggered, so the same
    lookup works for those too.
    """
    if not order_id:
        return None
    for attempt in range(retries):
        try:
            if USE_OLD_API:
                od = client.get_order(order_id)
            else:
                od = client["trade"].get_order_details(order_id)
            deal_size  = float(od.get("dealSize") or 0)
            deal_funds = float(od.get("dealFunds") or 0)
            fee        = float(od.get("fee") or 0)
            if deal_size > 0 and deal_funds > 0:
                return {
                    "avg_price": deal_funds / deal_size,
                    "size":      deal_size,
                    "funds":     deal_funds,
                    "fee":       fee,
                }
        except Exception as e:
            logger.warning("Fill fetch attempt {} failed [{}]: {}".format(
                attempt + 1, order_id, str(e)[:80]))
        time.sleep(0.5)
    logger.error("Could not fetch fills for order {} -- falling back to estimates".format(order_id))
    return None

def extract_order_id(order):
    if isinstance(order, dict):
        return order.get("orderId") or order.get("data", {}).get("orderId")
    return None

# ═══════════════════════════════════════════════════════════════
#  EXCHANGE-SIDE STOP ORDERS
# ═══════════════════════════════════════════════════════════════
def place_exchange_stop(symbol, size, stop_price):
    size = adjust_size_to_lot(symbol, size)
    if size <= 0:
        return None
    body = {
        "clientOid": str(uuid.uuid4()),
        "side":      "sell",
        "symbol":    symbol,
        "type":      "market",
        "stop":      "loss",
        "stopPrice": format_price(symbol, stop_price),
        "size":      "{:.8f}".format(size).rstrip("0").rstrip("."),
        "tradeType": "TRADE",
    }
    try:
        resp = kucoin_signed_request("POST", "/api/v1/stop-order", body)
        if resp.get("code") == "200000":
            oid = resp.get("data", {}).get("orderId")
            logger.info("Exchange stop placed [{}] size {} @ {} (id {})".format(
                symbol, body["size"], body["stopPrice"], oid))
            return oid
        logger.error("Stop order rejected [{}]: {}".format(symbol, str(resp)[:150]))
    except Exception as e:
        logger.error("Stop order error [{}]: {}".format(symbol, str(e)[:100]))
    return None

def cancel_exchange_stop(order_id):
    if not order_id:
        return True
    try:
        resp = kucoin_signed_request("DELETE", "/api/v1/stop-order/" + order_id)
        return resp.get("code") == "200000"
    except Exception as e:
        logger.warning("Stop cancel failed [{}]: {}".format(order_id, str(e)[:80]))
        return False

def get_stop_order_status(order_id):
    try:
        resp = kucoin_signed_request("GET", "/api/v1/stop-order/" + order_id)
        if resp.get("code") == "200000":
            return resp.get("data", {}).get("status")
        return None
    except Exception:
        return "UNKNOWN"

def sync_stop_order(symbol, state, new_stop, size, force=False):
    now = time.time()
    if not force:
        if now - (state.get("last_stop_sync") or 0) < STOP_SYNC_INTERVAL:
            return
        old = state.get("exchange_stop_price") or 0
        if old > 0 and abs(new_stop - old) / old < STOP_SYNC_MIN_DELTA:
            return
    if state.get("stop_order_id"):
        cancel_exchange_stop(state["stop_order_id"])
        state["stop_order_id"] = None
        state["exchange_stop_price"] = None
    oid = place_exchange_stop(symbol, size, new_stop)
    state["stop_order_id"]       = oid
    state["exchange_stop_price"] = new_stop if oid else None
    state["last_stop_sync"]      = now
    if oid is None:
        send_telegram("WARNING {} -- exchange stop could not be placed.\n"
                      "Running on SOFTWARE stop only until next sync.".format(symbol))
    save_state()

# ═══════════════════════════════════════════════════════════════
#  GHOST POSITION DETECTION (tracked positions only)
# ═══════════════════════════════════════════════════════════════
def check_for_ghost_positions():
    global last_ghost_check
    now = time.time()
    if now - last_ghost_check < GHOST_CHECK_INTERVAL:
        return
    last_ghost_check = now
    for symbol in [s for s in list(positions.keys()) if positions[s].get("position")]:
        info = {"symbol": symbol, "base": symbol.split("-")[0], "quote": QUOTE_CURRENCY}
        try:
            verify_position_holdings(symbol, info, positions[symbol])
        except Exception as e:
            logger.warning("Holdings verify error [{}]: {}".format(symbol, str(e)[:100]))

# ═══════════════════════════════════════════════════════════════
#  UNTRACKED HOLDINGS AUDIT (NEW in v8.3.3)
#
#  check_for_ghost_positions() above only looks at symbols the bot
#  currently BELIEVES are open. If state was ever lost (load_state
#  exception, corrupted/missing JSON) while real coins were held,
#  those coins become invisible to every other safety mechanism in
#  this file -- no stop resync, no verifier coverage, no exit ever
#  logged. This is very likely what happened to TAO-USDT in the
#  v8.3.2 log: two OPENs, zero exits, ever.
#
#  This pulls EVERY non-zero balance from the account directly and
#  flags/adopts anything that isn't a currently-tracked position.
# ═══════════════════════════════════════════════════════════════
def _log_wallet_audit_row(currency, qty, est_usd, tracked, action):
    row = {
        "timestamp": datetime.datetime.now().isoformat(),
        "currency":  currency,
        "qty":       qty,
        "est_usd":   round(est_usd, 4),
        "tracked":   tracked,
        "action":    action,
    }
    write_header = (not os.path.exists(WALLET_LOG_FILE)) or os.path.getsize(WALLET_LOG_FILE) == 0
    with open(WALLET_LOG_FILE, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=row.keys())
        if write_header:
            writer.writeheader()
        writer.writerow(row)

def audit_untracked_holdings(force=False, notify_if_clean=False):
    """
    Compare every non-USDT balance on the account against the
    positions this process currently tracks. Anything untracked
    above DUST_USD gets:
      1. logged to wallet_audit_v83.csv (paper trail independent
         of the trade log / state file),
      2. an immediate Telegram alert,
      3. "adopted" -- given a tracked position with a protective
         stop-loss placed immediately, so it's no longer naked --
         entry price is an ESTIMATE (current price), flagged as
         adopted everywhere it's displayed.
    Returns a human-readable summary string.
    """
    global last_wallet_audit
    now = time.time()
    if not force and (now - last_wallet_audit) < WALLET_AUDIT_INTERVAL:
        return ""
    last_wallet_audit = now

    try:
        accounts = client["user"].get_account_list() if not USE_OLD_API else client.get_accounts()
    except Exception as e:
        logger.error("Wallet audit: could not fetch accounts: {}".format(e))
        return "Wallet audit failed: could not fetch accounts ({})".format(str(e)[:80])

    tracked_bases = {sym.split("-")[0] for sym, st in positions.items() if st.get("position")}
    findings = []

    for acc in accounts:
        try:
            if acc.get("type") != "trade":
                continue
            currency = acc.get("currency")
            qty      = float(acc.get("available", 0) or 0)
        except Exception:
            continue
        if not currency or currency == "USDT" or qty <= 0:
            continue
        symbol = "{}-USDT".format(currency)

        try:
            t  = client["market"].get_ticker(symbol) if not USE_OLD_API else client.get_ticker(symbol)
            px = sanitize_price(symbol, float(t.get("price", 0) or 0))
        except Exception:
            px = 0
        est_usd = qty * px

        if currency in tracked_bases:
            continue
        if est_usd < DUST_USD:
            continue

        if not ADOPT_UNTRACKED:
            # v8.4: the bot never trades coins it didn't open (v8.3.3 sold the user's own
            # HOME/HYPE this way). Alert once per 24h per coin and leave it alone.
            if now - audit_alerted.get(currency, 0) > 86400:
                audit_alerted[currency] = now
                logger.warning("Untracked holding left untouched (adoption OFF): {:.8f} {} (~${:.2f})".format(
                    qty, currency, est_usd))
                _log_wallet_audit_row(currency, qty, est_usd, tracked=False, action="alert_only")
                findings.append("{}: {:.8f} (~${:.2f}) is not a bot position -- left untouched.".format(
                    currency, qty, est_usd))
            continue

        logger.error("UNTRACKED HOLDING: {:.8f} {} (~${:.2f}) -- not in tracked positions".format(
            qty, currency, est_usd))
        _log_wallet_audit_row(currency, qty, est_usd, tracked=False, action="found_untracked")

        adopted = False
        if px > 0:
            state = positions.setdefault(symbol, make_state())
            sl_pct = SYMBOL_MAX_SL.get(symbol, MAX_SL_PCT)
            stop_loss = px * (1 - sl_pct)
            state.update({
                "position":         "long",
                "entry_price":      px,
                "entry_fill_price": px,       # ESTIMATE -- real entry unknown
                "entry_fee":        0.0,
                "original_size":    qty,
                "remaining_size":   qty,
                "funds_used":       est_usd,
                "realized_usd":     0.0,
                "fees_usd":         0.0,
                "highest_price":    px,
                "stop_loss":        stop_loss,
                "tp1":              px * 1.02,
                "tp2":              px * 1.035,
                "tp3":              px * 1.06,
                "open_time":        now,
                "confidence":       None,
                "adopted":          True,
            })
            sellable = adjust_size_to_lot(symbol, qty)
            if sellable > 0:
                sync_stop_order(symbol, state, stop_loss, sellable, force=True)
                adopted = True
        _log_wallet_audit_row(currency, qty, est_usd, tracked=False,
                              action="adopted_with_stop" if adopted else "adopt_failed_no_price")

        findings.append(
            "{}: {:.8f} (~${:.2f}) -- was UNTRACKED. {}".format(
                currency, qty, est_usd,
                "Adopted, protective stop placed at -{:.1f}%.".format(sl_pct*100) if adopted
                else "Could not price it -- check manually NOW."
            )
        )

    save_state()
    if findings:
        report = "WALLET AUDIT -- {} untracked holding(s) found:\n\n{}".format(
            len(findings), "\n\n".join(findings))
        send_telegram(report)
        return report
    if notify_if_clean:
        return "Wallet audit clean -- every non-dust balance matches a tracked position."
    return ""

# ═══════════════════════════════════════════════════════════════
#  DATA FETCHING
# ═══════════════════════════════════════════════════════════════
def get_candles(symbol, interval="5min", limit=200):
    try:
        klines = client["market"].get_kline(symbol, interval) if not USE_OLD_API else client.get_kline_data(symbol, interval)
        if not klines:
            return None
        df = pd.DataFrame(klines)
        if USE_OLD_API:
            df["time"]   = df[0].astype(float)
            df["open"]   = df[1].astype(float)
            df["close"]  = df[2].astype(float)
            df["high"]   = df[3].astype(float)
            df["low"]    = df[4].astype(float)
            df["volume"] = df[5].astype(float)
        else:
            df.columns = ["time", "open", "close", "high", "low", "volume", "turnover"]
            df = df.astype(float)
        df = df.sort_values("time").reset_index(drop=True)
        sample_price = df["close"].iloc[-1]
        corrected    = sanitize_price(symbol, sample_price)
        if corrected != sample_price:
            factor = sample_price / corrected
            for col in ["open", "close", "high", "low"]:
                df[col] = df[col] / factor
        return df.tail(limit)
    except Exception as e:
        err = str(e)
        if "429" in err:
            time.sleep(10)
        else:
            logger.error("Candle fetch error [{} {}]: {}".format(symbol, interval, err[:100]))
        return None

def get_htf_candles(symbol):
    now   = time.time()
    cache = htf_cache.get(symbol)
    if cache and (now - cache["timestamp"]) < HTF_REFRESH_INTERVAL:
        return cache["df"]
    df = get_candles(symbol, interval="1hour", limit=100)
    if df is not None:
        htf_cache[symbol] = {"df": df, "timestamp": now}
    return df

def get_24h_volume(symbol):
    try:
        stats = client["market"].get_24h_stats(symbol) if not USE_OLD_API else client.get_24hr_stats(symbol)
        return float(stats.get("volValue", 0))
    except Exception:
        return 0

def get_balance(currency):
    try:
        accounts = client["user"].get_account_list() if not USE_OLD_API else client.get_accounts()
        for acc in accounts:
            if acc["currency"] == currency and acc["type"] == "trade":
                return float(acc["available"])
    except Exception as e:
        logger.error("Balance error [{}]: {}".format(currency, e))
    return 0.0

# ═══════════════════════════════════════════════════════════════
#  LIVE EQUITY + TRADE-LOG BACKUP (v8.4)
# ═══════════════════════════════════════════════════════════════
def refresh_equity(force=False):
    """Equity = free USDT + cost basis of open tracked positions. Cached 60s.
    Sizing, heat and daily-loss maths use this instead of the fixed 10."""
    global portfolio_size, equity_peak, last_equity_refresh
    now = time.time()
    if not USE_DYNAMIC_EQUITY:
        return portfolio_size
    if not force and (now - last_equity_refresh) < 60:
        return portfolio_size
    last_equity_refresh = now
    try:
        usdt = get_balance("USDT")
        if usdt <= 0:                      # API error returns 0.0 -- don't trust it
            return portfolio_size
        held = 0.0
        for st in positions.values():
            if st.get("position"):
                px = st.get("entry_fill_price") or st.get("entry_price") or 0
                held += (st.get("remaining_size") or 0) * px
        portfolio_size = max(MIN_EQUITY, usdt + held)
        if portfolio_size > equity_peak:
            equity_peak = portfolio_size
    except Exception as e:
        logger.warning("Equity refresh failed: {}".format(e))
    return portfolio_size

def backup_trade_log():
    """Hourly copy of the trade CSV + state to BACKUP_DIR (never overwrites with an empty file)."""
    global last_backup
    now = time.time()
    if now - last_backup < 3600:
        return
    last_backup = now
    try:
        os.makedirs(BACKUP_DIR, exist_ok=True)
        day = datetime.date.today().strftime("%Y%m%d")
        for path in (TRADE_LOG_FILE, STATE_FILE, WALLET_LOG_FILE):
            if os.path.exists(path) and os.path.getsize(path) > 0:
                shutil.copy2(path, os.path.join(BACKUP_DIR, "{}_{}".format(day, os.path.basename(path))))
    except Exception as e:
        logger.warning("Backup failed: {}".format(e))

# ═══════════════════════════════════════════════════════════════
#  INDICATORS
# ═══════════════════════════════════════════════════════════════
def add_indicators(df):
    close  = df["close"]
    high   = df["high"]
    low    = df["low"]
    volume = df["volume"]
    df["rsi"]      = RSIIndicator(close, window=14).rsi()
    df["rsi_fast"] = RSIIndicator(close, window=7).rsi()
    stoch = StochasticOscillator(high, low, close)
    df["stoch_k"]  = stoch.stoch()
    df["stoch_d"]  = stoch.stoch_signal()
    df["ema9"]     = EMAIndicator(close, window=9).ema_indicator()
    df["ema21"]    = EMAIndicator(close, window=21).ema_indicator()
    df["ema50"]    = EMAIndicator(close, window=50).ema_indicator()
    df["ema200"]   = EMAIndicator(close, window=200).ema_indicator()
    macd_obj       = MACD(close)
    df["macd"]     = macd_obj.macd()
    df["macd_sig"] = macd_obj.macd_signal()
    df["macd_diff"]= macd_obj.macd_diff()
    adx_obj        = ADXIndicator(high, low, close, window=14)
    df["adx"]      = adx_obj.adx()
    df["adx_pos"]  = adx_obj.adx_pos()
    df["adx_neg"]  = adx_obj.adx_neg()
    atr_obj        = AverageTrueRange(high, low, close, window=14)
    df["atr"]      = atr_obj.average_true_range()
    df["atr_pct"]  = df["atr"] / close
    bb_obj         = BollingerBands(close, window=20, window_dev=2)
    df["bb_upper"] = bb_obj.bollinger_hband()
    df["bb_lower"] = bb_obj.bollinger_lband()
    df["bb_mid"]   = bb_obj.bollinger_mavg()
    df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / df["bb_mid"]
    typical_price  = (high + low + close) / 3
    cumvol         = volume.cumsum()
    df["vwap"]     = (typical_price * volume).cumsum() / cumvol.replace(0, np.nan)
    df["vol_ma20"]  = volume.rolling(window=20).mean()
    df["vol_ma20"]  = df["vol_ma20"].replace(0, np.nan).fillna(volume.mean())
    df["vol_ratio"] = volume / df["vol_ma20"]
    df["vol_ratio"] = df["vol_ratio"].replace([np.inf, -np.inf], np.nan).fillna(1.0)
    df["price_accel"] = close.diff().diff()
    return df

# ═══════════════════════════════════════════════════════════════
#  REGIME DETECT (5min timeframe)
# ═══════════════════════════════════════════════════════════════
def detect_regime(df):
    last      = df.iloc[-1]
    adx       = last["adx"]
    bb_width  = last["bb_width"]
    ema_slope = (last["ema50"] - df["ema50"].iloc[-10]) / df["ema50"].iloc[-10]
    if bb_width > 0.06:                       return "VOLATILE"
    if adx < ADX_TRENDING:                    return "RANGING"
    if adx >= ADX_TRENDING and ema_slope > 0: return "TRENDING_UP"
    if adx >= ADX_TRENDING and ema_slope < 0: return "TRENDING_DOWN"
    return "RANGING"

def passes_regime_filter(df):
    last    = df.iloc[-1]
    adx     = last["adx"]
    atr_pct = last["atr_pct"]
    bb_w    = last["bb_width"]
    if adx > MAX_ADX_FOR_ENTRY:
        return False, "ADX {:.1f} too high (strong trend)".format(adx)
    if atr_pct > MAX_ATR_PCT_FOR_ENTRY:
        return False, "ATR% {:.3f} too volatile".format(atr_pct)
    if bb_w < MIN_BB_WIDTH_FOR_ENTRY:
        return False, "BB too tight (no movement)"
    if bb_w > MAX_BB_WIDTH_FOR_ENTRY:
        return False, "BB too wide (exploding)"
    return True, "OK"

# ═══════════════════════════════════════════════════════════════
#  REVERSAL FILTER — 2/3 required
# ═══════════════════════════════════════════════════════════════
def passes_reversal_filter(df):
    last  = df.iloc[-1]
    prev  = df.iloc[-2]
    prev2 = df.iloc[-3]
    rsi_up     = last["rsi"] > prev["rsi"]
    bull_close = last["close"] > last["open"]
    no_new_low = min(last["low"], prev["low"]) >= prev2["low"] * 0.998
    confirmed  = sum([rsi_up, bull_close, no_new_low])
    if confirmed < 2:
        reasons = []
        if not rsi_up:     reasons.append("RSI falling")
        if not bull_close: reasons.append("bearish candle")
        if not no_new_low: reasons.append("new lows")
        return False, "Only {}/3: {}".format(confirmed, ", ".join(reasons))
    return True, "{}/3 reversal confirmed".format(confirmed)

# ═══════════════════════════════════════════════════════════════
#  RSI DIVERGENCE
# ═══════════════════════════════════════════════════════════════
def detect_bullish_divergence(df, lookback=20):
    recent  = df.tail(lookback)
    low_idx = recent["low"].nsmallest(2).index.tolist()
    if len(low_idx) < 2:
        return False
    low_idx.sort()
    i1, i2 = low_idx[0], low_idx[1]
    return (recent.loc[i2, "low"] < recent.loc[i1, "low"] and
            recent.loc[i2, "rsi"] > recent.loc[i1, "rsi"])

# ═══════════════════════════════════════════════════════════════
#  HTF BIAS
# ═══════════════════════════════════════════════════════════════
def get_htf_bias(symbol):
    df = get_htf_candles(symbol)
    if df is None or len(df) < 50:
        return "NEUTRAL"
    df   = add_indicators(df)
    last = df.iloc[-1]
    bull = sum([last["ema9"] > last["ema21"], last["ema21"] > last["ema50"],
                last["macd_diff"] > 0, last["rsi"] > 50])
    if bull >= 3: return "BULLISH"
    if bull <= 1: return "BEARISH"
    return "NEUTRAL"

# ═══════════════════════════════════════════════════════════════
#  WEIGHTED CONFIDENCE SCORING (4 categories)
# ═══════════════════════════════════════════════════════════════
def calculate_confidence_weighted(df, symbol, regime, htf_bias):
    last    = df.iloc[-1]
    reasons = []
    risks   = []

    tech = 0
    rsi  = last["rsi"]
    price = last["close"]

    if rsi < 25:
        tech += 30; reasons.append("RSI extremely oversold ({:.1f})".format(rsi))
    elif rsi < RSI_OVERSOLD:
        tech += 22; reasons.append("RSI oversold ({:.1f})".format(rsi))
    elif rsi < 40:
        tech += 12; reasons.append("RSI approaching oversold ({:.1f})".format(rsi))
    elif rsi > RSI_OVERBOUGHT:
        tech -= 10; risks.append("RSI near overbought")

    if last["macd_diff"] > 0 and df.iloc[-2]["macd_diff"] <= 0:
        tech += 20; reasons.append("MACD bullish crossover")
    elif last["macd_diff"] > 0:
        tech += 10; reasons.append("MACD positive")
    elif last["macd_diff"] < 0:
        tech -= 5

    if last["ema9"] > last["ema21"] > last["ema50"]:
        tech += 20; reasons.append("Full EMA bullish (9>21>50)")
    elif last["ema9"] > last["ema21"]:
        tech += 10; reasons.append("Short EMA bullish")

    if price <= last["bb_lower"]:
        tech += 15; reasons.append("Price at BB lower band")
    elif price < last["bb_mid"]:
        tech += 8;  reasons.append("Price below BB mid")

    if not np.isnan(last["vwap"]):
        if price < last["vwap"] * 0.998:
            tech += 10; reasons.append("Price below VWAP (discount)")
        elif price < last["vwap"]:
            tech += 5

    if detect_bullish_divergence(df):
        tech += 5; reasons.append("Bullish RSI divergence")

    if last["stoch_k"] < 20 and last["stoch_d"] < 20:
        tech += 5

    tech = max(0, min(100, tech))

    reg_score = 50

    if htf_bias == "BULLISH":
        reg_score += 20; reasons.append("1H bias BULLISH")
    elif htf_bias == "BEARISH":
        reg_score -= 25; risks.append("1H bias BEARISH")

    if regime == "RANGING":
        reg_score += 15; reasons.append("Ranging market (ideal)")
    elif regime == "TRENDING_UP":
        reg_score += 10
    elif regime == "VOLATILE":
        reg_score -= 15; risks.append("Volatile regime")
    elif regime == "TRENDING_DOWN":
        reg_score -= 30; risks.append("Downtrend")

    funding = get_funding_rate(symbol)
    if funding < FUNDING_NEGATIVE_BONUS:
        reg_score += 15; reasons.append("Funding rate negative (over-shorted)")
    elif funding < 0:
        reg_score += 8
    elif funding > FUNDING_POSITIVE_PENALTY:
        reg_score -= 10; risks.append("High positive funding")

    fng_score, fng_label = get_fear_and_greed()
    if fng_score <= FNG_EXTREME_FEAR:
        reg_score += 15; reasons.append("Extreme Fear {}/100".format(fng_score))
    elif fng_score <= 45:
        reg_score += 8
    elif fng_score > 80:
        reg_score -= 15; risks.append("Extreme Greed index")
    elif fng_score > FNG_MAX_SCORE:
        reg_score -= 8

    reg_score = max(0, min(100, reg_score))

    vol_score = 30
    vol_ratio = last["vol_ratio"]
    if vol_ratio >= 3.0:
        vol_score = 100; reasons.append("Massive volume spike {:.1f}x".format(vol_ratio))
    elif vol_ratio >= 2.0:
        vol_score = 80;  reasons.append("Strong volume {:.1f}x".format(vol_ratio))
    elif vol_ratio >= 1.5:
        vol_score = 60;  reasons.append("Above avg volume {:.1f}x".format(vol_ratio))
    elif vol_ratio >= 1.0:
        vol_score = 45
    elif vol_ratio < 0.7:
        vol_score = 10;  risks.append("Low volume")

    mom_score = 50

    rsi_change = rsi - df.iloc[-3]["rsi"]
    if rsi_change > 5:
        mom_score += 20; reasons.append("RSI accelerating up")
    elif rsi_change > 2:
        mom_score += 10
    elif rsi_change < -5:
        mom_score -= 15

    macd_h = last["macd_diff"]
    if macd_h > 0:
        mom_score += min(20, abs(macd_h) * 1000)

    if not np.isnan(last["price_accel"]) and last["price_accel"] > 0:
        mom_score += 10

    mom_score = max(0, min(100, mom_score))

    final = (
        tech      * CONF_WEIGHT_TECHNICAL +
        reg_score * CONF_WEIGHT_REGIME    +
        vol_score * CONF_WEIGHT_VOLUME    +
        mom_score * CONF_WEIGHT_MOMENTUM
    )
    final = max(0, min(100, int(final)))

    breakdown = {
        "technical": tech,
        "regime":    reg_score,
        "volume":    vol_score,
        "momentum":  mom_score,
    }

    if risks:
        reasons.append("RISKS: " + " | ".join(risks))

    return final, reasons, breakdown

# ═══════════════════════════════════════════════════════════════
#  POSITION SIZING
# ═══════════════════════════════════════════════════════════════
def calculate_position_size(entry_price, stop_loss, confidence):
    sl_pct = max(abs(entry_price - stop_loss) / entry_price, MIN_SL_PCT)

    if confidence >= 85:   conf_mult = 1.5
    elif confidence >= 70: conf_mult = 1.2
    elif confidence >= 62: conf_mult = 1.0
    else:                  conf_mult = 0.7   # 55-61 (v8.4: lower entry threshold)

    pf          = refresh_equity()
    allocation  = pf * BASE_ALLOCATION_PCT * conf_mult
    risk_budget = pf * MAX_RISK_PER_TRADE * conf_mult      # 1% of equity at risk per trade
    risk_cap    = risk_budget / sl_pct
    funds       = min(allocation, risk_cap)
    funds       = min(funds, pf * MAX_POSITION_PCT)
    return round(funds, 2)

# ═══════════════════════════════════════════════════════════════
#  GUARDS
# ═══════════════════════════════════════════════════════════════
def _returns_for(symbol, df=None):
    now = time.time()
    c = corr_cache.get(symbol)
    if c and (now - c["ts"]) < CORR_CANDLE_TTL:
        return c["returns"]
    if df is None:
        df = get_candles(symbol, limit=80)
    if df is None or len(df) < 30:
        return None
    rets = df["close"].pct_change().dropna().values
    corr_cache[symbol] = {"returns": rets, "ts": now}
    return rets

def correlation_blocked(symbol, df):
    open_syms = [s for s in positions if positions[s].get("position") and s != symbol]
    if not open_syms:
        return False
    cand = _returns_for(symbol, df)
    if cand is None:
        return False
    for osym in open_syms:
        oret = _returns_for(osym)
        if oret is None:
            continue
        n = min(len(cand), len(oret), 60)
        if n < 20:
            continue
        try:
            corr = float(np.corrcoef(cand[-n:], oret[-n:])[0, 1])
        except Exception:
            continue
        if not np.isnan(corr) and corr >= CORRELATION_THRESHOLD:
            logger.info("[{}] corr {:.2f} with open {} -- blocked".format(symbol, corr, osym))
            return True
    return False

def prune_positions():
    now = time.time()
    core = {i["symbol"] for i in SYMBOLS}
    for sym in list(positions.keys()):
        if sym in core:
            continue
        st = positions[sym]
        if st.get("position") is not None:
            continue
        lct = st.get("last_close_time")
        if lct and (now - lct) < COOLDOWN_PERIOD:
            continue
        del positions[sym]

def open_position_count():
    return sum(1 for s in positions.values() if s["position"] is not None)

def total_portfolio_heat():
    heat = 0.0
    for state in positions.values():
        entry = state.get("entry_fill_price") or state.get("entry_price")
        if state["position"] and entry and state["stop_loss"]:
            risk  = abs(entry - state["stop_loss"]) / entry
            heat += (risk * (state["funds_used"] or 0)) / max(portfolio_size, 1.0)
    return heat

# ═══════════════════════════════════════════════════════════════
#  ORDER EXECUTION
# ═══════════════════════════════════════════════════════════════
def place_order(symbol, side, size=None, funds=None, retries=3):
    for attempt in range(retries):
        try:
            if side == "sell" and size is not None:
                size = adjust_size_to_lot(symbol, size)
                if size <= 0:
                    return None
            if USE_OLD_API:
                if side == "buy":
                    return client.create_market_order(symbol, side, funds=str(funds))
                else:
                    return client.create_market_order(symbol, side, size=str(size))
            else:
                if side == "buy":
                    return client["trade"].create_market_order(symbol, side, funds=str(funds))
                else:
                    return client["trade"].create_market_order(symbol, side, size=str(size))
        except Exception as e:
            err = str(e)
            if "429" in err:
                time.sleep((attempt + 1) * 5)
            elif "400100" in err and size and attempt < retries - 1:
                _, inc = LOT_RULES.get(symbol, (0.001, 0.001))
                size = round(size - inc, 8)
            else:
                logger.error("Order error [{} {}]: {}".format(symbol, side, err[:100]))
                if attempt == retries - 1:
                    send_telegram("ORDER FAILED {} {}\n{}".format(side.upper(), symbol, err[:80]))
                time.sleep(2)
    return None

def execute_market_sell(symbol, size, fallback_price):
    order = place_order(symbol, "sell", size=size)
    if not order:
        return None
    fill = get_fill_details(extract_order_id(order))
    if fill:
        return {"avg_price": fill["avg_price"], "size": fill["size"], "fee": fill["fee"]}
    est_fee = size * fallback_price * KUCOIN_FEE_RATE
    return {"avg_price": fallback_price, "size": size, "fee": est_fee}

# ═══════════════════════════════════════════════════════════════
#  TRADE LOGGING
#  v8.3.3: pnl_gross/pnl_net renamed to *_pct in the CSV header --
#  they were ALWAYS percentage returns (round(x*100,4)), never
#  dollars, but the unlabeled names read like currency and caused a
#  real misdiagnosis reviewing this log externally. realized_usd and
#  fee_usd remain the only dollar columns; no values changed here,
#  just the header.
# ═══════════════════════════════════════════════════════════════
def log_trade(symbol, action, price, size=None, pnl_gross=None, pnl_net=None,
              realized_usd=None, fee_usd=None, confidence=None, reason=None,
              breakdown=None):
    price_safe = sanitize_price(symbol, price)
    row = {
        "timestamp":     datetime.datetime.now().isoformat(),
        "symbol":        symbol,
        "action":        action,
        "fill_price":    round(price_safe, 8),
        "size":          round(size, 8) if size is not None else "",
        "pnl_gross_pct": round(pnl_gross * 100, 4) if pnl_gross is not None else "",
        "pnl_net_pct":   round(pnl_net * 100, 4)   if pnl_net   is not None else "",
        "realized_usd":  round(realized_usd, 5)    if realized_usd is not None else "",
        "fee_usd":       round(fee_usd, 5)         if fee_usd   is not None else "",
        "confidence":    confidence or "",
        "tech_score":    breakdown.get("technical", "") if breakdown else "",
        "regime_score":  breakdown.get("regime", "")    if breakdown else "",
        "vol_score":     breakdown.get("volume", "")    if breakdown else "",
        "mom_score":     breakdown.get("momentum", "")  if breakdown else "",
        "reason":        (reason or "")[:200],
    }
    write_header = (not os.path.exists(TRADE_LOG_FILE)) or os.path.getsize(TRADE_LOG_FILE) == 0
    with open(TRADE_LOG_FILE, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=row.keys())
        if write_header:
            writer.writeheader()
        writer.writerow(row)

# ═══════════════════════════════════════════════════════════════
#  PERFORMANCE
# ═══════════════════════════════════════════════════════════════
def calculate_performance():
    if not trade_results:
        return {}
    results = list(trade_results)
    wins    = [r for r in results if r > 0]
    losses  = [r for r in results if r <= 0]
    win_rate      = len(wins) / len(results) * 100
    avg_win       = np.mean(wins)   if wins   else 0
    avg_loss      = np.mean(losses) if losses else 0
    profit_factor = abs(sum(wins) / sum(losses)) if losses and sum(losses) != 0 else float("inf")
    if len(results) > 1:
        mean_r = np.mean(results)
        std_r  = np.std(results)
        sharpe = (mean_r / std_r) * math.sqrt(252) if std_r > 0 else 0
    else:
        sharpe = 0
    eq = list(equity_curve)
    max_dd = 0
    if len(eq) > 1:
        peak = eq[0]
        for v in eq:
            peak   = max(peak, v)
            max_dd = max(max_dd, (peak - v) / peak) if peak > 0 else max_dd
    return {
        "trades": len(results), "win_rate": win_rate,
        "avg_win_pct": avg_win * 100, "avg_loss_pct": avg_loss * 100,
        "profit_factor": profit_factor, "sharpe": sharpe,
        "max_drawdown": max_dd * 100, "total_pnl_pct": sum(results) * 100,
    }

# ═══════════════════════════════════════════════════════════════
#  ACCOUNTING ENGINE — every fill is booked in DOLLARS the moment
#  it happens. Partial exits count. Nothing is lost.
# ═══════════════════════════════════════════════════════════════
def book_leg(state, sell_size, fill_price, exit_fee):
    entry    = state["entry_fill_price"] or state["entry_price"] or fill_price
    original = state["original_size"] or sell_size
    entry_fee_share = (state["entry_fee"] or 0) * (sell_size / original) if original > 0 else 0
    realized  = sell_size * (fill_price - entry) - exit_fee - entry_fee_share
    gross_pct = (fill_price - entry) / entry if entry > 0 else 0
    cost      = sell_size * entry
    net_pct   = (realized / cost) if cost > 0 else 0
    state["realized_usd"] = (state.get("realized_usd") or 0) + realized
    state["fees_usd"]     = (state.get("fees_usd") or 0) + exit_fee + entry_fee_share
    return realized, gross_pct, net_pct

def apply_realized_to_books(realized_usd):
    global daily_pnl, weekly_pnl
    frac = realized_usd / max(portfolio_size, 1.0)
    daily_pnl  += frac
    weekly_pnl += frac
    prev_eq = equity_curve[-1] if equity_curve else float(PORTFOLIO_SIZE)
    equity_curve.append(prev_eq + realized_usd)

def finalize_close(symbol, state, sell_size, fill_price, exit_fee, reason,
                   breakdown=None, already_booked=False):
    global weekly_trades, weekly_wins, weekly_losses, consecutive_losses
    global weekly_best_trade, weekly_worst_trade, symbol_daily_losses
    global daily_wins, daily_losses

    now = time.time()

    if not already_booked and sell_size and sell_size > 0:
        realized, gross_pct, net_pct = book_leg(state, sell_size, fill_price, exit_fee)
        apply_realized_to_books(realized)
    else:
        entry = state["entry_fill_price"] or state["entry_price"] or fill_price
        gross_pct = (fill_price - entry) / entry if entry else 0

    total_realized = state.get("realized_usd") or 0
    funds_used     = state.get("funds_used") or PORTFOLIO_SIZE
    trade_return   = total_realized / funds_used if funds_used > 0 else 0

    trade_results.append(trade_return)
    weekly_trades += 1

    if trade_return > 0:
        weekly_wins += 1
        daily_wins  += 1
        consecutive_losses = 0
        if trade_return > weekly_best_trade.get("pnl", 0):
            weekly_best_trade = {"symbol": symbol, "pnl": trade_return}
    else:
        weekly_losses += 1
        daily_losses  += 1
        consecutive_losses += 1
        symbol_daily_losses[symbol] = symbol_daily_losses.get(symbol, 0) + 1
        if trade_return < weekly_worst_trade.get("pnl", 0):
            weekly_worst_trade = {"symbol": symbol, "pnl": trade_return}

    if state.get("stop_order_id"):
        cancel_exchange_stop(state["stop_order_id"])

    perf = calculate_performance()
    send_telegram(
        "{} CLOSED {}{}\n"
        "Final fill: ${:.6f} | {}\n"
        "Trade total: ${:.3f} ({:.2f}% on ${:.2f})\n"
        "Fees total: ${:.3f}\n"
        "Daily: {:.2f}% ({}/{})\n"
        "Weekly: {:.2f}%\n"
        "WR: {:.1f}% | PF: {:.2f}".format(
            "WIN" if trade_return > 0 else "LOSS", symbol,
            " [was ADOPTED -- entry was estimated]" if state.get("adopted") else "",
            fill_price, reason,
            total_realized, trade_return * 100, funds_used,
            state.get("fees_usd") or 0,
            daily_pnl * 100, daily_trades, tg_max_daily_trades,
            weekly_pnl * 100,
            perf.get("win_rate", 0), perf.get("profit_factor", 0),
        )
    )

    if consecutive_losses >= MAX_CONSECUTIVE_LOSSES:
        send_telegram("{} consecutive losses -- pausing entries today".format(consecutive_losses))
    if symbol_daily_losses.get(symbol, 0) >= MAX_SYMBOL_DAILY_LOSSES:
        send_telegram("{} blacklisted today ({} losses)".format(symbol, symbol_daily_losses[symbol]))

    log_trade(symbol, "CLOSE", fill_price, size=sell_size,
              pnl_gross=gross_pct, pnl_net=trade_return,
              realized_usd=total_realized, fee_usd=state.get("fees_usd"),
              reason=reason, breakdown=breakdown or state.get("conf_breakdown"))

    positions[symbol] = make_state()
    positions[symbol]["last_close_time"] = now
    save_state()

# ═══════════════════════════════════════════════════════════════
#  POSITION HOLDINGS VERIFIER
#  Ground truth = the wallet BALANCE, not the stop-order status
#  endpoint. If the coins are gone, the trade is over -- book it
#  instead of leaving a phantom "open" position.
#
#  v8.3.3: when an exchange stop-loss triggered, this used to
#  ALWAYS book the exit at the stop trigger price, never the real
#  fill. A stop-market order can slip past its trigger in a fast
#  move, so the trigger price was only ever an approximation even
#  when a real, fetchable fill existed. Now it tries
#  get_fill_details() on the stop order id first (same lookup
#  already used for regular market orders) and only falls back to
#  the estimate if that fails.
# ═══════════════════════════════════════════════════════════════
def verify_position_holdings(symbol, info, state, price_hint=None, force=False):
    now = time.time()
    if state.get("position") is None:
        return False
    if not force and now - (state.get("last_stop_check") or 0) < STOP_CHECK_INTERVAL:
        return False
    state["last_stop_check"] = now

    bal       = get_balance(info["base"])
    remaining = state.get("remaining_size") or 0
    if remaining <= 0 and state.get("funds_used") and state.get("entry_fill_price"):
        remaining = state["funds_used"] / state["entry_fill_price"]

    est_price = price_hint
    if not est_price:
        try:
            t = client["market"].get_ticker(symbol) if not USE_OLD_API else client.get_ticker(symbol)
            est_price = sanitize_price(symbol, float(t.get("price", 0))) or None
        except Exception:
            est_price = None
    if not est_price:
        est_price = state.get("entry_fill_price") or state.get("entry_price") or 0

    sellable  = adjust_size_to_lot(symbol, bal)
    dust_only = (sellable <= 0) or (est_price and bal * est_price < DUST_USD)
    gone      = remaining > 0 and bal < remaining * 0.2

    if dust_only or gone:
        had_stop   = bool(state.get("stop_order_id"))
        book_size  = max(0.0, remaining - bal)

        fill_price = None
        real_fee   = None
        used_real_fill = False
        if had_stop:
            # v8.3.3: try the REAL fill before falling back to the
            # stop trigger price estimate.
            real_fill = get_fill_details(state.get("stop_order_id"), retries=3)
            if real_fill and real_fill.get("avg_price"):
                fill_price = sanitize_price(symbol, real_fill["avg_price"])
                real_fee   = real_fill.get("fee")
                used_real_fill = True

        if fill_price is None:
            fill_price = (state.get("exchange_stop_price") or state.get("stop_loss")
                          or est_price) if had_stop else est_price

        exit_fee = real_fee if real_fee is not None else book_size * (fill_price or 0) * KUCOIN_FEE_RATE
        reason   = ("Exchange stop-loss filled ({})".format(
                        "REAL FILL" if used_real_fill else "ESTIMATED @ stop price")
                    if had_stop else "Position gone from wallet (ESTIMATED)")
        if bal > 0:
            reason += " | dust left: {:.8f} {} (~${:.2f}, untradeable)".format(
                bal, info["base"], bal * (est_price or 0))
        logger.warning("Holdings verify closed [{}]: {}".format(symbol, reason))
        if had_stop:
            cancel_exchange_stop(state.get("stop_order_id"))
            state["stop_order_id"] = None
        finalize_close(symbol, state, book_size, fill_price or 0, exit_fee, reason)
        return True

    if state.get("stop_order_id"):
        status = get_stop_order_status(state["stop_order_id"])
        if status not in ("NEW", "UNKNOWN"):
            logger.warning("Exchange stop missing but coins present [{}] -- re-placing".format(symbol))
            state["stop_order_id"] = None
            sync_stop_order(symbol, state, state["stop_loss"],
                            min(bal, remaining or bal), force=True)
    return False

def reconcile_exchange_stop(symbol, info, state):
    return verify_position_holdings(symbol, info, state)

# ═══════════════════════════════════════════════════════════════
#  DAILY RESET
# ═══════════════════════════════════════════════════════════════
def record_daily_log():
    global daily_log, pnl_calendar
    today_str = str(last_reset_date)
    if daily_pnl != 0.0 or daily_trades > 0:
        row = {"pnl": daily_pnl, "trades": daily_trades,
               "wins": daily_wins, "losses": daily_losses}
        daily_log[today_str]    = row
        pnl_calendar[today_str] = row
        if len(pnl_calendar) > 120:
            for k in sorted(pnl_calendar.keys())[:-120]:
                del pnl_calendar[k]

def top_filter_blocks(n=3):
    if not filter_rejects:
        return "none"
    items = sorted(filter_rejects.items(), key=lambda x: -x[1])[:n]
    return ", ".join("{} x{}".format(k, v) for k, v in items)

def reset_daily_stats():
    global daily_pnl, daily_trades, last_reset_date
    global cb_triggered, cb_reason, consecutive_losses, symbol_daily_losses
    global tg_max_daily_trades, daily_wins, daily_losses, filter_rejects
    today = datetime.date.today()
    if today != last_reset_date:
        perf    = calculate_performance()
        fng, fl = get_fear_and_greed()
        record_daily_log()
        send_telegram(
            "DAILY REPORT {}\n\n"
            "PnL: {:.2f}% | Trades: {} ({}W {}L)\n"
            "Win Rate: {:.1f}% | PF: {:.2f}\n"
            "Top filter blocks: {}\n"
            "F+G: {}/100 ({})".format(
                last_reset_date, daily_pnl * 100, daily_trades,
                daily_wins, daily_losses,
                perf.get("win_rate", 0), perf.get("profit_factor", 0),
                top_filter_blocks(), fng, fl,
            )
        )
        daily_pnl = 0.0; daily_trades = 0; consecutive_losses = 0
        daily_wins = 0; daily_losses = 0; filter_rejects = {}
        cb_triggered = False; cb_reason = ""; symbol_daily_losses = {}
        tg_max_daily_trades = MAX_DAILY_TRADES
        last_reset_date = today
        save_state()

def check_daily_limits(symbol=None):
    global cb_triggered, cb_reason, dd_alerted
    if tg_trading_paused:
        return False, "paused"
    if cb_triggered:
        return False, "circuit_breaker"
    if equity_peak > 0 and portfolio_size < equity_peak * (1 - MAX_DRAWDOWN_PAUSE):
        if not dd_alerted:
            dd_alerted = True
            send_telegram("DRAWDOWN PAUSE -- equity ${:.2f} is >{:.0f}% below peak ${:.2f}.\n"
                          "Entries paused. Send /resume to reset the baseline and continue.".format(
                              portfolio_size, MAX_DRAWDOWN_PAUSE * 100, equity_peak))
        return False, "drawdown_pause"
    if daily_trades >= tg_max_daily_trades:
        return False, "max_daily_trades"
    if daily_pnl <= MAX_DAILY_LOSS:
        cb_triggered = True; cb_reason = "Daily loss limit"
        send_telegram("CIRCUIT BREAKER -- daily loss limit hit")
        return False, "daily_loss_limit"
    if daily_pnl >= DAILY_PROFIT_TARGET:
        return False, "profit_target_hit"
    if total_portfolio_heat() >= MAX_PORTFOLIO_HEAT:
        return False, "portfolio_heat"
    if open_position_count() >= MAX_OPEN_POSITIONS:
        return False, "max_positions_open"
    if consecutive_losses >= MAX_CONSECUTIVE_LOSSES:
        return False, "loss_streak"
    if symbol and symbol_daily_losses.get(symbol, 0) >= MAX_SYMBOL_DAILY_LOSSES:
        return False, "symbol_blacklisted"
    return True, "ok"

# ═══════════════════════════════════════════════════════════════
#  MAIN SIGNAL ENGINE
# ═══════════════════════════════════════════════════════════════
heartbeat_timer = time.time()

def check_signals(df, info):
    global daily_trades, heartbeat_timer

    symbol = info["symbol"]
    base   = info["base"]
    state  = positions.setdefault(symbol, make_state())
    now    = time.time()
    last   = df.iloc[-1]
    price  = last["close"]
    rsi    = last["rsi"]
    atr    = last["atr"]

    if now - heartbeat_timer > 3600:
        perf        = calculate_performance()
        fng, flabel = get_fear_and_greed()
        usdt_bal    = get_balance("USDT")
        regime      = get_market_regime()
        send_telegram(
            "HEARTBEAT v8.4\n"
            "Regime: {} | BTC: {}\n"
            "PnL: {:.2f}% ({}/{})\n"
            "Open: {}/{} | USDT: ${:.2f}\n"
            "Streak: {} | WR: {:.1f}%\n"
            "Weekly PnL: {:.2f}%\n"
            "F+G: {}/100 ({})\n"
            "Top blocks: {}".format(
                regime, get_btc_bias(),
                daily_pnl*100, daily_trades, tg_max_daily_trades,
                open_position_count(), MAX_OPEN_POSITIONS, usdt_bal,
                consecutive_losses, perf.get("win_rate",0),
                weekly_pnl*100, fng, flabel,
                top_filter_blocks(),
            )
        )
        heartbeat_timer = now

    if state["last_close_time"] and (now - state["last_close_time"]) < COOLDOWN_PERIOD:
        return

    if state["position"] is None:
        limits_ok, limits_reason = check_daily_limits(symbol)
        if not limits_ok:
            per_symbol = limits_reason == "symbol_blacklisted"
            bump_filter(limits_reason, once_per_cycle=not per_symbol)
            return
        if not is_good_trading_time():
            bump_filter("hour_filter", once_per_cycle=True); return

        market_regime = get_market_regime()
        if market_regime == "HIGH_VOLATILITY":
            bump_filter("market_high_vol", once_per_cycle=True)
            return

        fng_score, fng_label = get_fear_and_greed()
        if fng_score > FNG_MAX_SCORE:
            bump_filter("fear_greed", once_per_cycle=True); return

        btc_bias = get_btc_bias()
        if btc_bias == "BEARISH":
            bump_filter("btc_bearish", once_per_cycle=True); return

        if get_24h_volume(symbol) < MIN_VOLUME_24H:
            bump_filter("volume_24h"); return
        if correlation_blocked(symbol, df):
            bump_filter("correlation"); return

        regime_ok, regime_reason = passes_regime_filter(df)
        if not regime_ok:
            bump_filter("regime_filter")
            logger.info("[{}] Regime: {}".format(symbol, regime_reason))
            return

        reversal_ok, reversal_reason = passes_reversal_filter(df)
        if not reversal_ok:
            bump_filter("reversal_2of3")
            logger.info("[{}] Reversal: {}".format(symbol, reversal_reason))
            return

        regime   = detect_regime(df)
        htf_bias = get_htf_bias(symbol)

        confidence, reasons, breakdown = calculate_confidence_weighted(df, symbol, regime, htf_bias)

        logger.info("[{}] ${:.6f} RSI:{:.1f} ADX:{:.1f} T:{} R:{} V:{} M:{} -> Conf:{}".format(
            symbol, price, rsi, last["adx"],
            breakdown["technical"], breakdown["regime"],
            breakdown["volume"], breakdown["momentum"],
            confidence))

        if confidence < MIN_CONFIDENCE:
            bump_filter("confidence"); return

        sym_max_sl = SYMBOL_MAX_SL.get(symbol, MAX_SL_PCT)
        raw_sl_pct = (ATR_SL_MULTIPLIER * atr) / price
        sl_pct     = max(MIN_SL_PCT, min(sym_max_sl, raw_sl_pct))

        tp1_prov = price + ATR_TP1_MULTIPLIER * atr
        tp2_prov = price + ATR_TP2_MULTIPLIER * atr
        tp3_prov = price + ATR_TP3_MULTIPLIER * atr
        reward_frac = (TP1_SELL_PCT * (tp1_prov - price) / price +
                       TP2_SELL_PCT * (tp2_prov - price) / price +
                       (1 - TP1_SELL_PCT - TP2_SELL_PCT) * (tp3_prov - price) / price)
        rr_ratio = reward_frac / sl_pct if sl_pct > 0 else 0
        if rr_ratio < MIN_RR_RATIO:
            bump_filter("rr_ratio"); return

        stop_prov = price * (1 - sl_pct)
        funds     = calculate_position_size(price, stop_prov, confidence)

        est_size = funds / price if price > 0 else 0
        if adjust_size_to_lot(symbol, est_size * TP1_SELL_PCT) <= 0:
            bump_filter("tranche_below_lot")
            logger.info("[{}] Skip -- TP1 tranche below min lot".format(symbol))
            return

        usdt_balance = get_balance("USDT")
        if usdt_balance < funds:
            bump_filter("insufficient_usdt")
            logger.warning("[{}] Insufficient USDT ${:.2f} < ${:.2f}".format(symbol, usdt_balance, funds))
            return

        order = place_order(symbol, "buy", funds=funds)
        if not order:
            return

        fill = get_fill_details(extract_order_id(order))
        if fill:
            entry_fill  = sanitize_price(symbol, fill["avg_price"])
            filled_size = fill["size"]
            entry_fee   = fill["fee"] if fill["fee"] > 0 else funds * KUCOIN_FEE_RATE
            real_funds  = fill["funds"]
        else:
            entry_fill  = price
            filled_size = funds / price
            entry_fee   = funds * KUCOIN_FEE_RATE
            real_funds  = funds

        stop_loss = entry_fill * (1 - sl_pct)
        tp1_price = entry_fill + ATR_TP1_MULTIPLIER * atr
        tp2_price = entry_fill + ATR_TP2_MULTIPLIER * atr
        tp3_price = entry_fill + ATR_TP3_MULTIPLIER * atr
        if not np.isnan(last["vwap"]) and last["vwap"] > tp1_price:
            tp2_price = max(tp2_price, last["vwap"] * 1.002)

        state["position"]         = "long"
        state["entry_price"]      = price
        state["entry_fill_price"] = entry_fill
        state["entry_fee"]        = entry_fee
        state["original_size"]    = filled_size
        state["remaining_size"]   = filled_size
        state["funds_used"]       = real_funds
        state["realized_usd"]     = 0.0
        state["fees_usd"]         = 0.0
        state["highest_price"]    = entry_fill
        state["stop_loss"]        = stop_loss
        state["tp1"]              = tp1_price
        state["tp2"]              = tp2_price
        state["tp3"]              = tp3_price
        state["trailing_stop"]    = None
        state["tp1_hit"]          = False
        state["tp2_hit"]          = False
        state["atr_at_entry"]     = atr
        state["confidence"]       = confidence
        state["conf_breakdown"]   = breakdown
        state["open_time"]        = now
        state["regime_at_entry"]  = market_regime
        state["adopted"]          = False
        daily_trades              += 1

        time.sleep(1.0)
        held      = get_balance(base)
        stop_size = min(filled_size, held) if held > 0 else filled_size
        state["remaining_size"] = stop_size
        sync_stop_order(symbol, state, stop_loss, stop_size, force=True)
        save_state()

        slip = (entry_fill - price) / price * 100 if price > 0 else 0
        sz = "LARGE" if confidence >= 85 else ("NORMAL" if confidence >= 70 else "SMALL")
        send_telegram(
            "LONG OPENED {}\n"
            "Fill: ${:.6f} (slip {:+.3f}%) | Conf: {}/100 ({})\n"
            "T:{} R:{} V:{} M:{}\n"
            "RR: {:.2f}:1 | RSI: {:.1f}\n"
            "SL: ${:.6f} (-{:.2f}%) [{}]\n"
            "TP1: ${:.6f} (30%) | TP2: ${:.6f} (40%)\n"
            "TP3 trail: ${:.6f}\n"
            "Size: ${:.2f} | Fee: ${:.4f}\n"
            "Regime: {} | BTC: {}\n"
            "F+G: {}/100\n"
            "{}".format(
                symbol, entry_fill, slip, confidence, sz,
                breakdown["technical"], breakdown["regime"],
                breakdown["volume"], breakdown["momentum"],
                rr_ratio, rsi,
                stop_loss, sl_pct * 100,
                "ON-EXCHANGE" if state.get("stop_order_id") else "SOFTWARE ONLY!",
                tp1_price, tp2_price, tp3_price,
                real_funds, entry_fee,
                market_regime, btc_bias,
                fng_score,
                " | ".join([r for r in reasons if not r.startswith("RISK")][:3]),
            )
        )
        log_trade(symbol, "OPEN", entry_fill, size=filled_size, fee_usd=entry_fee,
                  confidence=confidence, reason=" | ".join(reasons[:4]),
                  breakdown=breakdown)

    elif state["position"] == "long":
        if verify_position_holdings(symbol, info, state, price_hint=price):
            return

        entry    = state["entry_fill_price"] or state["entry_price"]
        original = state["original_size"] or 0
        pnl_pct  = (price - entry) / entry if entry else 0

        if price > (state["highest_price"] or 0):
            state["highest_price"] = price

        if state["tp2_hit"] and state["trailing_stop"] is None:
            state["trailing_stop"] = price - ATR_TRAIL_MULTIPLIER * state["atr_at_entry"]
        if state["trailing_stop"] is not None:
            new_trail = price - ATR_TRAIL_MULTIPLIER * state["atr_at_entry"]
            if new_trail > state["trailing_stop"]:
                state["trailing_stop"] = new_trail
            eff_stop = max(state["stop_loss"], state["trailing_stop"])
            sync_stop_order(symbol, state, eff_stop,
                            state.get("remaining_size") or 0)

        # v8.4 early break-even: lock +0.2% once the trade is +0.45% (before TP1)
        if (not state["tp1_hit"]) and pnl_pct >= EARLY_BE_TRIGGER:
            lock_price = entry * (1 + EARLY_BE_LOCK)
            if state["stop_loss"] < lock_price:
                state["stop_loss"] = lock_price
                sync_stop_order(symbol, state, lock_price,
                                state.get("remaining_size") or 0, force=True)

        if state["tp1_hit"] and not state["tp2_hit"]:
            be_price = entry * 1.002
            if state["stop_loss"] < be_price:
                state["stop_loss"] = be_price
                sync_stop_order(symbol, state, be_price,
                                state.get("remaining_size") or 0, force=True)

        time_in_trade = now - (state["open_time"] or now)
        stop_hit  = price <= state["stop_loss"] and not state.get("stop_order_id")
        tp1_hit   = (not state["tp1_hit"]) and price >= state["tp1"]
        tp2_hit   = state["tp1_hit"] and (not state["tp2_hit"]) and price >= state["tp2"]
        tp3_hit   = state["tp2_hit"] and price >= state["tp3"]
        trail_hit = state["trailing_stop"] and price <= state["trailing_stop"] and not state.get("stop_order_id")
        vwap_exit = (not np.isnan(last["vwap"]) and state["tp2_hit"]
                     and price >= last["vwap"] and pnl_pct > 0.008)
        rsi_exit  = rsi >= RSI_OVERBOUGHT and state["tp2_hit"]
        time_exit = time_in_trade > TIME_EXIT_SECONDS and abs(pnl_pct) < 0.004

        exit_reason = None
        sell_size   = None
        is_partial  = False
        which_tp    = None

        if stop_hit:
            exit_reason = "SOFTWARE stop backup ({:.2f}%)".format(pnl_pct*100)
            sell_size   = None
        elif tp1_hit:
            exit_reason = "TP1 +{:.2f}% (30% of original)".format(pnl_pct*100)
            sell_size   = original * TP1_SELL_PCT
            is_partial  = True
            which_tp    = "tp1"
        elif tp2_hit:
            exit_reason = "TP2 +{:.2f}% (40% of original)".format(pnl_pct*100)
            sell_size   = original * TP2_SELL_PCT
            is_partial  = True
            which_tp    = "tp2"
        elif tp3_hit or trail_hit:
            exit_reason = "TP3/Trail +{:.2f}% (final)".format(pnl_pct*100)
        elif vwap_exit:
            exit_reason = "VWAP reclaim +{:.2f}%".format(pnl_pct*100)
        elif rsi_exit:
            exit_reason = "RSI overbought +{:.2f}%".format(pnl_pct*100)
        elif time_exit:
            exit_reason = "Time exit {:.2f}%".format(pnl_pct*100)

        logger.info("[{}] PnL:{:.2f}% SL:{:.6f}({}) TP1hit:{} TP2hit:{} Trail:{}".format(
            symbol, pnl_pct*100, state["stop_loss"],
            "exch" if state.get("stop_order_id") else "soft",
            state["tp1_hit"], state["tp2_hit"],
            "{:.6f}".format(state["trailing_stop"]) if state["trailing_stop"] else "N/A"))

        if exit_reason is None:
            save_state()
            return

        base_balance = get_balance(base)

        if (base_balance < 0.00001
                or adjust_size_to_lot(symbol, base_balance) <= 0
                or base_balance * price < DUST_USD):
            verify_position_holdings(symbol, info, state, price_hint=price, force=True)
            return

        if is_partial:
            sell_size = adjust_size_to_lot(symbol, min(sell_size, base_balance))
            if sell_size <= 0:
                if which_tp == "tp1":
                    state["tp1_hit"] = True
                elif which_tp == "tp2":
                    state["tp2_hit"] = True
                logger.warning("[{}] {} tranche below lot size -- level skipped".format(
                    symbol, (which_tp or "").upper()))
                save_state()
                return
        else:
            if state.get("stop_order_id"):
                cancel_exchange_stop(state["stop_order_id"])
                state["stop_order_id"] = None
                state["exchange_stop_price"] = None
            sell_size = adjust_size_to_lot(symbol, base_balance)
            if sell_size <= 0:
                verify_position_holdings(symbol, info, state, price_hint=price, force=True)
                return

        fill = execute_market_sell(symbol, sell_size, price)
        if fill is None:
            if now - (state.get("last_sell_fail_alert") or 0) > 3600:
                state["last_sell_fail_alert"] = now
                save_state()
                send_telegram("CRITICAL SELL FAILED {}\nPnL: {:.2f}%\nSell manually NOW!\n"
                              "(will keep retrying; this alert repeats hourly max)".format(
                                  symbol, pnl_pct*100))
            return

        if is_partial:
            realized, gross_pct, net_pct = book_leg(
                state, fill["size"], fill["avg_price"], fill["fee"])
            apply_realized_to_books(realized)

            if which_tp == "tp1":
                state["tp1_hit"] = True
            elif which_tp == "tp2":
                state["tp2_hit"] = True
            state["remaining_size"] = max(0.0, (state.get("remaining_size") or 0) - fill["size"])

            new_stop = state["stop_loss"]
            if which_tp == "tp1":
                new_stop = max(new_stop, entry * 1.002)
                state["stop_loss"] = new_stop
            sync_stop_order(symbol, state, new_stop, state["remaining_size"], force=True)
            save_state()

            send_telegram(
                "PARTIAL EXIT {} -- {}\n"
                "Fill: ${:.6f} | Gross: +{:.2f}% | Net: +{:.2f}%\n"
                "Banked: ${:.3f} (trade total: ${:.3f})\n"
                "Remaining: {:.4f} {}\n"
                "SL now ${:.6f} [{}]".format(
                    which_tp.upper(), symbol,
                    fill["avg_price"], gross_pct*100, net_pct*100,
                    realized, state["realized_usd"],
                    state["remaining_size"], base,
                    state["stop_loss"],
                    "on-exchange" if state.get("stop_order_id") else "SOFTWARE ONLY",
                )
            )
            log_trade(symbol, "PARTIAL_EXIT", fill["avg_price"], size=fill["size"],
                      pnl_gross=gross_pct, pnl_net=net_pct, realized_usd=realized,
                      fee_usd=fill["fee"], reason=exit_reason,
                      breakdown=state.get("conf_breakdown"))
        else:
            finalize_close(symbol, state, fill["size"], fill["avg_price"],
                           fill["fee"], exit_reason)

# ═══════════════════════════════════════════════════════════════
#  MAIN LOOP
# ═══════════════════════════════════════════════════════════════
def main():
    logger.info("Elite Trading Bot v8.4 -- Starting")
    build_universe()
    load_state()

    # v8.3.3: independent wallet audit runs on EVERY startup, forced,
    # regardless of whether state loaded cleanly. state_load_ok=False
    # means positions may be completely wrong (empty) while real
    # holdings exist -- this is the exact TAO-USDT scenario from the
    # v8.3.2 log. Even on a clean load, a forced audit is cheap
    # insurance (one extra account-list call) against any other gap.
    logger.info("Running startup wallet audit (state_load_ok={})...".format(state_load_ok))
    startup_audit = audit_untracked_holdings(force=True, notify_if_clean=True)
    if startup_audit:
        logger.info("Startup audit: {}".format(startup_audit))

    logger.info("Fetching market conditions...")
    fng, flabel   = get_fear_and_greed()
    logger.info("F+G: {}/100 ({})".format(fng, flabel))
    market_regime = get_market_regime()
    logger.info("Market regime: {}".format(market_regime))

    for sym in [s for s in list(positions.keys()) if positions[s].get("position")]:
        state = positions[sym]
        info  = {"symbol": sym, "base": sym.split("-")[0], "quote": QUOTE_CURRENCY}
        if not reconcile_exchange_stop(sym, info, state):
            if state["position"] and not state.get("stop_order_id"):
                held = get_balance(info["base"])
                size = min(held, state.get("remaining_size") or held)
                if size > 0 and state.get("stop_loss"):
                    logger.info("Restoring exchange stop for {} after restart".format(sym))
                    sync_stop_order(sym, state, state["stop_loss"], size, force=True)

    scan_preview = get_scan_list()
    send_telegram(
        "ELITE BOT v8.4 ONLINE\n\n"
        "AGGRESSIVE profile (unvalidated live test):\n"
        "- Entry conf >=55, ADX<=45, no hour filter\n"
        "- SL 2xATR (min 0.7%), TP 1.8/3.0/4.5 ATR\n"
        "- Early break-even at +0.45%, 2h time exit\n"
        "- Sizing follows live equity (30%/trade)\n"
        "- 25 trades/day, 15 movers, streak pause 5\n"
        "- Drawdown pause at -10% from peak (/resume)\n"
        "- Untracked coins: ALERT ONLY, never traded\n\n"
        "Scanning {} symbols this cycle\n"
        "Regime: {} | F+G: {}/100 ({})\n"
        "Trades today: {}/{}\n\n"
        "Commands: /help".format(
            len(scan_preview),
            market_regime, fng, flabel,
            daily_trades, tg_max_daily_trades,
        )
    )

    logger.info("Main loop started -- hybrid scan every {}s".format(LOOP_INTERVAL))

    while True:
        try:
            begin_cycle()
            reset_daily_stats()
            check_weekly_report()
            check_for_ghost_positions()
            audit_untracked_holdings()   # v8.3.3: periodic full-wallet check (self-throttled)
            refresh_equity()             # v8.4: live equity for sizing / drawdown guard
            backup_trade_log()           # v8.4: hourly CSV + state backup
            poll_telegram_commands()

            if USE_DYNAMIC_UNIVERSE and (time.time() - last_universe_build > UNIVERSE_REFRESH_HOURS * 3600):
                build_universe()

            scan_syms  = get_scan_list()
            open_syms  = [s for s in positions if positions[s].get("position")]
            cycle_syms = list(dict.fromkeys(scan_syms + open_syms))

            for sym in cycle_syms:
                info = {"symbol": sym, "base": sym.split("-")[0], "quote": QUOTE_CURRENCY}
                try:
                    df = get_candles(sym)
                    if df is None or len(df) < 60:
                        continue
                    df = add_indicators(df)
                    check_signals(df, info)
                    time.sleep(0.5)
                except Exception as e:
                    logger.error("Symbol error [{}]: {}".format(sym, str(e)[:100]))

            prune_positions()

            time.sleep(LOOP_INTERVAL)

        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
            record_daily_log()
            send_telegram("Elite Bot v8.4 -- Stopped\n"
                          "(Open positions remain protected by exchange stops)")
            save_state()
            break
        except Exception as e:
            logger.error("Main loop error: {}".format(e), exc_info=True)
            send_telegram("Main Loop Error: {}".format(str(e)[:120]))
            time.sleep(30)

if __name__ == "__main__":
    main()