import os
import requests
import tweepy
from datetime import datetime
import pytz
import time

# --- CONFIGURACIÓN ---
CMC_API_KEY = os.environ.get("CMC_API_KEY")
TWITTER_API_KEY = os.environ.get("TWITTER_API_KEY")
TWITTER_API_SECRET = os.environ.get("TWITTER_API_SECRET")
TWITTER_ACCESS_TOKEN = os.environ.get("TWITTER_ACCESS_TOKEN")
TWITTER_ACCESS_SECRET = os.environ.get("TWITTER_ACCESS_SECRET")

# Hora fija UTC para el reporte (14:00 UTC funciona bien para EEUU y EU todo el año)
HORA_REPORTE_UTC = 14

def get_crypto_data():
    """Obtiene datos con truco de doble llamada (USD+EUR) para plan gratis"""
    url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
    ids = '1,1027,5426,1839,52' 
    headers = {'Accepts': 'application/json', 'X-CMC_PRO_API_KEY': CMC_API_KEY}

    # 1. USD
    r_usd = requests.get(url, headers=headers, params={'id': ids, 'convert': 'USD'})
    r_usd.raise_for_status()
    data_usd = r_usd.json()['data']

    # 2. EUR
    r_eur = requests.get(url, headers=headers, params={'id': ids, 'convert': 'EUR'})
    r_eur.raise_for_status()
    data_eur = r_eur.json()['data']

    # Fusionar
    for coin_id in data_usd:
        data_usd[coin_id]['quote']['EUR'] = data_eur[coin_id]['quote']['EUR']
    
    return data_usd

def format_number(n, symbol):
    if n >= 1: return f"{symbol}{n:,.2f}"
    else: return f"{symbol}{n:,.4f}"

def get_emoji(change):
    if change is None: return "⚪"
    if change > 0: return "🟢"
    if change < 0: return "🔴"
    return "⚪"

def generate_tweet_text(data, mode):
    # Fechas para el texto (Visualización)
    cet_tz = pytz.timezone('Europe/Madrid')
    et_tz = pytz.timezone('America/New_York')
    now_cet = datetime.now(cet_tz)
    now_et = datetime.now(et_tz)
    
    if mode == '7d':
        header_title = "Weekly Market Wrap-up"
        header_icon = "📅"
        time_label = "(7d)"
        change_key = 'percent_change_7d'
    elif mode == '24h':
        header_title = "Daily Crypto Report"
        header_icon = "📊"
        time_label = "(24h)"
        change_key = 'percent_change_24h'
    else: # 1h
        header_title = "Crypto Update"
        header_icon = "🪙"
        time_label = "(1h)"
        change_key = 'percent_change_1h'

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
    print("🤖 Iniciando bot (UTC)...")
    
    # Obtenemos la hora UTC actual del servidor
    now_utc = datetime.now(pytz.utc)
    current_hour = now_utc.hour
    
    # Lista de tweets a enviar en esta ejecución
    tweets_to_send = []

    # LOGICA UTC:
    if current_hour == HORA_REPORTE_UTC:
        # Son las 14:00 UTC -> Toca Reporte Diario
        tweets_to_send.append('24h')
        
        # Si además es Lunes (Monday = 0), añadimos el Semanal
        if now_utc.weekday() == 0:
            tweets_to_send.append('7d')
    else:
        # Cualquier otra hora par -> Reporte normal
        tweets_to_send.append('1h')

    # Ejecución
    client = tweepy.Client(
        consumer_key=TWITTER_API_KEY,
        consumer_secret=TWITTER_API_SECRET,
        access_token=TWITTER_ACCESS_TOKEN,
        access_token_secret=TWITTER_ACCESS_SECRET
    )
    
    try:
        data = get_crypto_data()
        
        for mode in tweets_to_send:
            text = generate_tweet_text(data, mode)
            client.create_tweet(text=text)
            print(f"✅ Tweet enviado ({mode})!")
            time.sleep(5) # Pequeña pausa de seguridad entre tweets
            
    except Exception as e:
        print(f"❌ Error: {e}")
        raise e

if __name__ == "__main__":
    main()
