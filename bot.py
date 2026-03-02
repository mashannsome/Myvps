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

prices = []

def check_signal():
    global prices
    
    price = get_price()
    prices.append(price)

    if len(prices) > 100:
        prices.pop(0)

    df = pd.DataFrame(prices, columns=["close"])
    
    if len(df) < 30:
        return

    df['ema9'] = ta.trend.ema_indicator(df['close'], window=9)
    df['ema21'] = ta.trend.ema_indicator(df['close'], window=21)
    df['rsi'] = ta.momentum.rsi(df['close'], window=14)

    last = df.iloc[-1]
    entry = round(last['close'],2)

    if last['ema9'] > last['ema21'] and last['rsi'] > 55:
        sl = round(entry - 3,2)
        tp = round(entry + 6,2)
        send_telegram(f"🔥 BUY XAUUSD\nEntry: {entry}\nSL: {sl}\nTP: {tp}")

    if last['ema9'] < last['ema21'] and last['rsi'] < 45:
        sl = round(entry + 3,2)
        tp = round(entry - 6,2)
        send_telegram(f"🔥 SELL XAUUSD\nEntry: {entry}\nSL: {sl}\nTP: {tp}")

while True:
    send_telegram("Bot XAUUSD aktif 🚀")
    try:
        check_signal()
        time.sleep(60)
    except:
        time.sleep(60)
