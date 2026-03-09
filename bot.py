import requests
import pandas as pd
import ta
import time
import os
import warnings
from datetime import datetime, UTC

warnings.filterwarnings("ignore")

# =========================
# ENV
# =========================
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
API_KEY = os.getenv("TWELVE_API_KEY")

# =========================
# GLOBAL CONFIG
# =========================
last_signal_time = 0
cooldown = 300

# =========================
# LOG FUNCTION
# =========================
def log(msg):

    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")

    print(f"[{now}] {msg}")

# =========================
# TELEGRAM
# =========================
def send_telegram(msg):

    try:

        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

        requests.post(
            url,
            data={"chat_id": CHAT_ID, "text": msg},
            timeout=10
        )

        log("SIGNAL SENT")

    except Exception as e:

        log(f"TELEGRAM ERROR: {e}")

# =========================
# SESSION FILTER
# =========================
def session_filter():

    hour = datetime.now(UTC).hour

    if hour < 6 or hour > 16:
        return False

    return True

# =========================
# GET MARKET DATA
# =========================
def get_data():

    try:

        url = "https://api.twelvedata.com/time_series"

        params = {
            "symbol": "XAU/USD",
            "interval": "1min",
            "outputsize": 500,
            "apikey": API_KEY
        }

        r = requests.get(url, params=params, timeout=15)

        if r.status_code != 200:
            log(f"HTTP ERROR {r.status_code}")
            return None

        data = r.json()

        if "values" not in data:
            log("INVALID DATA")
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

    except Exception as e:

        log(f"DATA ERROR: {e}")

        return None

# =========================
# TREND DETECTION
# =========================
def get_trend(df):

    try:

        df15 = df.resample("15min").agg({
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last"
        }).dropna()

        if len(df15) < 60:
            return None

        df15["ema20"] = ta.trend.ema_indicator(df15["close"], 20)
        df15["ema50"] = ta.trend.ema_indicator(df15["close"], 50)

        df15["adx"] = ta.trend.adx(
            df15["high"],
            df15["low"],
            df15["close"],
            14
        )

        last = df15.iloc[-1]

        if last["ema20"] > last["ema50"] and last["adx"] > 20:
            return "BUY"

        if last["ema20"] < last["ema50"] and last["adx"] > 20:
            return "SELL"

        return None

    except Exception as e:

        log(f"TREND ERROR: {e}")
        return None

# =========================
# LIQUIDITY SWEEP
# =========================
def liquidity_sweep(df):

    try:

        last = df.iloc[-1]
        prev = df.iloc[-2]

        if last["high"] > prev["high"] and last["close"] < prev["high"]:
            return "SELL"

        if last["low"] < prev["low"] and last["close"] > prev["low"]:
            return "BUY"

        return None

    except:

        return None

# =========================
# ENTRY SIGNAL
# =========================
def check_entry(df, trend):

    global last_signal_time

    try:

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

        # BUY
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

        # SELL
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

    except Exception as e:

        log(f"ENTRY ERROR: {e}")

# =========================
# BOT START
# =========================
send_telegram("🚀 XAUUSD SCALPING BOT STABLE VPS STARTED")

# =========================
# MAIN LOOP
# =========================
while True:

    try:

        log("BOT RUNNING")

        if not session_filter():

            log("SESSION CLOSED")

            time.sleep(60)

            continue

        df = get_data()

        if df is None:

            log("DATA EMPTY")

            time.sleep(60)

            continue

        trend = get_trend(df)

        log(f"TREND: {trend}")

        if trend:

            check_entry(df, trend)

        time.sleep(60)

    except Exception as e:

        log(f"MAIN LOOP ERROR: {e}")

        time.sleep(60)
