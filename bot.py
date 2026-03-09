import websocket
import json
import pandas as pd
import ta
import requests
import os
import time
from datetime import datetime, UTC

POLYGON_API_KEY = os.getenv("POLYGON_API_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

symbol = "C:XAUUSD"

price_data = []
max_data = 500

last_signal_time = 0
cooldown = 300

# =====================
# TELEGRAM
# =====================

def send_telegram(msg):

    try:

        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

        requests.post(
            url,
            data={"chat_id": CHAT_ID, "text": msg},
            timeout=10
        )

        print("SIGNAL SENT")

    except Exception as e:

        print(e)

# =====================
# SESSION FILTER
# =====================

def session_active():

    hour = datetime.now(UTC).hour

    if hour < 6 or hour > 16:
        return False

    return True

# =====================
# BUILD DF
# =====================

def get_df():

    df = pd.DataFrame(price_data)

    df["datetime"] = pd.to_datetime(df["datetime"])

    df.set_index("datetime", inplace=True)

    return df

# =====================
# TREND
# =====================

def get_trend(df):

    df15 = df.resample("15T").agg({"price":"last"}).dropna()

    if len(df15) < 50:
        return None

    df15["ema20"] = ta.trend.ema_indicator(df15["price"],20)
    df15["ema50"] = ta.trend.ema_indicator(df15["price"],50)

    last = df15.iloc[-1]

    if last["ema20"] > last["ema50"]:
        return "BUY"

    if last["ema20"] < last["ema50"]:
        return "SELL"

    return None

# =====================
# LIQUIDITY SWEEP
# =====================

def liquidity_sweep(df):

    last = df.iloc[-1]
    prev = df.iloc[-2]

    if last["price"] > prev["price"] * 1.0005 and last["price"] < prev["price"]:
        return "SELL"

    if last["price"] < prev["price"] * 0.9995 and last["price"] > prev["price"]:
        return "BUY"

    return None

# =====================
# ENTRY
# =====================

def check_entry():

    global last_signal_time

    if not session_active():
        return

    if len(price_data) < 100:
        return

    if time.time() - last_signal_time < cooldown:
        return

    df = get_df()

    df["ema3"] = ta.trend.ema_indicator(df["price"],3)
    df["ema8"] = ta.trend.ema_indicator(df["price"],8)

    df["rsi"] = ta.momentum.rsi(df["price"],7)

    last = df.iloc[-1]
    prev = df.iloc[-2]

    trend = get_trend(df)

    sweep = liquidity_sweep(df)

    entry = last["price"]

    if trend == "BUY" and sweep == "BUY":

        if last["ema3"] > last["ema8"] and last["price"] > prev["price"]:

            sl = round(entry - 3,2)
            tp = round(entry + 6,2)

            send_telegram(
f"""
🚀 XAUUSD BUY

Entry : {entry}
SL : {sl}
TP : {tp}

RR 1:2
AI Liquidity Strategy
"""
)

            last_signal_time = time.time()

    if trend == "SELL" and sweep == "SELL":

        if last["ema3"] < last["ema8"] and last["price"] < prev["price"]:

            sl = round(entry + 3,2)
            tp = round(entry - 6,2)

            send_telegram(
f"""
🚀 XAUUSD SELL

Entry : {entry}
SL : {sl}
TP : {tp}

RR 1:2
AI Liquidity Strategy
"""
)

            last_signal_time = time.time()

# =====================
# WEBSOCKET
# =====================

def on_message(ws, message):

    global price_data

    data = json.loads(message)

    for item in data:

        if item["ev"] == "C":

            price = item["p"]

            price_data.append({
                "datetime": datetime.now(UTC),
                "price": price
            })

            if len(price_data) > max_data:
                price_data.pop(0)

            check_entry()

def on_open(ws):

    print("CONNECTED")

    ws.send(json.dumps({
        "action": "auth",
        "params": POLYGON_API_KEY
    }))

    ws.send(json.dumps({
        "action": "subscribe",
        "params": symbol
    }))

def start_ws():

    ws = websocket.WebSocketApp(
        "wss://socket.polygon.io/forex",
        on_open=on_open,
        on_message=on_message
    )

    ws.run_forever()

# =====================
# MAIN
# =====================

send_telegram("🚀 XAUUSD AI SCALPING BOT STARTED")

while True:

    try:

        start_ws()

    except Exception as e:

        print("RECONNECTING...", e)

        time.sleep(5)
