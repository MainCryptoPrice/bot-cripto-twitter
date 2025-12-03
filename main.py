import os
import requests
import tweepy
from datetime import datetime
import pytz
import time

def main():
    print("🤖 Iniciando bot (Versión Final con Cohete y Hashtags)...")

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

    def get_fear_and_greed():
        """Solo para el reporte diario"""
        try:
            r = requests.get("https://api.alternative.me/fng/?limit=1")
            data = r.json()['data'][0]
            value = int(data['value'])
            
            # Icono según sentimiento
            if value >= 75: icon = "🤑" 
            elif value >= 55: icon = "🐂" 
            elif value <= 25: icon = "😨" 
            elif value <= 45: icon = "🐻" 
            else: icon = "😐" 
            
            return f"🧠 Sentiment: {value}/100 {icon}\n"
        except:
            return "" 

    def format_price(n, symbol):
        if n > 100: return f"{symbol}{n:,.0f}"
        elif n >= 1: return f"{symbol}{n:,.2f}"
        else: return f"{symbol}{n:,.4f}"

    def get_emoji(change):
        if change is None: return "⚪"
        if change > 0: return "📈"
        if change < 0: return "📉"
        return "⚪"

    def generate_tweet_text(data, mode):
        now_utc = datetime.now(pytz.utc)
        time_str = now_utc.strftime('%H:%M UTC')
        
        # Configuración por modo
        extra_header = ""
        key = 'percent_change_1h' # Por defecto

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
            extra_header = get_fear_and_greed() # Solo en diario
        else: 
            title = "Update"
            icon = "🪙"
            tag = "(1h)"
            key = 'percent_change_1h'

        # Cabecera
        tweet = f"{icon} {title} | {time_str}\n{extra_header}\n"
        
        order = ['1', '1027', '5426', '1839', '52']
        
        # 1. Calcular cuál es el MVP (La mejor moneda)
        best_change = -9999999
        best_coin_id = None
        
        for coin_id in order:
            # Buscamos la que tenga el número más alto
            change = data[coin_id]['quote']['USD'][key]
            if change > best_change:
                best_change = change
                best_coin_id = coin_id

        # 2. Construir lista
        for coin_id in order:
            c = data[coin_id]
            symbol = c['symbol']
            usd = c['quote']['USD']
            eur = c['quote']['EUR']
            change = usd[key]
            
            # Lógica del Cohete: Si es la mejor moneda, añadimos 🚀
            rocket = " 🚀" if coin_id == best_coin_id else ""
            
            line = (
                f"{symbol}: {format_price(usd['price'], '$')} / {format_price(eur['price'], '€')} "
                f"{get_emoji(change)} {change:+.1f}% {tag}{rocket}"
            )
            tweet += line + "\n"
        
        # 3. Hashtags (Intentamos meter los 3)
        hashtags = "\n#Bitcoin #Ethereum #Crypto"
        tweet += hashtags
        
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
            
            # Recorte de seguridad inteligente
            # Si nos pasamos de 280, quitamos hashtags primero
            if len(text) > 280:
                print("⚠️ Tweet muy largo, quitando hashtags...")
                text = text.replace("#Bitcoin #Ethereum #Crypto", "#BTC #ETH #Crypto")
            
            if len(text) > 280:
                text = text[:280] # Corte final de emergencia
            
            client.create_tweet(text=text)
            print(f"✅ Tweet enviado ({mode})!")
            print(text)
            time.sleep(5)
            
    except Exception as e:
        print(f"❌ Error fatal: {e}")
        raise e

if __name__ == "__main__":
    main()
