import os
import requests
import tweepy
from datetime import datetime
import pytz
import time

# --- CONFIGURACIÓN ---
MODO_PRUEBA = False 

def main():
    print(f"🤖 Iniciando bot (Modo Prueba: {MODO_PRUEBA})...")

    # CARGAR LLAVES
    CMC_API_KEY = os.environ.get("CMC_API_KEY")
    TWITTER_API_KEY = os.environ.get("TWITTER_API_KEY")
    TWITTER_API_SECRET = os.environ.get("TWITTER_API_SECRET")
    TWITTER_ACCESS_TOKEN = os.environ.get("TWITTER_ACCESS_TOKEN")
    TWITTER_ACCESS_SECRET = os.environ.get("TWITTER_ACCESS_SECRET")
    
    HORA_REPORTE_UTC = 14

    ATH_VALUES = {
        '1': 108000,    '1027': 4891,   '5426': 260,
        '1839': 720,    '52': 3.84
    }

    # --- FUNCIONES ROBUSTAS ---
    def get_crypto_data_con_reintentos():
        """Intenta obtener datos hasta 3 veces si falla"""
        max_retries = 3
        url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
        ids = '1,1027,5426,1839,52' 
        headers = {'Accepts': 'application/json', 'X-CMC_PRO_API_KEY': CMC_API_KEY}
        
        for i in range(max_retries):
            try:
                print(f"📡 Conectando con CMC (Intento {i+1}/{max_retries})...")
                # 1. USD
                r_usd = requests.get(url, headers=headers, params={'id': ids, 'convert': 'USD'}, timeout=10)
                r_usd.raise_for_status()
                data_usd = r_usd.json()['data']
                
                # 2. EUR
                r_eur = requests.get(url, headers=headers, params={'id': ids, 'convert': 'EUR'}, timeout=10)
                r_eur.raise_for_status()
                data_eur = r_eur.json()['data']

                for coin_id in data_usd:
                    data_usd[coin_id]['quote']['EUR'] = data_eur[coin_id]['quote']['EUR']
                
                return data_usd # ¡Éxito!
            
            except Exception as e:
                print(f"⚠️ Fallo en intento {i+1}: {e}")
                if i < max_retries - 1:
                    print("⏳ Esperando 60 segundos antes de reintentar...")
                    time.sleep(60) # Espera 1 minuto
                else:
                    print("❌ Se acabaron los intentos. Rendirse.")
                    raise e

    def get_fear_and_greed():
        try:
            r = requests.get("https://api.alternative.me/fng/?limit=1", timeout=5)
            data = r.json()['data'][0]
            val = int(data['value'])
            if val >= 75: i = "🤑" 
            elif val >= 55: i = "🐂" 
            elif val <= 25: i = "😨" 
            elif val <= 45: i = "🐻" 
            else: i = "😐" 
            return f"🧠 Sentiment: {val}/100 {i}\n"
        except: return "" 

    def format_price(n, s):
        if n > 100: return f"{s}{n:,.0f}"
        elif n >= 1: return f"{s}{n:,.2f}"
        else: return f"{s}{n:,.4f}"

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
            icon = "💰"
            tag = "(1h)"
            key = 'percent_change_1h'

        tweet = f"{icon} {title} | {time_str}\n{extra_header}\n"
        order = ['1', '1027', '5426', '1839', '52']
        
        best_change = -9999999
        best_coin_id = None
        for cid in order:
            ch = data[cid]['quote']['USD'][key]
            if ch > best_change: best_change = ch; best_coin_id = cid

        for cid in order:
            c = data[cid]
            sym = c['symbol']
            usd = c['quote']['USD']
            eur = c['quote']['EUR']
            ch = usd[key]
            pusd = usd['price']
            
            rocket = " 🚀" if cid == best_coin_id else ""
            
            if mode == '7d':
                ath = ATH_VALUES.get(cid, 0)
                if ath > 0:
                    dpct = ((pusd - ath) / ath) * 100
                    ath_str = "🏆 ATH!" if dpct >= 0 else f"🏔️ {dpct:.0f}% ATH"
                else: ath_str = ""
                line = f"${sym}: {format_price(pusd, '$')} {get_emoji(ch)} {ch:+.1f}% | {ath_str}"
            else:
                line = f"${sym}: {format_price(pusd, '$')} / {format_price(eur['price'], '€')} {get_emoji(ch)} {ch:+.1f}% {tag}{rocket}"
            tweet += line + "\n"
        
        tweet += "\n$BTC $ETH $SOL #Crypto"
        return tweet

    # --- EJECUCIÓN PRINCIPAL ---
    now_utc = datetime.now(pytz.utc)
    curr_h = now_utc.hour
    to_send = []
    
    # Lógica de horario
    if curr_h == HORA_REPORTE_UTC:
        to_send.append('24h')
        if now_utc.weekday() == 0: to_send.append('7d')
    else:
        to_send.append('1h')

    client = tweepy.Client(
        consumer_key=TWITTER_API_KEY, consumer_secret=TWITTER_API_SECRET,
        access_token=TWITTER_ACCESS_TOKEN, access_token_secret=TWITTER_ACCESS_SECRET
    )
    
    try:
        # Usamos la función nueva con reintentos
        data = get_crypto_data_con_reintentos()
        
        for mode in to_send:
            text = generate_tweet_text(data, mode)
            if len(text) > 280: text = text.replace("$BTC $ETH $SOL #Crypto", "#Crypto")
            if len(text) > 280: text = text[:280]
            
            if MODO_PRUEBA:
                print(f"🧪 [TEST] {mode}:\n{text}")
            else:
                client.create_tweet(text=text)
                print(f"✅ Enviado {mode}")
            time.sleep(5)
            
    except Exception as e:
        print(f"❌ Error fatal tras reintentos: {e}")
        raise e

if __name__ == "__main__":
    main()
