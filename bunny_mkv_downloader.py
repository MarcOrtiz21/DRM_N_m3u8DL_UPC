import os
import re
import json
import requests
import subprocess

# --- CONFIGURACION ---
BASE_DIR = r"C:\Users\marco\OneDrive - MSFT\UPC\VIDEOS_ASES"
RE_PATH = "N_m3u8DL-RE.exe"

def select_folder():
    """Interfaz para seleccionar o crear la carpeta de la asignatura"""
    if not os.path.exists(BASE_DIR):
        os.makedirs(BASE_DIR)
    
    folders = [f for f in os.listdir(BASE_DIR) if os.path.isdir(os.path.join(BASE_DIR, f))]
    
    print("\n--- SELECCION DE ASIGNATURA ---")
    print(f"0. [RAIZ] {BASE_DIR}")
    for i, folder in enumerate(folders, 1):
        print(f"{i}. {folder}")
    print(f"{len(folders) + 1}. [CREAR NUEVA CARPETA]")
    
    try:
        u_input = input("\nSelecciona una opcion (numero): ").strip()
        if not u_input: return BASE_DIR
        choice = int(u_input)
        if choice == 0: return BASE_DIR
        elif 1 <= choice <= len(folders): return os.path.join(BASE_DIR, folders[choice-1])
        elif choice == len(folders) + 1:
            new_f = input("Nombre de la nueva carpeta: ").strip()
            path = os.path.join(BASE_DIR, new_f)
            os.makedirs(path, exist_ok=True)
            return path
    except:
        pass
    return BASE_DIR

def parse_fetch_or_headers(input_str):
    """Extrae URL y Headers independientemente de si pegan el fetch o solo el JSON"""
    license_url = None
    headers = {}

    # Intentar extraer URL de licencia si es un fetch
    url_match = re.search(r'fetch\("(.*?)"', input_str)
    if url_match:
        license_url = url_match.group(1)
    else:
        # Si no hay fetch, quizas la URL sea una linea suelta
        urls = re.findall(r'https://video\.bunnycdn\.com/WidevineLicense/.*?token=[\w-]+', input_str)
        if urls: license_url = urls[0]

    # Intentar extraer bloque JSON de headers
    if '"headers":' in input_str:
        h_match = re.search(r'"headers":\s*({.*?})', input_str, re.DOTALL)
        if h_match:
            try:
                h_json = h_match.group(1).replace('\n', '').replace('  ', '')
                h_json = re.sub(r',\s*}', '}', h_json)
                headers = json.loads(h_json)
            except: pass
    
    # Si lo pegado ES directamente el JSON (tu caso)
    if not headers and input_str.strip().startswith('{'):
        try:
            h_json = input_str.strip().replace('\n', '')
            h_json = re.sub(r',\s*}', '}', h_json)
            headers = json.loads(h_json)
        except: pass

    # Inyectar campos obligatorios de BunnyCDN si no estan
    headers["Origin"] = "https://iframe.mediadelivery.net"
    headers["Referer"] = "https://iframe.mediadelivery.net/"
    
    return license_url, headers

def get_pssh(m3u8_url):
    """Obtiene el PSSH desde el m3u8"""
    try:
        r = requests.get(m3u8_url, timeout=10)
        match = re.search(r'#EXT-X-WRM-OBJ:.*BASE64:(.*)', r.text)
        if match:
            return match.group(1).split(',')[0].split('#')[0].strip()
    except:
        pass
    return None

def main():
    print("=== ASISTENTE DE DESCARGA MKV (UPC) ===")
    
    target_dir = select_folder()
    print(f"[*] Carpeta destino: {target_dir}")
    
    m3u8_url = input("\n1. URL del .m3u8: ").strip()
    nombre = input("2. Nombre de la clase (sin extension): ").strip()
    
    print("\n3. Pega el FETCH de Chrome (o solo los Headers JSON).")
    print("   Pulsa ENTER DOS VECES seguidas para finalizar el pegado:")
    
    lines = []
    while True:
        line = input()
        if line == "" and (not lines or lines[-1] == ""):
            break
        lines.append(line)
    input_str = "\n".join(lines)

    license_url, headers = parse_fetch_or_headers(input_str)
    
    if not license_url:
        print("\n[!] No se encontro la URL de licencia en lo pegado.")
        license_url = input("[?] Pega la URL de Widevine License manualmente: ").strip()

    pssh = get_pssh(m3u8_url)
    if pssh:
        print(f"[+] PSSH detectado automaticamente: {pssh[:30]}...")
    else:
        pssh = input("[!] No se detecto PSSH. Pegalo manualmente (Base64): ").strip()

    # Intentar obtener keys automaticamente
    print("[*] Intentando obtener keys via API de CDRM Project...")
    keys = []
    try:
        payload = {
            "PSSH": pssh,
            "License URL": license_url,
            "Headers": json.dumps(headers),
            "JSON Proxy": ""
        }
        r = requests.post("https://cdrm-project.com/api", json=payload, timeout=15)
        if r.status_code == 200:
            res = r.json()
            if 'keys' in res:
                keys = [k for k in res['keys'] if isinstance(k, str)]
    except:
        pass

    if not keys:
        print("[!] No se pudieron obtener las keys automaticamente.")
        print("[*] Introduce las KEYS manualmente (id:key). Enter doble para terminar:")
        while True:
            k = input("> ").strip()
            if not k: break
            # Soporte para pegado multiple
            for line in k.split('\n'):
                if ':' in line: keys.append(line.strip())

    if not keys:
        print("[!] Sin keys no se puede realizar la descarga.")
        return

    # Ejecutar descarga en MKV
    print(f"\n[*] Iniciando descarga y fusion en MKV...")
    command = [
        RE_PATH,
        m3u8_url,
        "--save-dir", target_dir,
        "--save-name", nombre,
        "--mux-after-done", "format=mkv",
        "--auto-select",
        "-H", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
        "-H", "Referer: https://iframe.mediadelivery.net/",
        "-H", "Origin: https://iframe.mediadelivery.net"
    ]

    for k in keys:
        command.extend(["--key", k])

    try:
        subprocess.run(command, check=True)
        print(f"\n[OK] Finalizado. Archivo en: {target_dir}")
    except:
        print("\n[!] Error al ejecutar la descarga.")

if __name__ == "__main__":
    main()
