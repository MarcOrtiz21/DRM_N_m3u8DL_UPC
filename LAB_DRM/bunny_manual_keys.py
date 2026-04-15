import os
import re
import subprocess
import requests
from hashlib import md5
from urllib.parse import urlparse

# --- CONFIGURACIÓN ---
BASE_SAVE_PATH = r"C:\Users\marco\OneDrive - MSFT\UPC\VIDEOS_ASES\LAB_DOWNLOADS"

def enviar_pings_bunny(embed_url, referer):
    """Simula que el vídeo se está viendo para evitar bloqueos"""
    print("-> Configurando pings de Bunny CDN...")
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"})
    
    try:
        resp = session.get(embed_url, headers={"Referer": referer})
        page = resp.text
        server_id = re.search(r"https://video-(.*?)\.mediadelivery\.net", page).group(1)
        search = re.search(r'contextId=(.*?)&secret=(.*?)"', page)
        context_id, secret = search.group(1), search.group(2)
        
        ping_headers = {"Origin": "https://iframe.mediadelivery.net", "Referer": "https://iframe.mediadelivery.net/"}
        session.get(f"https://video-{server_id}.mediadelivery.net/.drm/{context_id}/activate", headers=ping_headers)
        
        h = md5(f"{secret}_{context_id}_0_false_0".encode("utf8")).hexdigest()
        session.get(f"https://video-{server_id}.mediadelivery.net/.drm/{context_id}/ping", 
                    params={"hash": h, "time": 0, "paused": "false", "chosen_res": "0"}, 
                    headers=ping_headers)
        print("[OK] Bunny CDN activado (pings enviados).")
        return True
    except:
        print("[!] No se pudieron enviar los pings. La descarga podría fallar o cortarse.")
        return False

def main():
    print("="*60)
    print("      LABORATORIO DRM - DESCARGA MANUAL DE EMERGENCIA")
    print("="*60)
    
    m3u8 = input("1. URL del m3u8:\n> ").strip()
    embed = input("2. URL del Embed (iframe.mediadelivery.net...):\n> ").strip()
    referer = input("3. URL de la Academia (Referer):\n> ").strip()
    
    print("\n4. Pega las KEYS (ID:KEY) que hayas obtenido en cualquier web:")
    keys_text = ""
    while True:
        line = input()
        if not line: break
        keys_text += line + " "
    keys = re.findall(r'([a-fA-F0-9]{32}:[a-fA-F0-9]{32})', keys_text)
    
    if not keys:
        print("[!] No hay keys, no puedo descifrar el vídeo.")
        return

    nombre = input("\n5. Nombre del archivo:\n> ").strip()
    if not nombre: nombre = "video_final"

    if not os.path.exists(BASE_SAVE_PATH): os.makedirs(BASE_SAVE_PATH)

    # Activar Bunny
    enviar_pings_bunny(embed, referer)

    # Lanzar N_m3u8DL-RE
    comando = [
        "N_m3u8DL-RE", m3u8,
        "--save-dir", BASE_SAVE_PATH,
        "--save-name", nombre,
        "-H", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
        "-H", "Origin: https://iframe.mediadelivery.net",
        "-H", f"Referer: {referer}",
        "--auto-select",
        "-M", "format=mkv"
    ]
    for k in keys: comando.extend(["--key", k])
    
    print(f"\n[DESCARGANDO] -> {nombre}.mkv")
    subprocess.run(comando)

if __name__ == "__main__":
    main()
