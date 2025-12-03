import os
import tweepy
import datetime

# 1. CARGAR LLAVES
api_key = os.environ.get("TWITTER_API_KEY")
api_secret = os.environ.get("TWITTER_API_SECRET")
access_token = os.environ.get("TWITTER_ACCESS_TOKEN")
access_secret = os.environ.get("TWITTER_ACCESS_SECRET")

def main():
    print("🤖 Intentando enviar un tweet de prueba...")

    # 2. CONEXIÓN (Cliente v2)
    client = tweepy.Client(
        consumer_key=api_key,
        consumer_secret=api_secret,
        access_token=access_token,
        access_token_secret=access_secret
    )

    # 3. TEXTO ÚNICO (Para evitar error de "tweet duplicado")
    hora_actual = datetime.datetime.now().strftime("%H:%M:%S")
    texto = f"Hola Twitter! Prueba de conexión {hora_actual}"

    try:
        # 4. ENVIAR
        response = client.create_tweet(text=texto)
        print(f"✅ ¡ÉXITO! Tweet enviado con ID: {response.data['id']}")
        print(f"Texto enviado: {texto}")
    except tweepy.errors.Forbidden as e:
        print("❌ ERROR 403 (PROHIBIDO):")
        print("Twitter dice que tus llaves NO tienen permiso de escritura.")
        print("Detalle técnico:", e)
    except Exception as e:
        print(f"❌ OTRO ERROR: {e}")

if __name__ == "__main__":
    main()
