import os
import requests
import tweepy
from datetime import datetime
import pytz
import time

def main():
    print("🤖 Iniciando bot de precios (Diseño Gráficas)...")

    # 1. CARGAR LLAVES
    CMC_API_KEY = os.environ.get("CMC_API_KEY")
    TWITTER_API_KEY = os.environ.get("TWITTER_API_KEY")
    TWITTER_API_SECRET = os.environ.get("TWITTER_API_SECRET")
    TWITTER_ACCESS_TOKEN = os.environ.get("TWITTER_ACCESS_TOKEN")
    TWITTER_ACCESS_SECRET = os.environ.get("TWITTER_ACCESS_SECRET")
    
    HORA_REPORTE_UTC = 14

    # --- FUNCIONES INTERNAS ---
    def get_crypto_data():
        url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
        ids = '1,1027,5426,1839,52' 
        headers = {'Accepts': 'application/json', 'X-CMC_PRO_API_KEY': CMC_API_KEY}
        
        try:
            r_usd = requests.get(url, headers=headers, params={'id': ids, 'convert': 'USD'})
            r_usd.raise_for_status()
            data_usd = r_usd.json()['data']

            r_eur = requests.get(url, headers=headers, params={'id': ids, 'convert': 'EUR'})
            r_eur.raise_for_status()
            data_eur = r_eur.json()['data']

            for coin_id in data_usd:
                data_usd[coin_id]['quote']['EUR'] = data_eur[coin_id]['quote']['EUR']
            return data_usd
        except Exception as e:
            print(f"❌ Error API CMC: {e}")
            raise e

    def format_price(n, symbol):
        if n > 100:
            return f"{symbol}{n:,.0f}"
        elif n >= 1:
            return f"{symbol}{n:,.2f}"
        else:
            return f"{symbol}{n:,.4f}"

    def get_emoji(change):
        if change is None: return "⚪"
        # CAMBIO AQUÍ: Usamos gráficas en vez de bolas
        if change > 0: return "📈"
        if change < 0: return "📉"
        return "⚪"

    def generate_tweet_text(data, mode):
        now_utc = datetime.now(pytz.utc)
        time_str = now_utc.strftime('%H:%M UTC')
        
        if mode == '7d':
            title = "Weekly Wrap"
            icon = "📅"
            tag = "(7d)"
            key = 'percent_change_7d'
        elif mode == '24h':
            title = "Daily Report"
            icon = "📊"
            tag = "(24h)"
            key = 'percent_change_24h'
        else: 
            title = "Update"
            icon = "🪙"
            tag = "(1h)"
            key = 'percent_change_1h'

        tweet = f"{icon} {title} | {time_str}\n\n"
        
        order = ['1', '1027', '5426', '1839', '52']
        for coin_id in order:
            c = data[coin_id]
            symbol = c['symbol']
            usd = c['quote']['USD']
            eur = c['quote']['EUR']
            change = usd[key]
            
            line = (
                f"{symbol}: {format_price(usd['price'], '$')} / {format_price(eur['price'], '€')} "
                f"{get_emoji(change)} {change:+.1f}% {tag}"
            )
            tweet += line + "\n"
        
        return tweet

    # --- LÓGICA PRINCIPAL ---
    now_utc = datetime.now(pytz.utc)
    current_hour = now_utc.hour
    
    tweets_to_send = []
    if current_hour == HORA_REPORTE_UTC:
        tweets_to_send.append('24h')
        if now_utc.weekday() == 0:
            tweets_to_send.append('7d')
    else:
        tweets_to_send.append('1h')

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
            
            if len(text) > 280:
                print(f"⚠️ Recortando tweet ({len(text)} chars)...")
                text = text[:280]
            
            client.create_tweet(text=text)
            print(f"✅ Tweet enviado ({mode})!")
            print(text)
            time.sleep(5)
            
    except Exception as e:
        print(f"❌ Error fatal: {e}")
        raise e

if __name__ == "__main__":
    main()
