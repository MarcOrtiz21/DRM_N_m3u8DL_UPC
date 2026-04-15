import os
import re
import subprocess
import time
import sys
import requests
import random
from hashlib import md5
from urllib.parse import urlparse

# --- CONFIGURACIÓN (Heredada de tu proyecto) ---
BASE_SAVE_PATH = r"C:\Users\marco\OneDrive - MSFT\UPC\VIDEOS_ASES"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

class BunnyLabDownloader:
    def __init__(self, m3u8_url, embed_url, referer, save_path, file_name):
        self.m3u8_url = m3u8_url
        self.embed_url = embed_url
        self.referer = referer
        self.save_path = save_path
        self.file_name = file_name
        self.guid = urlparse(embed_url).path.split("/")[-1]
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})
        
    def _get_bunny_context(self):
        """Extrae el server_id, contextId y secret para los pings de Bunny"""
        try:
            headers = {"Referer": self.referer}
            resp = self.session.get(self.embed_url, headers=headers)
            page = resp.text
            
            server_id = re.search(r"https://video-(.*?)\.mediadelivery\.net", page).group(1)
            search = re.search(r'contextId=(.*?)&secret=(.*?)"', page)
            context_id, secret = search.group(1), search.group(2)
            
            return server_id, context_id, secret
        except Exception as e:
            print(f"[!] Error extrayendo contexto de Bunny: {e}")
            return None, None, None

    def simulate_viewing(self, server_id, context_id, secret):
        """Simula los pings de reproducción para que Bunny no bloquee la descarga"""
        print("-> Enviando pings de 'activación' a Bunny CDN...")
        ping_headers = {
            "Origin": "https://iframe.mediadelivery.net",
            "Referer": "https://iframe.mediadelivery.net/",
            "authority": f"video-{server_id}.mediadelivery.net"
        }
        
        # 1. Activate
        self.session.get(
            f"https://video-{server_id}.mediadelivery.net/.drm/{context_id}/activate",
            headers=ping_headers
        )
        
        # 2. Ping inicial
        def send_ping(t):
            h = md5(f"{secret}_{context_id}_{t}_false_0".encode("utf8")).hexdigest()
            self.session.get(
                f"https://video-{server_id}.mediadelivery.net/.drm/{context_id}/ping",
                params={"hash": h, "time": t, "paused": "false", "chosen_res": "0"},
                headers=ping_headers
            )
        
        send_ping(0)
        print("-> Vídeo 'activado' en el servidor.")

    def download(self, keys):
        comando = [
            "N_m3u8DL-RE", self.m3u8_url,
            "--save-dir", self.save_path,
            "--save-name", self.file_name,
            "-H", f"User-Agent: {USER_AGENT}",
            "-H", "Origin: https://iframe.mediadelivery.net",
            "-H", f"Referer: {self.referer}",
            "--auto-select",
            "-M", "format=mkv"
        ]
        
        for k in keys:
            comando.extend(["--key", k])
            
        print(f"\n[LAB] Iniciando descarga en: {self.save_path}")
        subprocess.run(comando)

def get_input(prompt):
    return input(f"{prompt}\n> ").strip()

def main():
    print("="*60)
    print("      LABORATORIO DRM - OPTIMIZADOR BUNNY CDN")
    print("="*60)
    
    # 1. Datos básicos
    m3u8 = get_input("1. URL del m3u8 (o deja vacío para salir):")
    if not m3u8: return
    
    embed_url = get_input("2. URL del Embed (iframe.mediadelivery.net...):")
    referer = get_input("3. URL de la Academia (Referer):")
    nombre = get_input("4. Nombre del archivo (sin extensión):")
    
    # 2. Keys (Copiadas de CDRM-Project o Guesser)
    print("\n5. Pega las KEYS (puedes pegar todo el bloque de texto de CDRM):")
    keys_text = ""
    while True:
        line = input()
        if not line: break
        keys_text += line + " "
    
    keys = re.findall(r'([a-fA-F0-9]{32}:[a-fA-F0-9]{32})', keys_text)
    if not keys:
        print("[!] No se encontraron keys válidas. Abortando.")
        return

    # 3. Ruta de guardado (Simplificada para el Lab)
    save_path = os.path.join(BASE_SAVE_PATH, "LAB_DOWNLOADS")
    if not os.path.exists(save_path): os.makedirs(save_path)

    # 4. Proceso
    lab = BunnyLabDownloader(m3u8, embed_url, referer, save_path, nombre)
    
    s_id, c_id, sec = lab._get_bunny_context()
    if s_id and c_id:
        lab.simulate_viewing(s_id, c_id, sec)
    
    lab.download(keys)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nDetenido.")
