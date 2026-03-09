import requests
import pandas as pd
import ta
import time
import os
from datetime import datetime

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
API_KEY = os.getenv("TWELVE_API_KEY")

last_signal_time = 0
cooldown = 300


def send_telegram(msg):

    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

        requests.post(url, data={
            "chat_id": CHAT_ID,
            "text": msg
        })

        print("SIGNAL SENT")

    except Exception as e:
        print(e)


def session_filter():

    hour = datetime.utcnow().hour

    if hour < 6 or hour > 16:
        return False

    return True


def get_data():

    url = "https://api.twelvedata.com/time_series"

    params = {
        "symbol": "XAU/USD",
        "interval": "1min",
        "outputsize": 1000,
        "apikey": API_KEY
    }

    r = requests.get(url, params=params)

    data = r.json()

    if "values" not in data:
        return None

    df = pd.DataFrame(data["values"])

    df = df.iloc[::-1]

    df["datetime"] = pd.to_datetime(df["datetime"])

    df["open"] = df["open"].astype(float)
    df["high"] = df["high"].astype(float)
    df["low"] = df["low"].astype(float)
    df["close"] = df["close"].astype(float)

    df.set_index("datetime", inplace=True)

    return df


def get_trend(df):

    df15 = df.resample("15T").agg({
        "open":"first",
        "high":"max",
        "low":"min",
        "close":"last"
    }).dropna()

    df15["ema20"] = ta.trend.ema_indicator(df15["close"],20)
    df15["ema50"] = ta.trend.ema_indicator(df15["close"],50)
    df15["adx"] = ta.trend.adx(df15["high"],df15["low"],df15["close"],14)

    last = df15.iloc[-1]

    if last["ema20"] > last["ema50"] and last["adx"] > 20:
        return "BUY"

    if last["ema20"] < last["ema50"] and last["adx"] > 20:
        return "SELL"

    return None


def liquidity_sweep(df):

    last = df.iloc[-1]
    prev = df.iloc[-2]

    if last["high"] > prev["high"] and last["close"] < prev["high"]:
        return "SELL"

    if last["low"] < prev["low"] and last["close"] > prev["low"]:
        return "BUY"

    return None


def check_entry(df, trend):

    global last_signal_time

    if time.time() - last_signal_time < cooldown:
        return

    df["ema3"] = ta.trend.ema_indicator(df["close"],3)
    df["ema8"] = ta.trend.ema_indicator(df["close"],8)

    df["rsi"] = ta.momentum.rsi(df["close"],7)

    df["atr"] = ta.volatility.average_true_range(
        df["high"],
        df["low"],
        df["close"],
        14
    )

    last = df.iloc[-1]
    prev = df.iloc[-2]

    entry = last["close"]
    atr = last["atr"]

    sweep = liquidity_sweep(df)

    if trend == "BUY" and sweep == "BUY":

        if last["ema3"] > last["ema8"] and last["close"] > prev["high"]:

            sl = round(entry - atr*1.5,2)
            tp = round(entry + atr*3,2)

            send_telegram(
f"""
🚀 XAUUSD BUY

Entry : {entry}
SL : {sl}
TP : {tp}

RR 1:2
Strategy : Liquidity Sweep
"""
)

            last_signal_time = time.time()


    if trend == "SELL" and sweep == "SELL":

        if last["ema3"] < last["ema8"] and last["close"] < prev["low"]:

            sl = round(entry + atr*1.5,2)
            tp = round(entry - atr*3,2)

            send_telegram(
f"""
🚀 XAUUSD SELL

Entry : {entry}
SL : {sl}
TP : {tp}

RR 1:2
Strategy : Liquidity Sweep
"""
)

            last_signal_time = time.time()


send_telegram("🚀 XAUUSD SCALPING BOT V3 AKTIF")


while True:

    try:

        if not session_filter():
            print("SESSION OFF")
            time.sleep(60)
            continue

        df = get_data()

        if df is None:
            time.sleep(60)
            continue

        trend = get_trend(df)

        print("TREND:",trend)

        if trend:

            check_entry(df,trend)

        time.sleep(60)

    except Exception as e:

        print("ERROR:",e)

        time.sleep(60)
