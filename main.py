import os
import requests
import tweepy
from datetime import datetime
import pytz
import time

# --- CONFIGURACIÓN DE SEGURIDAD ---
# Pon True si quieres probar cambios sin publicar en Twitter.
# Pon False para que el bot funcione normalmente.
MODO_PRUEBA = False 

def main():
    print(f"🤖 Iniciando bot (Modo Prueba: {MODO_PRUEBA})...")

    # 1. CARGAR LLAVES
    CMC_API_KEY = os.environ.get("CMC_API_KEY")
    TWITTER_API_KEY = os.environ.get("TWITTER_API_KEY")
    TWITTER_API_SECRET = os.environ.get("TWITTER_API_SECRET")
    TWITTER_ACCESS_TOKEN = os.environ.get("TWITTER_ACCESS_TOKEN")
    TWITTER_ACCESS_SECRET = os.environ.get("TWITTER_ACCESS_SECRET")
    
    HORA_REPORTE_UTC = 14

    # --- CONSTANTES ATH (Máximos Históricos Aprox) ---
    ATH_VALUES = {
        '1': 108000,    # Bitcoin
        '1027': 4891,   # Ethereum
        '5426': 260,    # Solana
        '1839': 720,    # BNB
        '52': 3.84      # XRP
    }

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
        
        extra_header = ""
        key = 'percent_change_1h'

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
            extra_header = get_fear_and_greed()
        else: 
            title = "Update"
            icon = "🪙"
            tag = "(1h)"
            key = 'percent_change_1h'

        tweet = f"{icon} {title} | {time_str}\n{extra_header}\n"
        
        order = ['1', '1027', '5426', '1839', '52']
        
        # Calcular MVP
        best_change = -9999999
        best_coin_id = None
        for coin_id in order:
            change = data[coin_id]['quote']['USD'][key]
            if change > best_change:
                best_change = change
                best_coin_id = coin_id

        for coin_id in order:
            c = data[coin_id]
            symbol = c['symbol']
            usd = c['quote']['USD']
            eur = c['quote']['EUR']
            change = usd[key]
            price_usd = usd['price']
            
            rocket = " 🚀" if coin_id == best_coin_id else ""
            
            # --- LÓGICA SEMANAL (ATH) ---
            if mode == '7d':
                ath = ATH_VALUES.get(coin_id, 0)
                if ath > 0:
                    distance_pct = ((price_usd - ath) / ath) * 100
                    if distance_pct >= 0:
                        ath_str = "🏆 ATH!"
                    else:
                        ath_str = f"🏔️ {distance_pct:.0f}% ATH"
                else:
                    ath_str = ""
                
                # Semanal: Sin Euros, con ATH
                line = (
                    f"${symbol}: {format_price(price_usd, '$')} "
                    f"{get_emoji(change)} {change:+.1f}% | {ath_str}"
                )
            else:
                # Diario/Normal: Con Euros, sin ATH
                line = (
                    f"${symbol}: {format_price(price_usd, '$')} / {format_price(eur['price'], '€')} "
                    f"{get_emoji(change)} {change:+.1f}% {tag}{rocket}"
                )
            
            tweet += line + "\n"
        
        hashtags = "\n$BTC $ETH $SOL #Crypto"
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
            
            # Recorte de seguridad
            if len(text) > 280:
                text = text.replace("$BTC $ETH $SOL #Crypto", "#Crypto")
            if len(text) > 280:
                text = text[:280]
            
            # --- EL GRAN CAMBIO: MODO PRUEBA ---
            if MODO_PRUEBA:
                print(f"🧪 [SIMULACRO] Tweet que se enviaría ({mode}):")
                print(text)
                print("-" * 20)
            else:
                client.create_tweet(text=text)
                print(f"✅ Tweet enviado ({mode})!")
                print(text)
            
            time.sleep(5)
            
    except Exception as e:
        print(f"❌ Error fatal: {e}")
        raise e

if __name__ == "__main__":
    main()
