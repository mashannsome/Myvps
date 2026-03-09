import requests
import pandas as pd
import ta
import time
import os

# =====================
# ENV
# =====================

TWELVE_API = os.getenv("TWELVE_API_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

symbol = "XAU/USD"

last_signal = None
last_signal_time = 0
cooldown = 600

# =====================
# TELEGRAM
# =====================

def send_telegram(msg):

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    requests.post(
        url,
        data={
            "chat_id": CHAT_ID,
            "text": msg
        }
    )

# =====================
# GET DATA
# =====================

def get_data():

    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval=1min&outputsize=200&apikey={TWELVE_API}"

    r = requests.get(url)

    data = r.json()

    df = pd.DataFrame(data["values"])

    df = df.iloc[::-1]

    df["open"] = df["open"].astype(float)
    df["high"] = df["high"].astype(float)
    df["low"] = df["low"].astype(float)
    df["close"] = df["close"].astype(float)

    return df

# =====================
# BOS DETECTION
# =====================

def break_of_structure(df):

    last = df.iloc[-1]
    prev = df.iloc[-2]

    if last["high"] > prev["high"]:
        return "BUY"

    if last["low"] < prev["low"]:
        return "SELL"

    return None

# =====================
# LIQUIDITY SWEEP
# =====================

def liquidity_sweep(df):

    last = df.iloc[-1]
    prev = df.iloc[-2]

    if last["high"] > prev["high"] and last["close"] < prev["high"]:
        return "SELL"

    if last["low"] < prev["low"] and last["close"] > prev["low"]:
        return "BUY"

    return None

# =====================
# SIGNAL LOGIC
# =====================

def check_signal():

    global last_signal
    global last_signal_time

    if time.time() - last_signal_time < cooldown:
        return

    df = get_data()

    df["ema20"] = ta.trend.ema_indicator(df["close"],20)
    df["ema50"] = ta.trend.ema_indicator(df["close"],50)

    df["rsi"] = ta.momentum.rsi(df["close"],14)

    last = df.iloc[-1]

    price = last["close"]

    trend = None

    if last["ema20"] > last["ema50"]:
        trend = "BUY"

    if last["ema20"] < last["ema50"]:
        trend = "SELL"

    bos = break_of_structure(df)

    sweep = liquidity_sweep(df)

    # BUY
    if trend == "BUY" and bos == "BUY" and sweep != "SELL" and last["rsi"] > 55:

        if last_signal != "BUY":

            msg=f"""
🚀 XAUUSD BUY

Entry : {price}
SL : {round(price-3,2)}
TP : {round(price+6,2)}

Strategy:
Trend EMA
Break Of Structure
RSI Momentum
"""

            send_telegram(msg)

            last_signal="BUY"
            last_signal_time=time.time()

    # SELL
    if trend == "SELL" and bos == "SELL" and sweep != "BUY" and last["rsi"] < 45:

        if last_signal != "SELL":

            msg=f"""
🚀 XAUUSD SELL

Entry : {price}
SL : {round(price+3,2)}
TP : {round(price-6,2)}

Strategy:
Trend EMA
Break Of Structure
RSI Momentum
"""

            send_telegram(msg)

            last_signal="SELL"
            last_signal_time=time.time()

# =====================
# MAIN LOOP
# =====================

print("XAUUSD BOT STARTED")

send_telegram("🚀 XAUUSD BOT RUNNING (RAILWAY)")

while True:

    try:

        check_signal()

    except Exception as e:

        print("ERROR:", e)

    time.sleep(60)
