import os
import requests
import tweepy
from datetime import datetime
import pytz

# --- 1. CONFIGURACIÓN ---
CMC_API_KEY = os.environ.get("CMC_API_KEY")
TWITTER_API_KEY = os.environ.get("TWITTER_API_KEY")
TWITTER_API_SECRET = os.environ.get("TWITTER_API_SECRET")
TWITTER_ACCESS_TOKEN = os.environ.get("TWITTER_ACCESS_TOKEN")
TWITTER_ACCESS_SECRET = os.environ.get("TWITTER_ACCESS_SECRET")

HORA_REPORTE_CET = 15

def get_crypto_data():
    url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
    parameters = {'id': '1,1027,5426,1839,52', 'convert': 'USD,EUR'}
    headers = {'Accepts': 'application/json', 'X-CMC_PRO_API_KEY': CMC_API_KEY}
    response = requests.get(url, headers=headers, params=parameters)
    response.raise_for_status()
    return response.json()['data']

def format_number(n, symbol):
    if n >= 1: return f"{symbol}{n:,.2f}"
    else: return f"{symbol}{n:,.4f}"

def get_emoji(change):
    if change is None: return "⚪"
    if change > 0: return "🟢"
    if change < 0: return "🔴"
    return "⚪"

def build_tweet_content(data):
    cet_tz = pytz.timezone('Europe/Madrid')
    et_tz = pytz.timezone('America/New_York')
    now_cet = datetime.now(cet_tz)
    now_et = datetime.now(et_tz)
    
    is_special_time = (now_cet.hour == HORA_REPORTE_CET)
    is_monday = (now_cet.weekday() == 0)
    
    time_label = "(1h)"
    header_icon = "🪙"
    header_title = "Crypto Update"
    change_key = 'percent_change_1h'
    
    if is_special_time:
        if is_monday:
            header_title = "Weekly Market Wrap-up"
            header_icon = "📅"
            time_label = "(7d)"
            change_key = 'percent_change_7d'
        else:
            header_title = "Daily Crypto Report"
            header_icon = "📊"
            time_label = "(24h)"
            change_key = 'percent_change_24h'

    tweet = f"{header_icon} {header_title} (CET: {now_cet.strftime('%H:%M')} | ET: {now_et.strftime('%H:%M')})\n"
    
    order = ['1', '1027', '5426', '1839', '52']
    
    for coin_id in order:
        coin = data[coin_id]
        name = coin['symbol']
        quote_usd = coin['quote']['USD']
        quote_eur = coin['quote']['EUR']
        change_val = quote_usd[change_key]
        emoji = get_emoji(change_val)
        
        line = (
            f"{coin['name']} ({name}): "
            f"{format_number(quote_usd['price'], '$')} / "
            f"{format_number(quote_eur['price'], '€')} "
            f"{emoji} {change_val:+.2f}% {time_label}"
        )
        tweet += line + "\n"
    
    tweet += "🔁 Updates every 2h"
    return tweet

def main():
    print("🤖 Iniciando bot...")
    client = tweepy.Client(
        consumer_key=TWITTER_API_KEY,
        consumer_secret=TWITTER_API_SECRET,
        access_token=TWITTER_ACCESS_TOKEN,
        access_token_secret=TWITTER_ACCESS_SECRET
    )
    try:
        data = get_crypto_data()
        tweet_text = build_tweet_content(data)
        client.create_tweet(text=tweet_text)
        print(f"✅ Tweet enviado!\n{tweet_text}")
    except Exception as e:
        print(f"❌ Error: {e}")
        raise e

if __name__ == "__main__":
    main()
