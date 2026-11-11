"""
backtest.py  --  replays the Elite Bot v8.2 strategy over historical 5m candles.

Measures PER-COIN strategy expectancy with realistic fills + fees. Reads the
CSVs produced by fetch_kucoin.py (data/<SYMBOL>_5min.csv).

FIDELITY NOTES (read these before trusting numbers):
  Replicated faithfully from the live bot:
    - 5m indicators (ta lib, same windows), regime filter, 2/3 reversal filter,
      bullish-divergence, weighted confidence score + MIN_CONFIDENCE gate,
      blended RR gate, time-of-day filter, 24h $vol floor (from candle turnover),
      BTC market-regime gate + BTC-bias gate, 1h HTF bias (resampled), and the
      full 30/40/30 + SL->BE + ATR-trailing + TP3 exit logic with $-accounting.
  Neutralized (no reliable history): funding rate=0, Fear&Greed=50, news=NEUTRAL.
      These are small/zero-weight inputs; neutralizing is conservative.
  Fill model (documented assumptions, deliberately pessimistic):
    - Entry at the NEXT bar's OPEN after the signal bar (no look-ahead).
    - Each later bar resolves at most ONE exit leg, priority [SL, TP1, TP2,
      TP3/trail, time-exit]; level crossings detected via bar high/low.
    - If SL and a TP both fall inside one bar, SL is taken first (pessimistic).
    - SLIPPAGE_BPS applied against you on every fill; 0.1% taker fee per side.
  Not modeled: the 2-position cap, cross-coin correlation, min-lot rounding
      (backtest uses a large notional so lot rounding is negligible). This is a
      per-coin expectancy test, by design.
"""
import os, sys, glob, math, argparse
import numpy as np, pandas as pd
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.trend import EMAIndicator, MACD, ADXIndicator
from ta.volatility import BollingerBands, AverageTrueRange

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

# ── strategy constants (kept in sync with the live bot) ──
KUCOIN_FEE_RATE = 0.001
SLIPPAGE_BPS    = 5.0            # 5 bps adverse slippage per fill (tune to taste)
MIN_CONFIDENCE  = 62
MIN_RR_RATIO    = 2
RSI_OVERSOLD, RSI_OVERBOUGHT = 35, 65
ADX_TRENDING    = 20
MIN_VOLUME_24H  = 500_000
MAX_ADX_FOR_ENTRY, MAX_ATR_PCT_FOR_ENTRY = 35, 0.025
MIN_BB_WIDTH_FOR_ENTRY, MAX_BB_WIDTH_FOR_ENTRY = 0.005, 0.08
ATR_SL_MULTIPLIER = 1.5
ATR_TP1_MULTIPLIER, ATR_TP2_MULTIPLIER, ATR_TP3_MULTIPLIER = 2.5, 4.5, 7.0
ATR_TRAIL_MULTIPLIER = 1.0
MIN_SL_PCT, MAX_SL_PCT = 0.005, 0.025
TP1_SELL_PCT, TP2_SELL_PCT = 0.30, 0.40
CONF_W = dict(technical=0.45, regime=0.20, volume=0.15, momentum=0.20, news=0.00)
USE_TIME_FILTER = True
AVOID_HOURS_UTC = {1, 4, 6, 9, 13, 14, 15, 22}
COOLDOWN_BARS   = 1             # 300s cooldown ~= 1 five-min bar
NOTIONAL        = 1000.0        # backtest position size (returns are %-based, size-independent)


def load(symbol):
    p = os.path.join(DATA_DIR, "{}_5min.csv".format(symbol))
    if not os.path.exists(p):
        return None
    df = pd.read_csv(p).sort_values("time").reset_index(drop=True)
    return df if len(df) > 300 else None


def add_indicators(df):
    c, h, l, v = df["close"], df["high"], df["low"], df["volume"]
    df["rsi"]    = RSIIndicator(c, 14).rsi()
    st = StochasticOscillator(h, l, c)
    df["stoch_k"], df["stoch_d"] = st.stoch(), st.stoch_signal()
    df["ema9"]  = EMAIndicator(c, 9).ema_indicator()
    df["ema21"] = EMAIndicator(c, 21).ema_indicator()
    df["ema50"] = EMAIndicator(c, 50).ema_indicator()
    m = MACD(c); df["macd_diff"] = m.macd_diff()
    df["adx"]   = ADXIndicator(h, l, c, 14).adx()
    atr = AverageTrueRange(h, l, c, 14).average_true_range()
    df["atr"]   = atr; df["atr_pct"] = atr / c
    bb = BollingerBands(c, 20, 2)
    df["bb_lower"], df["bb_mid"] = bb.bollinger_lband(), bb.bollinger_mavg()
    df["bb_width"] = (bb.bollinger_hband() - bb.bollinger_lband()) / df["bb_mid"]
    tp = (h + l + c) / 3
    df["vwap"] = (tp * v).cumsum() / v.cumsum().replace(0, np.nan)
    df["vol_ma20"]  = v.rolling(20).mean()
    df["vol_ratio"] = (v / df["vol_ma20"]).replace([np.inf, -np.inf], np.nan).fillna(1.0)
    df["price_accel"] = c.diff().diff()
    df["vol24"] = df["turnover"].rolling(288, min_periods=50).sum()   # ~24h $volume
    return df


def hourly(df):
    """Resample 5m -> 1h; return per-hour rows keyed by CLOSE time (start+3600)."""
    idx = pd.to_datetime(df["time"], unit="s")
    g = df.set_index(idx).resample("1h")
    o = g["open"].first(); hi = g["high"].max(); lo = g["low"].min()
    cl = g["close"].last()
    H = pd.DataFrame({"open": o, "high": hi, "low": lo, "close": cl}).dropna()
    H["close_ts"] = (H.index.astype("int64") // 10**9) + 3600
    c = H["close"]
    H["ema9"]  = EMAIndicator(c, 9).ema_indicator()
    H["ema21"] = EMAIndicator(c, 21).ema_indicator()
    H["ema50"] = EMAIndicator(c, 50).ema_indicator()
    H["ema200"]= EMAIndicator(c, 200).ema_indicator()
    H["rsi"]   = RSIIndicator(c, 14).rsi()
    H["macd_diff"] = MACD(c).macd_diff()
    H["atr_pct"] = AverageTrueRange(H["high"], H["low"], c, 14).average_true_range() / c
    bb = BollingerBands(c, 20)
    H["bb_width"] = (bb.bollinger_hband() - bb.bollinger_lband()) / c
    return H.reset_index(drop=True)


def btc_regime_bias(H):
    """Port of get_market_regime / get_btc_bias on BTC hourly rows."""
    reg, bias = [], []
    for _, r in H.iterrows():
        if any(pd.isna(r[k]) for k in ("ema50", "rsi", "macd_diff", "atr_pct", "bb_width")):
            reg.append("SIDEWAYS"); bias.append("NEUTRAL"); continue
        if r["atr_pct"] > 0.03 or r["bb_width"] > 0.08:
            g = "HIGH_VOLATILITY"
        else:
            ema200 = r["ema200"] if not pd.isna(r["ema200"]) else r["ema50"]
            bull = sum([r["close"] > r["ema50"], r["close"] > ema200,
                        r["rsi"] > 55, r["macd_diff"] > 0])
            g = ("STRONG_BULL" if bull == 4 else "BULL" if bull >= 3
                 else "BEAR" if bull <= 1 else "SIDEWAYS")
        reg.append(g)
        bias.append("BULLISH" if g in ("STRONG_BULL", "BULL")
                    else "BEARISH" if g == "BEAR" else "NEUTRAL")
    H = H.copy(); H["regime"] = reg; H["btc_bias"] = bias
    return H[["close_ts", "regime", "btc_bias"]]


def htf_bias_series(H):
    out = []
    for _, r in H.iterrows():
        if any(pd.isna(r[k]) for k in ("ema9", "ema21", "ema50", "macd_diff", "rsi")):
            out.append("NEUTRAL"); continue
        bull = sum([r["ema9"] > r["ema21"], r["ema21"] > r["ema50"],
                    r["macd_diff"] > 0, r["rsi"] > 50])
        out.append("BULLISH" if bull >= 3 else "BEARISH" if bull <= 1 else "NEUTRAL")
    H = H.copy(); H["htf_bias"] = out
    return H[["close_ts", "htf_bias"]]


def asof_merge(df, feat):
    return pd.merge_asof(df.sort_values("time"), feat.sort_values("close_ts"),
                         left_on="time", right_on="close_ts", direction="backward")


def detect_div(window):
    if len(window) < 5: return False
    lows = window["low"].nsmallest(2).index.tolist()
    if len(lows) < 2: return False
    lows.sort(); i1, i2 = lows
    return (window.loc[i2, "low"] < window.loc[i1, "low"] and
            window.loc[i2, "rsi"] > window.loc[i1, "rsi"])


def confidence(df, i, regime5m, htf_bias):
    """Port of calculate_confidence_weighted (funding=0, fng=50, news neutral)."""
    r = df.iloc[i]; price = r["close"]; rsi = r["rsi"]
    tech = 0
    if   rsi < 25:            tech += 30
    elif rsi < RSI_OVERSOLD:  tech += 22
    elif rsi < 40:            tech += 12
    elif rsi > RSI_OVERBOUGHT:tech -= 10
    if r["macd_diff"] > 0 and df.iloc[i-1]["macd_diff"] <= 0: tech += 20
    elif r["macd_diff"] > 0:  tech += 10
    elif r["macd_diff"] < 0:  tech -= 5
    if   r["ema9"] > r["ema21"] > r["ema50"]: tech += 20
    elif r["ema9"] > r["ema21"]:              tech += 10
    if   price <= r["bb_lower"]: tech += 15
    elif price <  r["bb_mid"]:   tech += 8
    if not pd.isna(r["vwap"]):
        if price < r["vwap"] * 0.998: tech += 10
        elif price < r["vwap"]:       tech += 5
    if detect_div(df.iloc[max(0, i-19):i+1]): tech += 5
    if r["stoch_k"] < 20 and r["stoch_d"] < 20: tech += 5
    tech = max(0, min(100, tech))

    reg = 50
    if   htf_bias == "BULLISH": reg += 20
    elif htf_bias == "BEARISH": reg -= 25
    if   regime5m == "RANGING":      reg += 15
    elif regime5m == "TRENDING_UP":  reg += 10
    elif regime5m == "VOLATILE":     reg -= 15
    elif regime5m == "TRENDING_DOWN":reg -= 30
    # funding=0 -> no change ; fng=50 -> no change
    reg = max(0, min(100, reg))

    vr = r["vol_ratio"]
    vol = (100 if vr >= 3 else 80 if vr >= 2 else 60 if vr >= 1.5
           else 45 if vr >= 1.0 else 10 if vr < 0.7 else 30)

    mom = 50
    rc = rsi - df.iloc[i-2]["rsi"]
    if   rc > 5:  mom += 20
    elif rc > 2:  mom += 10
    elif rc < -5: mom -= 15
    if r["macd_diff"] > 0: mom += min(20, abs(r["macd_diff"]) * 1000)
    if not pd.isna(r["price_accel"]) and r["price_accel"] > 0: mom += 10
    mom = max(0, min(100, mom))

    news = 50
    final = (tech*CONF_W["technical"] + reg*CONF_W["regime"] + vol*CONF_W["volume"]
             + mom*CONF_W["momentum"] + news*CONF_W["news"])
    return int(max(0, min(100, final)))


def regime5m(df, i):
    r = df.iloc[i]
    if i < 10 or pd.isna(r["ema50"]): return "RANGING"
    slope = (r["ema50"] - df.iloc[i-10]["ema50"]) / df.iloc[i-10]["ema50"]
    if r["bb_width"] > 0.06: return "VOLATILE"
    if r["adx"] < ADX_TRENDING: return "RANGING"
    return "TRENDING_UP" if slope > 0 else "TRENDING_DOWN"


def passes_regime(r):
    return (r["adx"] <= MAX_ADX_FOR_ENTRY and r["atr_pct"] <= MAX_ATR_PCT_FOR_ENTRY
            and MIN_BB_WIDTH_FOR_ENTRY <= r["bb_width"] <= MAX_BB_WIDTH_FOR_ENTRY)


def passes_reversal(df, i):
    a, b, c = df.iloc[i], df.iloc[i-1], df.iloc[i-2]
    conf = sum([a["rsi"] > b["rsi"], a["close"] > a["open"],
                min(a["low"], b["low"]) >= c["low"] * 0.998])
    return conf >= 2


def slip(price, side):
    s = SLIPPAGE_BPS / 10000.0
    return price * (1 + s) if side == "buy" else price * (1 - s)


def simulate_trade(entry_fill, atr, future):
    """
    Replays the 30/40/30 + SL->BE + ATR-trail + TP3 exits over `future` bars.
    Returns (realized_usd, trade_return, bars_held, exit_reason). Pure + testable.
    """
    sl_pct = max(MIN_SL_PCT, min(MAX_SL_PCT, ATR_SL_MULTIPLIER * atr / entry_fill))
    sl  = entry_fill * (1 - sl_pct)
    tp1 = entry_fill * (1 + ATR_TP1_MULTIPLIER * atr / entry_fill)
    tp2 = entry_fill * (1 + ATR_TP2_MULTIPLIER * atr / entry_fill)
    tp3 = entry_fill * (1 + ATR_TP3_MULTIPLIER * atr / entry_fill)
    orig_size  = NOTIONAL / entry_fill
    orig_funds = NOTIONAL
    entry_fee  = NOTIONAL * KUCOIN_FEE_RATE
    realized   = 0.0
    remaining  = orig_size
    tp1_hit = tp2_hit = False
    trail = None
    held = 0

    def book(px, size, reason):
        nonlocal realized
        fill = slip(px, "sell")
        gross = (fill - entry_fill) * size
        exit_fee = size * fill * KUCOIN_FEE_RATE
        ent_fee  = entry_fee * (size / orig_size)
        realized += gross - exit_fee - ent_fee
        return reason

    for k in range(len(future)):
        bar = future.iloc[k]; held = k + 1
        hi, lo, cl = bar["high"], bar["low"], bar["close"]
        if tp1_hit and not tp2_hit and sl < entry_fill * 1.001:   # SL->BE after TP1
            sl = entry_fill * 1.001
        if tp2_hit:                                                # trailing after TP2
            t = cl - ATR_TRAIL_MULTIPLIER * atr
            trail = t if trail is None else max(trail, t)
        # one event per bar, SL first (pessimistic)
        if lo <= sl:
            book(sl, remaining, "SL/BE"); return realized, realized/orig_funds, held, "SL/BE"
        if trail is not None and lo <= trail:
            book(trail, remaining, "TRAIL"); return realized, realized/orig_funds, held, "TRAIL"
        if not tp1_hit and hi >= tp1:
            book(tp1, orig_size*TP1_SELL_PCT, "TP1"); remaining -= orig_size*TP1_SELL_PCT
            tp1_hit = True; continue
        if tp1_hit and not tp2_hit and hi >= tp2:
            book(tp2, orig_size*TP2_SELL_PCT, "TP2"); remaining -= orig_size*TP2_SELL_PCT
            tp2_hit = True; continue
        if tp2_hit and hi >= tp3:
            book(tp3, remaining, "TP3"); return realized, realized/orig_funds, held, "TP3"
    # ran out of data -> close at last close
    book(future.iloc[-1]["close"], remaining, "EOD")
    return realized, realized / orig_funds, held, "EOD"


def backtest_symbol(symbol, btc_feat):
    df = load(symbol)
    if df is None: return None, []
    df = add_indicators(df)
    Hc = hourly(df)
    df = asof_merge(df, htf_bias_series(Hc))
    df = asof_merge(df, btc_feat)
    df["hour"] = (pd.to_datetime(df["time"], unit="s").dt.hour)
    df = df.reset_index(drop=True)

    trades = []
    i = 60
    n = len(df)
    while i < n - 1:
        r = df.iloc[i]
        if any(pd.isna(r[k]) for k in ("rsi","adx","atr","bb_width","ema50","vwap")):
            i += 1; continue
        # ── entry gates (mirror live order) ──
        if USE_TIME_FILTER and r["hour"] in AVOID_HOURS_UTC:           i += 1; continue
        if r.get("regime") == "HIGH_VOLATILITY":                       i += 1; continue
        if r.get("btc_bias") == "BEARISH":                             i += 1; continue
        if (r["vol24"] if not pd.isna(r["vol24"]) else 0) < MIN_VOLUME_24H: i += 1; continue
        if not passes_regime(r):                                       i += 1; continue
        if not passes_reversal(df, i):                                 i += 1; continue
        conf = confidence(df, i, regime5m(df, i), r.get("htf_bias", "NEUTRAL"))
        if conf < MIN_CONFIDENCE:                                      i += 1; continue
        atr = r["atr"]; price = r["close"]
        sl_pct = max(MIN_SL_PCT, min(MAX_SL_PCT, ATR_SL_MULTIPLIER*atr/price))
        tp1 = price*(1+ATR_TP1_MULTIPLIER*atr/price)
        tp2 = price*(1+ATR_TP2_MULTIPLIER*atr/price)
        tp3 = price*(1+ATR_TP3_MULTIPLIER*atr/price)
        reward = (TP1_SELL_PCT*(tp1-price)/price + TP2_SELL_PCT*(tp2-price)/price
                  + (1-TP1_SELL_PCT-TP2_SELL_PCT)*(tp3-price)/price)
        if (reward/sl_pct if sl_pct > 0 else 0) < MIN_RR_RATIO:        i += 1; continue
        # ── enter at NEXT bar open ──
        entry_fill = slip(df.iloc[i+1]["open"], "buy")
        future = df.iloc[i+1:].reset_index(drop=True)
        usd, ret, held, why = simulate_trade(entry_fill, atr, future)
        trades.append(dict(symbol=symbol, entry_i=i+1, conf=conf, ret=ret,
                           usd=usd, bars=held, reason=why,
                           time=pd.to_datetime(df.iloc[i+1]["time"], unit="s")))
        i = i + 1 + held + COOLDOWN_BARS      # jump past the trade + cooldown
    return df, trades


def stats(trades, label):
    if not trades:
        print("  {}: no trades".format(label)); return None
    rets = np.array([t["ret"] for t in trades])
    wins = rets[rets > 0]; losses = rets[rets <= 0]
    wr = len(wins)/len(rets)*100
    pf = (wins.sum()/abs(losses.sum())) if losses.sum() != 0 else float("inf")
    exp = rets.mean()*100
    eq = np.cumprod(1+rets); peak = np.maximum.accumulate(eq)
    mdd = ((peak-eq)/peak).max()*100 if len(eq) else 0
    print("  {:<14} trades={:<4} WR={:5.1f}%  PF={:5.2f}  exp/trade={:+.3f}%  "
          "total={:+.1f}%  maxDD={:.1f}%".format(
              label, len(rets), wr, pf, exp, (eq[-1]-1)*100, mdd))
    return dict(trades=len(rets), wr=wr, pf=pf, exp=exp, total=(eq[-1]-1)*100, mdd=mdd)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", type=str, default="")
    args = ap.parse_args()

    btc = load("BTC-USDT")
    if btc is None:
        print("Need data/BTC-USDT_5min.csv (run fetch_kucoin.py first)"); sys.exit(1)
    btc = add_indicators(btc)
    btc_feat = btc_regime_bias(hourly(btc))

    if args.symbols:
        syms = [s.strip() for s in args.symbols.split(",")]
    else:
        syms = sorted(os.path.basename(p).replace("_5min.csv", "")
                      for p in glob.glob(os.path.join(DATA_DIR, "*_5min.csv")))
    syms = [s for s in syms if s != "BTC-USDT"]

    all_trades = []
    print("\nPER-COIN EXPECTANCY")
    for s in syms:
        _, tr = backtest_symbol(s, btc_feat)
        stats(tr, s); all_trades += tr

    print("\nAGGREGATE")
    agg = stats(all_trades, "ALL COINS")
    if all_trades:
        all_trades.sort(key=lambda t: t["time"])
        cut = int(len(all_trades)*0.7)
        print("\nTIME SPLIT (out-of-sample check)")
        stats(all_trades[:cut], "first 70%")
        stats(all_trades[cut:], "last 30%")
        pd.DataFrame(all_trades).to_csv(os.path.join(DATA_DIR, "backtest_trades.csv"), index=False)
        print("\nPer-trade log -> data/backtest_trades.csv")