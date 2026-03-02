import requests
import pandas as pd
import ta
import time
import os
from datetime import datetime

# ========================
# ENV VARIABLES
# ========================
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
API_KEY = os.getenv("TWELVE_API_KEY")

# ========================
# TELEGRAM FUNCTION
# ========================
def send_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = {"chat_id": CHAT_ID, "text": message}
        r = requests.post(url, data=data)
        print(f"[TELEGRAM] {r.status_code} | {r.text}")
    except Exception as e:
        print("TELEGRAM ERROR:", e)

# ========================
# GET 1 MINUTE CANDLES
# ========================
def get_1m_candles():
    try:
        url = "https://api.twelvedata.com/time_series"
        params = {
            "symbol": "XAU/USD",
            "interval": "1min",
            "outputsize": 1000,
            "apikey": API_KEY
        }
        r = requests.get(url, params=params, timeout=10)
        if r.status_code != 200:
            print("HTTP ERROR:", r.status_code)
            return None
        data = r.json()
        if "values" not in data:
            print("Invalid response:", data)
            return None
        df = pd.DataFrame(data["values"])
        df = df.iloc[::-1]
        df["close"] = df["close"].astype(float)
        df["high"] = df["high"].astype(float)
        df["low"] = df["low"].astype(float)
        df["open"] = df["open"].astype(float)
        return df
    except Exception as e:
        print("CANDLE ERROR:", e)
        return None

# ========================
# TREND 15M FILTER
# ========================
def get_trend_15m(df_1m):
    df_15m = df_1m.groupby(df_1m.index // 15).last()
    if len(df_15m) < 50:
        return None
    df_15m["ema20"] = ta.trend.ema_indicator(df_15m["close"], window=20)
    df_15m["ema50"] = ta.trend.ema_indicator(df_15m["close"], window=50)
    last = df_15m.iloc[-1]
    if last["ema20"] > last["ema50"]:
        return "BUY"
    elif last["ema20"] < last["ema50"]:
        return "SELL"
    else:
        return None

# ========================
# ENTRY 5M SCALPING
# ========================
def check_entry_5m(df_1m, trend):
    df_5m = df_1m.groupby(df_1m.index // 5).agg({"open":"first","close":"last","high":"max","low":"min"})
    if len(df_5m) < 30:
        return
    df_5m["ema9"] = ta.trend.ema_indicator(df_5m["close"], window=9)
    df_5m["ema21"] = ta.trend.ema_indicator(df_5m["close"], window=21)
    df_5m["rsi"] = ta.momentum.rsi(df_5m["close"], window=14)
    df_5m["atr"] = ta.volatility.average_true_range(df_5m["high"], df_5m["low"], df_5m["close"], window=14)
    macd = ta.trend.MACD(df_5m["close"], window_slow=26, window_fast=12, window_sign=9)
    df_5m["macd"] = macd.macd_diff()
    bb = ta.volatility.BollingerBands(df_5m["close"], window=20, window_dev=2)
    df_5m["bb_high"] = bb.bollinger_hband()
    df_5m["bb_low"] = bb.bollinger_lband()
    
    last = df_5m.iloc[-1]
    prev = df_5m.iloc[-2]
    entry = round(last["close"],2)
    
    # BUY 5M
    if trend=="BUY" and last["ema9"]>last["ema21"] and last["rsi"]>45 and last["macd"]>0 and last["atr"]>0.5 and last["close"]>last["bb_high"]:
        sl = round(entry-4,2)
        tp = round(entry+8,2)
        send_telegram(f"🚀 5M BUY\nEntry:{entry}\nSL:{sl}\nTP:{tp}\nRR 1:2")
    
    # SELL 5M
    if trend=="SELL" and last["ema9"]<last["ema21"] and last["rsi"]<55 and last["macd"]<0 and last["atr"]>0.5 and last["close"]<last["bb_low"]:
        sl = round(entry+4,2)
        tp = round(entry-8,2)
        send_telegram(f"🚀 5M SELL\nEntry:{entry}\nSL:{sl}\nTP:{tp}\nRR 1:2")

# ========================
# ENTRY 1M MICRO SCALPING
# ========================
def check_entry_1m(df_1m, trend):
    df_1m["ema3"] = ta.trend.ema_indicator(df_1m["close"], window=3)
    df_1m["ema8"] = ta.trend.ema_indicator(df_1m["close"], window=8)
    df_1m["rsi"] = ta.momentum.rsi(df_1m["close"], window=7)
    df_1m["atr"] = ta.volatility.average_true_range(df_1m["high"], df_1m["low"], df_1m["close"], window=14)
    
    last = df_1m.iloc[-1]
    prev = df_1m.iloc[-2]
    entry = round(last["close"],2)
    
    # BUY 1M
    if trend=="BUY" and last["ema3"]>last["ema8"] and last["close"]>prev["close"] and 45<last["rsi"]<65 and last["atr"]>0.3:
        sl = round(entry-2,2)
        tp = round(entry+4,2)
        send_telegram(f"⚡ 1M BUY\nEntry:{entry}\nSL:{sl}\nTP:{tp}\nRR 1:2")
    
    # SELL 1M
    if trend=="SELL" and last["ema3"]<last["ema8"] and last["close"]<prev["close"] and 35<last["rsi"]<55 and last["atr"]>0.3:
        sl = round(entry+2,2)
        tp = round(entry-4,2)
        send_telegram(f"⚡ 1M SELL\nEntry:{entry}\nSL:{sl}\nTP:{tp}\nRR 1:2")

# ========================
# MAIN LOOP
# ========================
send_telegram("🚀 XAUUSD ULTRA Dual-Timeframe Bot Aktif")

while True:
    try:
        df = get_1m_candles()
        if df is None:
            time.sleep(60)
            continue
        trend = get_trend_15m(df)
        print("Trend:", trend)
        if trend:
            check_entry_5m(df, trend)
            check_entry_1m(df, trend)
        time.sleep(60)
    except Exception as e:
        print("MAIN ERROR:", e)
        time.sleep(60)
