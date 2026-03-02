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
        requests.post(url, data=data)
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
        df = df.iloc[::-1]  # reverse biar urut lama ke baru
        df["close"] = df["close"].astype(float)

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
# ENTRY 5M SETUP
# ========================
def check_entry_5m(df_1m, trend):

    df_5m = df_1m.groupby(df_1m.index // 5).last()

    if len(df_5m) < 30:
        return

    df_5m["ema9"] = ta.trend.ema_indicator(df_5m["close"], window=9)
    df_5m["ema21"] = ta.trend.ema_indicator(df_5m["close"], window=21)
    df_5m["rsi"] = ta.momentum.rsi(df_5m["close"], window=14)

    last = df_5m.iloc[-1]
    prev = df_5m.iloc[-2]

    entry = round(last["close"], 2)

    # BUY CONDITION
    if trend == "BUY":
        if (
            last["ema9"] > last["ema21"] and
            45 < last["rsi"] < 60 and
            last["close"] > prev["close"]
        ):
            sl = round(entry - 4, 2)
            tp = round(entry + 8, 2)

            send_telegram(
                f"🔥 XAUUSD BUY (5M Pullback)\n"
                f"Entry: {entry}\n"
                f"SL: {sl}\n"
                f"TP: {tp}\n"
                f"RR 1:2"
            )

    # SELL CONDITION
    if trend == "SELL":
        if (
            last["ema9"] < last["ema21"] and
            40 < last["rsi"] < 55 and
            last["close"] < prev["close"]
        ):
            sl = round(entry + 4, 2)
            tp = round(entry - 8, 2)

            send_telegram(
                f"🔥 XAUUSD SELL (5M Pullback)\n"
                f"Entry: {entry}\n"
                f"SL: {sl}\n"
                f"TP: {tp}\n"
                f"RR 1:2"
            )

# ========================
# MAIN LOOP
# ========================
send_telegram("🚀 XAUUSD PRO 5M Bot Aktif (TwelveData)")

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

        time.sleep(60)

    except Exception as e:
        print("MAIN ERROR:", e)
        time.sleep(60)
