import os
import tweepy

# Cargar llaves
api_key = os.environ.get("TWITTER_API_KEY", "")
api_secret = os.environ.get("TWITTER_API_SECRET", "")
access_token = os.environ.get("TWITTER_ACCESS_TOKEN", "")
access_secret = os.environ.get("TWITTER_ACCESS_SECRET", "")

def censurar(texto):
    if not texto or len(texto) < 5:
        return "❌ VACÍO O MUY CORTO"
    # Muestra solo los 2 primeros y 2 últimos caracteres
    return f"{texto[:2]}...{texto[-2:]} (Longitud: {len(texto)})"

def check_keys():
    print("--- 🕵️‍♂️ INFORME DE DIAGNÓSTICO ---")
    
    print(f"1. API Key:        {censurar(api_key)}")
    print(f"2. API Secret:     {censurar(api_secret)}")
    print(f"3. Access Token:   {censurar(access_token)}")
    print(f"4. Access Secret:  {censurar(access_secret)}")
    
    print("-" * 30)
    
    # Comprobaciones automáticas
    errores = []
    
    # Chequeo del Access Token (El fallo más común)
    if not access_token.replace("-", "").isalnum():
         # A veces se cuelan comillas o espacios
         pass 
         
    if "-" not in access_token:
        errores.append("⚠️ ALERTA ROJA: El Access Token NO tiene un guion (-). \n   -> Posiblemente has copiado otra cosa (¿Client ID?).\n   -> Debe ser algo como: 12345678-AbCdEfGh...")
    elif not access_token[0].isdigit():
        errores.append("⚠️ ALERTA: El Access Token suele empezar por NÚMEROS. El tuyo no.")

    # Chequeo de longitudes sospechosas
    if len(api_key) > 50:
        errores.append("⚠️ ALERTA: La API Key es larguísima (>50). \n   -> ¿Seguro que no has pegado el 'Bearer Token' o el 'Client ID'?")
        
    if len(errores) > 0:
        print("\n❌ SE HAN ENCONTRADO ERRORES GRAVES:")
        for e in errores:
            print(e)
    else:
        print("\n✅ Las llaves parecen tener el formato correcto (a simple vista).")
        print("Intentando autenticación de prueba (Read Only)...")
        
        try:
            client = tweepy.Client(
                consumer_key=api_key,
                consumer_secret=api_secret,
                access_token=access_token,
                access_token_secret=access_secret
            )
            me = client.get_me()
            print(f"🎉 ¡ÉXITO! Conectado como: {me.data.username}")
            print("Si ves esto, el problema era solo de permisos de escritura, no de conexión.")
        except Exception as e:
            print(f"💥 Error al conectar: {e}")

if __name__ == "__main__":
    check_keys()
