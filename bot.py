import requests
import pandas as pd
import ta
import time
import os

TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message}
    requests.post(url, data=data)

def get_price():
    url = "https://api.gold-api.com/price/XAUUSD"
    r = requests.get(url)
    return r.json()["price"]

prices_1m = []

def get_trend_15m():
    if len(prices_1m) < 200:
        return None

    df = pd.DataFrame(prices_1m[-150:], columns=["close"])
    df_15m = df.groupby(df.index // 15).last()

    df_15m['ema50'] = ta.trend.ema_indicator(df_15m['close'], window=50)
    df_15m['ema200'] = ta.trend.ema_indicator(df_15m['close'], window=200)

    last = df_15m.iloc[-1]

    if last['ema50'] > last['ema200']:
        return "BUY"
    elif last['ema50'] < last['ema200']:
        return "SELL"
    else:
        return None

def check_entry_5m(trend):
    if len(prices_1m) < 100:
        return

    df = pd.DataFrame(prices_1m[-75:], columns=["close"])
    df_5m = df.groupby(df.index // 5).last()

    df_5m['ema9'] = ta.trend.ema_indicator(df_5m['close'], window=9)
    df_5m['ema21'] = ta.trend.ema_indicator(df_5m['close'], window=21)
    df_5m['rsi'] = ta.momentum.rsi(df_5m['close'], window=14)

    last = df_5m.iloc[-1]
    prev = df_5m.iloc[-2]

    entry = round(last['close'], 2)

    if trend == "BUY":
        if (last['ema9'] > last['ema21'] and
            45 < last['rsi'] < 60 and
            last['close'] > prev['close']):
            
            sl = round(entry - 4, 2)
            tp = round(entry + 8, 2)

            send_telegram(
                f"🔥 XAUUSD BUY (5M Pullback)\n"
                f"Entry: {entry}\n"
                f"SL: {sl}\n"
                f"TP: {tp}\n"
                f"RR 1:2"
            )

    if trend == "SELL":
        if (last['ema9'] < last['ema21'] and
            40 < last['rsi'] < 55 and
            last['close'] < prev['close']):
            
            sl = round(entry + 4, 2)
            tp = round(entry - 8, 2)

            send_telegram(
                f"🔥 XAUUSD SELL (5M Pullback)\n"
                f"Entry: {entry}\n"
                f"SL: {sl}\n"
                f"TP: {tp}\n"
                f"RR 1:2"
            )

send_telegram("🚀 XAUUSD PRO 5M Bot Aktif")

while True:
    try:
        price = get_price()
        prices_1m.append(price)

        if len(prices_1m) > 500:
            prices_1m.pop(0)

        trend = get_trend_15m()

        if trend:
            check_entry_5m(trend)

        time.sleep(60)

    except:
        time.sleep(60)
