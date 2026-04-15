import os
import re
import json
import subprocess
import time
import sys
from urllib.parse import urlparse

try:
    from DrissionPage import ChromiumPage, ChromiumOptions
except ImportError:
    print("Instalando dependencias de DrissionPage...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "DrissionPage"])
    from DrissionPage import ChromiumPage, ChromiumOptions

BASE_SAVE_PATH = r"C:\Users\marco\OneDrive - MSFT\UPC\VIDEOS_ASES\LAB_DOWNLOADS"

def parse_fetch_v21(fetch_text):
    """Extrae URL y Headers del fetch como en el laboratorio anterior"""
    url = None
    headers_dict = {}
    try:
        url_match = re.search(r'fetch\((?:\'|")([^\'"]+)(?:\'|")', fetch_text)
        if url_match:
            url = url_match.group(1)
        
        headers_match = re.search(r'["\']headers["\']\s*:\s*(\{.*?\})', fetch_text, re.DOTALL)
        if headers_match:
            headers_str = headers_match.group(1)
            pares = re.findall(r'["\']([^"\']+)["\']\s*:\s*["\']([^"\']+)["\']', headers_str)
            headers_dict = {k: v for k, v in pares}
            
            headers_dict["Origin"] = "https://iframe.mediadelivery.net"
            headers_dict["Referer"] = "https://iframe.mediadelivery.net/"
            
        return url, headers_dict
    except Exception as e:
        print(f"[!] Error extrayendo Fetch: {e}")
    return None, None

def get_keys_via_getwvkeys(pssh, license_url, headers_dict):
    """Automatiza GetWVKeys.cc mediante el navegador"""
    print("\n-> Inicializando navegador (perfil persistente)...")
    
    # Configuramos DrissionPage para que guarde las cookies de Discord
    user_data_path = os.path.join(os.getcwd(), "DrissionProfile")
    co = ChromiumOptions().set_user_data_path(user_data_path)
    page = ChromiumPage(co)
    
    try:
        page.get('https://getwvkeys.cc/')
        time.sleep(3)
        
        # Verificar si estamos logueados
        if "Login with Discord" in page.html or "login" in page.url.lower():
            print("\n" + "="*50)
            print(" [INICIO DE SESIÓN REQUERIDO] ")
            print(" Pareces no estar logueado en GetWVKeys.cc.")
            print(" Ve a la ventana del navegador, inicia sesión con Discord y vuelve aquí.")
            print("="*50)
            input(">>> Presiona ENTER cuando hayas iniciado sesión en la página... ")
            page.get('https://getwvkeys.cc/') # Recargamos
            time.sleep(2)
            
        print("\n-> Rellenando formulario de GetWVKeys...")
        
        # Como GetWVKeys puede cambiar IDs, usamos esperas genéricas interactivas
        print("Buscando caja de PSSH...")
        campos_texto = page.eles('tag:input') + page.eles('tag:textarea')
        
        pssh_injected = False
        url_injected = False
        headers_injected = False
        
        # Intento de autocompletado si reconocemos la interfaz típica de WVKeys
        try:
            # PSSH
            pssh_box = page.ele('xpath://*[@id="pssh" or @name="pssh" or @placeholder="PSSH"]')
            if pssh_box:
                pssh_box.clear()
                pssh_box.input(pssh)
                pssh_injected = True
                
            # License URL
            url_box = page.ele('xpath://*[@id="license" or @name="license" or contains(@placeholder, "License")]')
            if url_box:
                url_box.clear()
                url_box.input(license_url)
                url_injected = True
            
            # Headers
            headers_box = page.ele('xpath://textarea[contains(@id, "header") or contains(@name, "header")]')
            if headers_box:
                headers_box.clear()
                headers_json = json.dumps(headers_dict, separators=(',', ':'))
                headers_box.input(headers_json)
                headers_injected = True
        except:
            pass

        if not (pssh_injected and url_injected and headers_injected):
            print("[!] La web ha cambiado de aspecto. Rellena los datos manualmente en la ventana del navegador.")
            print(f"PSSH: {pssh}\n")
            print(f"URL: {license_url}\n")
            print(f"HEADERS: {json.dumps(headers_dict)}\n")
        else:
            print("[OK] Datos completados correctamente en la web.")
            
            # Click automático en Submit si lo encontramos
            submit_btn = page.ele('xpath://button[contains(text(), "Submit") or contains(text(), "Get Keys")]')
            if submit_btn:
                submit_btn.click()
                print("-> Haciendo click en Submit automáticamente...")

        print("\n" + "="*50)
        input(">>> [ACCIÓN MÁQUINA] Revisa el navegador, dale a Submit si no lo ha hecho, y presiona ENTER cuando las KEYS estén en pantalla... ")
        print("="*50)

        # Extraer llaves
        html = page.html
        keys = re.findall(r'([a-fA-F0-9]{32}:[a-fA-F0-9]{32})', html)
        if keys:
            keys = list(set(keys))
            print(f"\n[EXITO] Se han extraído {len(keys)} llaves de la web:")
            for k in keys: print(f"  > {k}")
            return keys
        else:
            print("[!] No se detectó ninguna llave válida (formato KID:KEY) en la pantalla.")
            return []
            
    except Exception as e:
        print(f"[!] Error durante automatización: {e}")
    finally:
        page.quit()

def main():
    print("="*60)
    print("      LABORATORIO DRM v3 - GETWVKEYS AUTOMATOR")
    print("="*60)
    
    m3u8 = input("1. Pega la URL del m3u8:\n> ").strip()
    if not m3u8: return
    
    pssh = input("\n2. Pega el PSSH (detectado por la extensión):\n> ").strip()
    if not pssh: return
    
    print("\n3. Pega el comando FETCH completo de la licencia (Copy as fetch):")
    fetch_input = ""
    while True:
        line = input()
        if not line: break
        fetch_input += line + "\n"
    
    lic_url, headers = parse_fetch_v21(fetch_input)
    if not lic_url or not headers:
        print("[!] No se pudo extraer la Licencia o los Headers del fetch.")
        return
        
    keys = get_keys_via_getwvkeys(pssh, lic_url, headers)
    
    if keys:
        nombre = input("\n4. Nombre para el archivo final (sin .mkv):\n> ").strip()
        if not nombre: nombre = "ases_video"
        
        if not os.path.exists(BASE_SAVE_PATH):
            os.makedirs(BASE_SAVE_PATH)
            
        comando = [
            "N_m3u8DL-RE", m3u8,
            "--save-dir", BASE_SAVE_PATH,
            "--save-name", nombre,
            "--auto-select",
            "-M", "format=mkv"
        ]
        
        # Mantenemos las cabeceras estándar para descarga Bunny si las hay
        comando.extend(["-H", "Origin: https://iframe.mediadelivery.net"])
        comando.extend(["-H", "Referer: https://iframe.mediadelivery.net/"])
        
        for k in keys: comando.extend(["--key", k])
        
        print(f"\n[Iniciando descarga] -> Guardando en {BASE_SAVE_PATH}")
        subprocess.run(comando)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCancelado.")
