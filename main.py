import os
import requests
import tweepy
from datetime import datetime
import pytz
import time

# --- CONFIGURACIÓN DE LLAVES ---
# (Ya comprobamos que funcionan, no toques nada en los Secrets)
CMC_API_KEY = os.environ.get("CMC_API_KEY")
TWITTER_API_KEY = os.environ.get("TWITTER_API_KEY")
TWITTER_API_SECRET = os.environ.get("TWITTER_API_SECRET")
TWITTER_ACCESS_TOKEN = os.environ.get("TWITTER_ACCESS_TOKEN")
TWITTER_ACCESS_SECRET = os.environ.get("TWITTER_ACCESS_SECRET")

# Hora fija UTC para el reporte especial (14:00 UTC)
# Esto equivale a las 15:00/16:00 en España y 09:00/10:00 en Nueva York
HORA_REPORTE_UTC = 14

def get_crypto_data():
    """
    Obtiene precios de CoinMarketCap.
    Hacemos 2 llamadas separadas (USD y EUR) para evitar el error del plan gratuito.
    """
    url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
    # IDs: BTC(1), ETH(1027), SOL(5426), BNB(1839), XRP(52)
    ids = '1,1027,5426,1839,52' 
    headers = {'Accepts': 'application/json', 'X-CMC_PRO_API_KEY': CMC_API_KEY}

    try:
        # 1. Llamada para precios en USD
        r_usd = requests.get(url, headers=headers, params={'id': ids, 'convert': 'USD'})
        r_usd.raise_for_status()
        data_usd = r_usd.json()['data']

        # 2. Llamada para precios en EUR
        r_eur = requests.get(url, headers=headers, params={'id': ids, 'convert': 'EUR'})
        r_eur.raise_for_status()
        data_eur = r_eur.json()['data']

        # 3. Fusionar datos (meter el precio EUR dentro del paquete USD)
        for coin_id in data_usd:
            data_usd[coin_id]['quote']['EUR'] = data_eur[coin_id]['quote']['EUR']
        
        return data_usd
        
    except Exception as e:
        print(f"❌ Error conectando con CoinMarketCap: {e}")
        raise e

def format_number(n, symbol):
    if n >= 1: return f"{symbol}{n:,.2f}"
    else: return f"{symbol}{n:,.4f}"

def get_emoji(change):
    if change is None: return "⚪"
    if change > 0: return "🟢"
    if change < 0: return "🔴"
    return "⚪"

def generate_tweet_text(data, mode):
    # Preparar horas para visualización (Madrid y NY)
    cet_tz = pytz.timezone('Europe/Madrid')
    et_tz = pytz.timezone('America/New_York')
    now_cet = datetime.now(cet_tz)
    now_et = datetime.now(et_tz)
    
    # Configurar títulos e iconos según el modo
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
    else: # Modo normal 1h
        header_title = "Crypto Update"
        header_icon = "🪙"
        time_label = "(1h)"
        change_key = 'percent_change_1h'

    # Construir encabezado
    tweet = f"{header_icon} {header_title} (CET: {now_cet.strftime('%H:%M')} | ET: {now_et.strftime('%H:%M')})\n"
    
    # Lista de monedas y orden
    order = ['1', '1027', '5426', '1839', '52']
    
    for coin_id in order:
        coin = data[coin_id]
        name = coin['symbol']
        quote_usd = coin['quote']['USD']
        quote_eur = coin['quote']['EUR']
        
        # Obtener variación según el modo (1h, 24h o 7d)
        change_val = quote_usd[change_key]
        emoji = get_emoji(change_val)
        
        # Formato de línea: Bitcoin (BTC): $X / €X 🟢 +X% (1h)
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
    print("🤖 Iniciando bot de precios (UTC)...")
    
    # Obtener hora actual UTC del servidor
    now_utc = datetime.now(pytz.utc)
    current_hour = now_utc.hour
    
    tweets_to_send = []

    # --- LÓGICA DE PROGRAMACIÓN ---
    # Si son las 14:00 UTC -> Toca reporte especial
    if current_hour == HORA_REPORTE_UTC:
        # Siempre enviamos el Diario (24h)
        tweets_to_send.append('24h')
        
        # Si es lunes (0), enviamos TAMBIÉN el Semanal (7d)
        if now_utc.weekday() == 0:
            tweets_to_send.append('7d')
            
    else:
        # Cualquier otra hora -> Update normal (1h)
        tweets_to_send.append('1h')

    # Conexión a Twitter
    client = tweepy.Client(
        consumer_key=TWITTER_API_KEY,
        consumer_secret=TWITTER_API_SECRET,
        access_token=TWITTER_ACCESS_TOKEN,
        access_token_secret=TWITTER_ACCESS_SECRET
    )
    
    try:
        # Pedimos los datos una sola vez
        data = get_crypto_data()
        
        # Publicamos los tweets que toquen (1 o 2)
        for mode in tweets_to_send:
            text = generate_tweet_text(data, mode)
            client.create_tweet(text=text)
            print(f"✅ Tweet enviado ({mode})!")
            print(text)
            print("-" * 20)
            time.sleep(5) # Esperar 5 segs entre tweets si hay varios
            
    except Exception as e:
        print(f"❌ Error fatal: {e}")
        raise e

if __name__ == "__main__":
    main()
