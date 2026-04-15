import os
import re
import json
import subprocess
import time
import sys
from urllib.parse import urlparse

# Intentamos importar DrissionPage para la automatización de la web
try:
    from DrissionPage import ChromiumPage
except ImportError:
    print("Instalando DrissionPage...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "DrissionPage"])
    from DrissionPage import ChromiumPage

# --- CONFIGURACIÓN ---
BASE_SAVE_PATH = r"C:\Users\marco\OneDrive - MSFT\UPC\VIDEOS_ASES"

def parse_fetch_v21(fetch_text):
    """Extrae URL y Headers de un comando fetch de JS (v2.1 Robusta)"""
    try:
        # Extraer URL (busca entre comillas dobles o simples dentro de fetch)
        url_match = re.search(r'fetch\((?:\'|")([^\'"]+)(?:\'|")', fetch_text)
        url = url_match.group(1) if url_match else None
        
        # Extraer Headers (buscamos el bloque de objeto JSON)
        # Usamos una búsqueda más elástica para no fallar con los binarios
        headers_match = re.search(r'["\']headers["\']\s*:\s*(\{.*?\})', fetch_text, re.DOTALL)
        if headers_match:
            headers_str = headers_match.group(1)
            # Extraemos clave-valor ignorando el resto
            # Buscamos patrones "clave": "valor"
            pares = re.findall(r'["\']([^"\']+)["\']\s*:\s*["\']([^"\']+)["\']', headers_str)
            headers_dict = {k: v for k, v in pares}
            
            # Aplicar el FIX de Bunny que tenías en tu script original
            headers_dict["Origin"] = "https://iframe.mediadelivery.net"
            headers_dict["Referer"] = "https://iframe.mediadelivery.net/"
            
            return url, headers_dict
    except Exception as e:
        print(f"[!] Error al parsear el fetch v2.1: {e}")
    return None, None

def automatizar_cdrm_lab(headers_dict):
    """Navega a CDRM-Project y mete los headers automáticamente"""
    print("\n-> Abriendo CDRM-Project para obtener las llaves...")
    page = ChromiumPage()
    try:
        page.get('https://cdrm-project.com/')
        time.sleep(3)
        
        # Convertimos headers a JSON string para la caja de texto
        headers_json_str = json.dumps(headers_dict, separators=(',', ':'))
        
        # Inyectar el botón de "Pagar PSSH" si podemos para ayudarte
        # Buscamos la caja de Headers específicamente
        textareas = page.eles('tag:textarea')
        headers_injected = False
        
        for ta in textareas:
            if "accept" in ta.value or not ta.value:
                ta.clear()
                ta.input(headers_json_str)
                print("[OK] Headers inyectados con éxito.")
                headers_injected = True
                break
        
        if not headers_injected:
            print("[!] Advertencia: No se encontró la caja de headers automáticamente. Pégalos a mano si es necesario.")
            print(f"[DATA]: {headers_json_str}")

        print("\n" + "="*50)
        print(" [ACCION REQUERIDA] ")
        print(" 1. Introduce el PSSH en la web (obtenlo de la extension o consola).")
        print(" 2. Haz clic en SUBMIT.")
        print("="*50)
        
        # Esperar a que aparezcan las llaves (patrón 32:32)
        print("-> Monitorizando pantalla para capturar las llaves...")
        while True:
            html = page.html
            keys = re.findall(r'([a-fA-F0-9]{32}:[a-fA-F0-9]{32})', html)
            if keys:
                print(f"\n[EXITO] Se han encontrado {len(keys)} llaves:")
                for k in set(keys): print(f"  > {k}")
                return list(set(keys))
            time.sleep(2)
    except Exception as e:
        print(f"[!] Error en la automatización: {e}")
    finally:
        page.quit()
    return []

def main():
    print("="*60)
    print("      LABORATORIO DRM v2.1 - BUNNY OPTIMIZER")
    print("="*60)
    
    m3u8 = input("1. Pega la URL del m3u8 (Enter para usar el de prueba):\n> ").strip()
    if not m3u8: m3u8 = "https://vz-572fbc8f-66a.b-cdn.net/6abe2fb5-5511-4260-8332-428e46bc7fcd/playlist.m3u8"
    
    print("\n2. Pega el comando FETCH completo:")
    fetch_input = ""
    while True:
        line = input()
        if not line: break
        fetch_input += line + "\n"
    
    lic_url, headers = parse_fetch_v21(fetch_input)
    
    if headers:
        print(f"\n[OK] Se han detectado {len(headers)} headers.")
        keys = automatizar_cdrm_lab(headers)
        
        if keys:
            nombre = input("\n3. Nombre para el archivo final (sin .mkv):\n> ").strip()
            if not nombre: nombre = "video_bunny_lab"
            
            save_path = os.path.join(BASE_SAVE_PATH, "LAB_DOWNLOADS")
            if not os.path.exists(save_path): os.makedirs(save_path)
            
            comando = [
                "N_m3u8DL-RE", m3u8,
                "--save-dir", save_path,
                "--save-name", nombre,
                "-H", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
                "-H", "Origin: https://iframe.mediadelivery.net",
                "-H", "Referer: https://iframe.mediadelivery.net/",
                "--auto-select",
                "-M", "format=mkv"
            ]
            for k in keys: comando.extend(["--key", k])
            
            print(f"\n[Lanzando descarga] -> Guardando en {save_path}")
            subprocess.run(comando)
    else:
        print("[!] Error: No se pudo extraer nada del fetch. Asegúrate de copiarlo completo.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[!] Proceso detenido.")
