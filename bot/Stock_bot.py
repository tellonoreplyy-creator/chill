import yfinance as yf
import pandas as pd
import requests
import time
from datetime import datetime

# ===== CONFIG =====
TICKERS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "NVDA", "NFLX", "BRK-B", "JPM",
    "V", "MA", "DIS", "KO", "PEP", "PG", "UNH", "HD", "MCD", "INTC", "AMD", "ADBE",
    "CRM", "PYPL", "CSCO", "T", "VZ"
]

SHORT_WINDOW = 5
LONG_WINDOW = 20
LOOKAHEAD_DAYS = 3
CHECK_INTERVAL = 60 * 10  # every 10 minutes
SUGGESTED_BUY_AMOUNT = 50.0

TELEGRAM_TOKEN = "8252454918:AAHBkWLEj_v8ZL_y8MqL8pzlteX_9RjMb9Q"
CHAT_ID = 5520281230  # your Telegram chat ID


# ===== TELEGRAM ALERT =====
def send_alert(message: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        r = requests.post(url, data=data)
        print(f"[DEBUG] Telegram → {r.status_code}: {r.text}")
    except Exception as e:
        print("❌ Telegram send failed:", e)


# ===== ACCURACY CALCULATION =====
def crossover_accuracy(data: pd.DataFrame, short_window=5, long_window=20, lookahead=3) -> float:
    """
    Measure how often historical BUY crossovers were profitable.
    """
    data = data.copy()
    data["MA_Short"] = data["Close"].rolling(short_window).mean()
    data["MA_Long"] = data["Close"].rolling(long_window).mean()

    success, total = 0, 0
    for i in range(long_window, len(data) - lookahead):
        if data["MA_Short"].iloc[i] > data["MA_Long"].iloc[i] and data["MA_Short"].iloc[i - 1] <= data["MA_Long"].iloc[i - 1]:
            total += 1
            future_max = data["Close"].iloc[i + 1:i + 1 + lookahead].max()
            if future_max > data["Close"].iloc[i]:
                success += 1

    return success / total if total > 0 else 0.0


# ===== SIGNAL DETECTION =====
def get_stock_signal(ticker: str) -> str:
    try:
        # Pull more data (1y) for better accuracy
        data = yf.download(ticker, period="1y", interval="1d", auto_adjust=True, progress=False)
        if data.empty or "Close" not in data.columns:
            return f"{ticker}: ⚪ No price data"

        data["MA_Short"] = data["Close"].rolling(SHORT_WINDOW).mean()
        data["MA_Long"] = data["Close"].rolling(LONG_WINDOW).mean()

        last_close = data["Close"].iloc[-1].item()
        accuracy = crossover_accuracy(data, SHORT_WINDOW, LONG_WINDOW, LOOKAHEAD_DAYS)
        cash_link = f"https://cash.app/search?q={ticker}"

        short_now, long_now = data["MA_Short"].iloc[-1], data["MA_Long"].iloc[-1]
        short_prev, long_prev = data["MA_Short"].iloc[-2], data["MA_Long"].iloc[-2]

        # BUY signal
        if short_now > long_now and short_prev <= long_prev and accuracy >= 0.85:
            shares = round(SUGGESTED_BUY_AMOUNT / last_close, 4)
            return (
                f"🟢 *BUY {ticker}* — ${last_close:.2f}\n"
                f"📈 Accuracy: {accuracy*100:.1f}%\n"
                f"💵 Suggestion: ${SUGGESTED_BUY_AMOUNT:.2f} → ~{shares} shares\n"
                f"[Buy on Cash App]({cash_link})"
            )

        # SELL signal
        elif short_now < long_now and short_prev >= long_prev:
            return f"🔴 *SELL {ticker}* — ${last_close:.2f}"

        # HOLD
        else:
            return f"⚪ HOLD {ticker} — ${last_close:.2f} (Acc {accuracy*100:.1f}%)"

    except Exception as e:
        return f"{ticker}: ⚠️ Error ({e})"


# ===== MAIN LOOP =====
while True:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"\n📊 Checking stocks at {now}...")

    messages = [f"📢 *Stock Signals — {now}*"]
    for ticker in TICKERS:
        result = get_stock_signal(ticker)
        print(result)
        messages.append(result)

    send_alert("\n\n".join(messages))

    print(f"😴 Sleeping for {CHECK_INTERVAL/60:.0f} minutes...")
    time.sleep(CHECK_INTERVAL)





