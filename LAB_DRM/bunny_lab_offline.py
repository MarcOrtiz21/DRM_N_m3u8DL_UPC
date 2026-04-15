"""
LABORATORIO DRM vFINAL - DESENCRIPTADOR OFFLINE
================================================
Este script no depende de NINGUNA web de terceros.
Utiliza tu propio CDM (.wvd) para extraer las llaves Widevine
directamente del servidor de licencias de Bunny CDN.

Uso:
  1. Pega la URL de la clase de ASES
  2. El script extrae automáticamente el iframe, la licencia, el PSSH y el m3u8
  3. Desencripta las llaves offline con tu CDM
  4. Descarga y desencripta el vídeo con N_m3u8DL-RE

Requiere:
  pip install pywidevine requests
"""
import os
import re
import subprocess
import sys
import time

try:
    from pywidevine.cdm import Cdm
    from pywidevine.device import Device
    from pywidevine.pssh import PSSH
    import requests
except ImportError:
    print("Instalando dependencias...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pywidevine", "requests"])
    from pywidevine.cdm import Cdm
    from pywidevine.device import Device
    from pywidevine.pssh import PSSH
    import requests

# --- CONFIGURACIÓN ---
BASE_SAVE_PATH = r"C:\Users\marco\OneDrive - MSFT\UPC\VIDEOS_ASES"
PRESET_PERIODS = ["Parcial", "Intensivo Parcial", "Final", "Intensivo Final"]

# Buscar automáticamente archivos .wvd en la carpeta WYD
WVD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "WYD")
if not os.path.isdir(WVD_DIR):
    WVD_DIR = r"C:\Users\marco\Documents\DRM_DOWNLOADER\WYD"

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36"

# ==========================================
# SECCIÓN 1: EXTRACCIÓN DE DATOS DE ASES
# ==========================================

def extract_video_data_from_ases(ases_url):
    """Extrae embed URL, license URL, m3u8, y PSSH de una URL de clase de ASES"""
    print("\n[PASO 1] Obteniendo datos del vídeo de ASES...")
    
    s = requests.Session()
    s.headers.update({"user-agent": UA})
    
    # Acceder a la página de ASES
    r = s.get(ases_url)
    if r.status_code != 200:
        print(f"  [!] Error accediendo a ASES: {r.status_code}")
        return None
    print(f"  Página ASES: OK ({r.status_code})")
    
    # Buscar iframe embed URL
    embed_matches = re.findall(
        r'(https://iframe\.mediadelivery\.net/embed/[^\s"<>\']+)', r.text
    )
    if not embed_matches:
        data_matches = re.findall(r'data-url="([^"]+)"', r.text)
        if data_matches:
            embed_matches = [data_matches[0]]
    
    if not embed_matches:
        print("  [!] No se encontró el iframe de vídeo en la página de ASES.")
        return None
    
    embed_url = embed_matches[0].replace("&amp;", "&")
    print(f"  Embed URL: {embed_url[:100]}...")
    
    # Acceder al iframe para sacar los datos del reproductor
    r2 = s.get(embed_url, headers={"referer": ases_url.split("/campus")[0] + "/"})
    if r2.status_code != 200:
        print(f"  [!] Error accediendo al iframe: {r2.status_code}")
        return None
    print(f"  Iframe: OK ({r2.status_code})")
    
    # Extraer License URL (Widevine)
    lic_matches = re.findall(
        r"(https://video\.bunnycdn\.com/WidevineLicense/[^'\"\\]+)", r2.text
    )
    if not lic_matches:
        print("  [!] No se encontró License URL. ¿El vídeo tiene DRM?")
        return None
    license_url = lic_matches[0].replace("&amp;", "&")
    print(f"  License URL: OK")
    
    # Extraer m3u8
    m3u8_matches = re.findall(
        r"(https://vz-[^'\"\\]+/playlist\.m3u8)", r2.text
    )
    m3u8_url = m3u8_matches[0] if m3u8_matches else None
    print(f"  m3u8 URL: {m3u8_url}")
    
    # Extraer PSSH del HTML (está en el init data del reproductor HLS.js)
    # El PSSH normalmente viene en los segmentos de vídeo, pero lo tenemos de la extensión
    # Lo extraemos del PSSH que genera el reproductor al iniciar
    pssh_matches = re.findall(
        r'PSSH.*?([A-Za-z0-9+/=]{60,})', r2.text
    )
    
    # Extraer título del vídeo
    title_matches = re.findall(r'og:title"\s+content="([^"]+)"', r2.text)
    title = title_matches[0] if title_matches else "video_ases"
    print(f"  Título: {title}")
    
    return {
        "embed_url": embed_url,
        "license_url": license_url,
        "m3u8_url": m3u8_url,
        "title": title,
    }

# ==========================================
# SECCIÓN 2: DESENCRIPTACIÓN OFFLINE
# ==========================================

def find_wvd_files():
    """Busca archivos .wvd disponibles"""
    wvd_files = []
    if os.path.isdir(WVD_DIR):
        for f in os.listdir(WVD_DIR):
            if f.endswith(".wvd"):
                wvd_files.append(os.path.join(WVD_DIR, f))
    return wvd_files

def extract_pssh_from_m3u8(m3u8_url):
    """Extrae PSSH automáticamente del manifiesto HLS (m3u8)"""
    import base64
    
    bunny_headers = {
        "user-agent": UA,
        "referer": "https://iframe.mediadelivery.net/",
        "origin": "https://iframe.mediadelivery.net",
    }
    
    try:
        # 1. Descargar master playlist
        r = requests.get(m3u8_url, headers=bunny_headers)
        if r.status_code != 200:
            print(f"  [!] m3u8 devolvió {r.status_code}")
            return None
        
        # 2. Encontrar sub-playlists (video streams)
        base = m3u8_url.rsplit("/", 1)[0]
        sub_urls = []
        for line in r.text.strip().split("\n"):
            line = line.strip()
            if line and not line.startswith("#"):
                if line.startswith("http"):
                    sub_urls.append(line)
                else:
                    sub_urls.append(base + "/" + line)
        
        if not sub_urls:
            print("  [!] No se encontraron sub-playlists en el m3u8")
            return None
        
        # Filtrar solo streams de video (no audio)
        video_subs = [u for u in sub_urls if "stream_1" not in u]  # stream_1 suele ser audio
        if not video_subs:
            video_subs = sub_urls
        
        # 3. Descargar primera sub-playlist de video
        r2 = requests.get(video_subs[0], headers=bunny_headers)
        if r2.status_code != 200:
            print(f"  [!] Sub-playlist devolvió {r2.status_code}")
            return None
        
        # MÉTODO A: Extraer PSSH directamente del tag EXT-X-KEY (data:text/plain;base64,...)
        key_pssh = re.findall(
            r'#EXT-X-KEY:.*?URI="data:text/plain;base64,([A-Za-z0-9+/=]+)"', r2.text
        )
        if key_pssh:
            print("  PSSH extraído del tag EXT-X-KEY")
            return key_pssh[0]
        
        # MÉTODO B: Extraer PSSH del init segment binario
        map_matches = re.findall(r'#EXT-X-MAP:URI="([^"]+)"', r2.text)
        if map_matches:
            init_uri = map_matches[0]
            if not init_uri.startswith("http"):
                init_uri = video_subs[0].rsplit("/", 1)[0] + "/" + init_uri
            
            r3 = requests.get(init_uri, headers=bunny_headers)
            if r3.status_code == 200:
                pssh = extract_pssh_from_init(r3.content)
                if pssh:
                    print("  PSSH extraído del init segment")
                    return pssh
        
        print("  [!] No se pudo encontrar PSSH en ningún método")
        
    except Exception as e:
        print(f"  [!] Error extrayendo PSSH: {e}")
    return None

def extract_pssh_from_init(init_data):
    """Extrae PSSH box Widevine de un segmento de inicialización"""
    import base64
    # Widevine System ID
    widevine_system_id = bytes.fromhex("edef8ba979d64acea3c827dcd51d21ed")
    idx = init_data.find(widevine_system_id)
    if idx == -1:
        return None
    
    # La PSSH box empieza 12 bytes antes del system ID
    box_start = idx - 12
    if box_start < 0:
        return None
    
    # Leer tamaño de la box (4 bytes big-endian)
    box_size = int.from_bytes(init_data[box_start:box_start+4], 'big')
    pssh_box = init_data[box_start:box_start+box_size]
    
    return base64.b64encode(pssh_box).decode()

def decrypt_keys_offline(license_url, pssh_b64):
    """Desencripta las llaves Widevine usando pywidevine 100% offline"""
    print("\n[PASO 2] Desencriptando llaves Widevine offline...")
    
    wvd_files = find_wvd_files()
    if not wvd_files:
        print(f"  [!] No se encontraron archivos .wvd en {WVD_DIR}")
        return []
    
    print(f"  CDMs disponibles: {len(wvd_files)}")
    
    headers = {
        "accept": "*/*",
        "content-type": "application/octet-stream",
        "origin": "https://iframe.mediadelivery.net",
        "referer": "https://iframe.mediadelivery.net/",
        "user-agent": UA,
    }
    
    pssh = PSSH(pssh_b64)
    
    for wvd_path in wvd_files:
        wvd_name = os.path.basename(wvd_path)
        print(f"\n  Probando CDM: {wvd_name}")
        
        try:
            device = Device.load(wvd_path)
            cdm = Cdm.from_device(device)
            session_id = cdm.open()
            
            challenge = cdm.get_license_challenge(session_id, pssh)
            print(f"  Challenge: {len(challenge)} bytes")
            
            response = requests.post(license_url, headers=headers, data=challenge)
            print(f"  Servidor: {response.status_code}")
            
            if response.status_code == 200:
                cdm.parse_license(session_id, response.content)
                
                keys = []
                for key in cdm.get_keys(session_id):
                    kid_hex = key.kid.hex  # uuid.UUID.hex -> str sin guiones
                    key_hex = key.key.hex()  # bytes.hex() -> str
                    
                    if key.type == "CONTENT":
                        print(f"    [KEY] {kid_hex}:{key_hex}")
                        keys.append(f"{kid_hex}:{key_hex}")
                
                cdm.close(session_id)
                
                if keys:
                    print(f"\n  [ÉXITO] {len(keys)} llaves extraídas con {wvd_name}")
                    return keys
            else:
                error_msg = response.text[:200] if response.text else "(vacío)"
                print(f"  Error: {error_msg}")
                cdm.close(session_id)
                
        except Exception as e:
            print(f"  Error con {wvd_name}: {e}")
    
    return []

# ==========================================
# SECCIÓN 3: GESTIÓN DE DIRECTORIOS
# ==========================================

def _list_subdirs(path):
    """Lista subdirectorios ordenados de una carpeta."""
    if not os.path.isdir(path):
        return []
    return sorted([f for f in os.listdir(path) if os.path.isdir(os.path.join(path, f))])

def _count_files(path):
    """Cuenta archivos (no dirs) en una carpeta."""
    try:
        return len([f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))])
    except:
        return 0

def _show_folder_menu(current_path):
    """Muestra menú de navegación multinivel. Retorna path seleccionado."""
    while True:
        rel = os.path.relpath(current_path, BASE_SAVE_PATH)
        header = rel if rel != "." else "Raíz"
        print(f"\n  ┌─ 📁 {header}")
        print(f"  │")
        
        subdirs = _list_subdirs(current_path)
        
        for i, d in enumerate(subdirs, 1):
            print(f"  │  {i}. {d}")
        
        if not subdirs:
            print(f"  │  (carpeta vacía)")
        
        idx = len(subdirs)
        n_select = idx + 1
        n_new    = idx + 2
        n_rename = idx + 3
        n_delete = idx + 4
        n_back   = idx + 5
        
        print(f"  │")
        print(f"  │  {n_select}. ✅ Guardar aquí")
        print(f"  │  {n_new}. ➕ Nueva carpeta")
        if subdirs:
            print(f"  │  {n_rename}. ✏️  Renombrar")
            print(f"  │  {n_delete}. 🗑️  Eliminar")
        if current_path != BASE_SAVE_PATH:
            print(f"  │  {n_back}. ⬅  Atrás")
        print(f"  └─")
        
        choice = input("  > ").strip()
        if not choice:
            return current_path
        
        if choice.isdigit():
            n = int(choice)
            if 1 <= n <= len(subdirs):
                current_path = os.path.join(current_path, subdirs[n - 1])
                continue
            elif n == n_select:
                os.makedirs(current_path, exist_ok=True)
                return current_path
            elif n == n_new:
                parent_name = os.path.basename(current_path).lower()
                existing_weeks = [d for d in subdirs if d.lower().startswith("semana")]
                suggestion = ""
                if any(p.lower() in parent_name for p in ["parcial", "final", "post"]):
                    next_week = len(existing_weeks) + 1
                    suggestion = f" (Enter = Semana {next_week})"
                
                name = input(f"  Nombre{suggestion}: ").strip()
                if not name and suggestion:
                    name = f"Semana {len(existing_weeks) + 1}"
                if name:
                    new_path = os.path.join(current_path, name)
                    os.makedirs(new_path, exist_ok=True)
                    print(f"  ✔ Creada: {name}")
                    current_path = new_path
                continue
            elif n == n_rename and subdirs:
                print("  ¿Cuál renombrar?")
                for i, d in enumerate(subdirs, 1):
                    print(f"    {i}. {d}")
                sel = input("  > ").strip()
                if sel.isdigit() and 1 <= int(sel) <= len(subdirs):
                    old_name = subdirs[int(sel) - 1]
                    new_name = input(f"  Nuevo nombre para '{old_name}': ").strip()
                    if new_name and new_name != old_name:
                        try:
                            os.rename(os.path.join(current_path, old_name),
                                      os.path.join(current_path, new_name))
                            print(f"  ✔ '{old_name}' → '{new_name}'")
                        except Exception as e:
                            print(f"  ✖ Error: {e}")
                continue
            elif n == n_delete and subdirs:
                print("  ¿Cuál eliminar?")
                for i, d in enumerate(subdirs, 1):
                    sub_path = os.path.join(current_path, d)
                    total = _count_files(sub_path) + len(_list_subdirs(sub_path))
                    warn = f" ⚠ {total} elementos" if total > 0 else " (vacía)"
                    print(f"    {i}. {d}{warn}")
                sel = input("  > ").strip()
                if sel.isdigit() and 1 <= int(sel) <= len(subdirs):
                    target_name = subdirs[int(sel) - 1]
                    target_path = os.path.join(current_path, target_name)
                    confirm = input(f"  ¿Eliminar '{target_name}'? (s/N): ").strip().lower()
                    if confirm == "s":
                        import shutil
                        try:
                            shutil.rmtree(target_path)
                            print(f"  ✔ Eliminada")
                        except Exception as e:
                            print(f"  ✖ Error: {e}")
                continue
            elif n == n_back and current_path != BASE_SAVE_PATH:
                current_path = os.path.dirname(current_path)
                continue
        
        print("  ✖ Opción no válida")

def choose_save_directory():
    """Menú interactivo multinivel para elegir dónde guardar."""
    print(f"\n  ╔══════════════════════════════════════════╗")
    print(f"  ║  📂  SELECCIONAR CARPETA DE DESTINO      ║")
    print(f"  ╚══════════════════════════════════════════╝")
    
    if not os.path.exists(BASE_SAVE_PATH):
        os.makedirs(BASE_SAVE_PATH)
    
    return _show_folder_menu(BASE_SAVE_PATH)

# ==========================================
# SECCIÓN 4: DESCARGA
# ==========================================

def download_video(m3u8_url, keys, save_path, filename):
    """Descarga y desencripta el vídeo con N_m3u8DL-RE"""
    print(f"\n[PASO 3] Descargando y desencriptando...")
    print(f"  Destino: {save_path}")
    print(f"  Archivo: {filename}.mkv")
    print(f"  Keys: {len(keys)}")
    
    comando = [
        "N_m3u8DL-RE", m3u8_url,
        "--save-dir", save_path,
        "--save-name", filename,
        "-H", f"User-Agent: {UA}",
        "-H", "Origin: https://iframe.mediadelivery.net",
        "-H", "Referer: https://iframe.mediadelivery.net/",
        "--auto-select",
        "-M", "format=mkv",
    ]
    
    for k in keys:
        comando.extend(["--key", k])
    
    result = subprocess.run(
        comando, 
        cwd=os.path.dirname(os.path.abspath(__file__)) + "/.."
    )
    return result.returncode == 0

# ==========================================
# SECCIÓN 5: EXTRACCIÓN DESDE EMBED URL
# ==========================================

def extract_video_data_from_embed(embed_url):
    """Extrae license URL, m3u8, y título directamente de una URL de iframe embed"""
    print("\n[PASO 1] Obteniendo datos del iframe embed...")
    
    s = requests.Session()
    s.headers.update({"user-agent": UA})
    
    # Extraer GUID y library_id de la embed URL
    embed_match = re.search(r'/embed/(\d+)/([a-f0-9\-]+)', embed_url)
    if not embed_match:
        print("  [!] No se pudo parsear la URL del embed.")
        return None
    library_id = embed_match.group(1)
    guid = embed_match.group(2)
    print(f"  Library: {library_id}, GUID: {guid}")
    
    # Extraer token y expires del embed URL (si los tiene)
    from urllib.parse import urlparse, parse_qs
    parsed = urlparse(embed_url)
    params = parse_qs(parsed.query)
    token = params.get("token", [None])[0]
    expires = params.get("expires", [None])[0]
    
    r = s.get(embed_url, headers={"referer": "https://www.asesacademia.com/"})
    if r.status_code != 200:
        print(f"  [!] Error accediendo al iframe: {r.status_code}")
        return None
    print(f"  Iframe: OK ({r.status_code})")
    
    # License URL - intentar extraer del HTML
    lic_matches = re.findall(
        r"(https://video\.bunnycdn\.com/WidevineLicense/[^'\"\\]+)", r.text
    )
    if lic_matches:
        license_url = lic_matches[0].replace("&amp;", "&")
        print(f"  License URL: OK (del HTML)")
    elif token and expires:
        # Construir la License URL a partir de los componentes del embed
        license_url = f"https://video.bunnycdn.com/WidevineLicense/{library_id}/{guid}?token={token}&expires={expires}"
        print(f"  License URL: OK (construida desde token del embed)")
    else:
        print("  [!] No se encontró License URL y el embed no tiene token.")
        print("  Usa mejor la URL completa de ASES (con ?key=...)")
        return None
    
    # m3u8 - intentar extraer del HTML, si no construir
    m3u8_matches = re.findall(
        r"(https://vz-[^'\"\\]+/playlist\.m3u8)", r.text
    )
    if m3u8_matches:
        m3u8_url = m3u8_matches[0]
    else:
        # Intentar construir el CDN base desde el HTML
        cdn_matches = re.findall(r"(https://vz-[a-f0-9\-]+\.b-cdn\.net)", r.text)
        if cdn_matches:
            m3u8_url = f"{cdn_matches[0]}/{guid}/playlist.m3u8"
        else:
            m3u8_url = None
    print(f"  m3u8 URL: {m3u8_url}")
    
    # Título
    title_matches = re.findall(r'og:title"\s+content="([^"]+)"', r.text)
    title = title_matches[0] if title_matches else "video_ases"
    print(f"  Título: {title}")
    
    return {
        "embed_url": embed_url,
        "license_url": license_url,
        "m3u8_url": m3u8_url,
        "title": title,
    }

def extract_video_data_from_m3u8(m3u8_url, license_url):
    """Construye datos para descarga manual cuando el usuario pega la m3u8 y license URL"""
    return {
        "embed_url": None,
        "license_url": license_url,
        "m3u8_url": m3u8_url,
        "title": "video_manual",
    }

# ==========================================
# MAIN
# ==========================================

def detect_and_extract(user_input):
    """Detecta qué tipo de URL/dato ha pegado el usuario y extrae los datos"""
    
    # Caso 1: URL de ASES (asesacademia.com)
    if "asesacademia.com" in user_input:
        print("\n  [Detectado: URL de ASES Academia]")
        return extract_video_data_from_ases(user_input)
    
    # Caso 2: URL de embed de mediadelivery (iframe)
    if "iframe.mediadelivery.net/embed/" in user_input:
        print("\n  [Detectado: Embed URL de Bunny]")
        return extract_video_data_from_embed(user_input)
    
    # Caso 3: URL del m3u8 directamente
    if "playlist.m3u8" in user_input or "b-cdn.net" in user_input:
        print("\n  [Detectado: m3u8 directo]")
        print("  Necesito también la License URL.")
        print("  Puedes encontrarla en DevTools > Network > busca 'WidevineLicense'")
        lic_url = input("  Pega la License URL:\n  > ").strip()
        if not lic_url:
            return None
        return extract_video_data_from_m3u8(user_input, lic_url)
    
    # Caso 4: Quizás es una URL de ASES sin el dominio completo
    if "/campus/" in user_input or "/virtualclasses/" in user_input:
        # Intentar añadir dominio
        if not user_input.startswith("http"):
            user_input = "https://www.asesacademia.com" + user_input
        print("\n  [Detectado: URL parcial de ASES]")
        return extract_video_data_from_ases(user_input)
    
    print("  [!] No se reconoce el tipo de URL.")
    print("  Formatos aceptados:")
    print("    - URL de clase ASES (con ?key=...)")
    print("    - URL del iframe (iframe.mediadelivery.net/embed/...)")
    print("    - URL del m3u8 directa (vz-xxx.b-cdn.net/.../playlist.m3u8)")
    return None

def _banner():
    print("\n")
    print("  ╔══════════════════════════════════════════════════════╗")
    print("  ║                                                      ║")
    print("  ║   🔓  ASES DRM DOWNLOADER  ·  Modo Offline           ║")
    print("  ║       Desencriptación local sin webs externas        ║")
    print("  ║                                                      ║")
    print("  ╚══════════════════════════════════════════════════════╝")

def _section(title):
    w = 54
    pad = w - len(title) - 4
    print(f"\n  ┌{'─' * w}┐")
    print(f"  │  {title}{' ' * max(pad, 0)}  │")
    print(f"  └{'─' * w}┘")

def main():
    _banner()
    
    # Verificar CDMs
    wvd_files = find_wvd_files()
    if not wvd_files:
        print(f"\n  ✖ No se encontraron archivos .wvd en: {WVD_DIR}")
        print("    Coloca tu archivo .wvd ahí para poder desencriptar.")
        return
    cdm_names = [os.path.basename(f).split("_")[0:2] for f in wvd_files]
    print(f"  🔑 CDMs: {len(wvd_files)} detectados")
    
    # Seleccionar directorio de guardado
    save_path = choose_save_directory()
    rel_save = os.path.relpath(save_path, BASE_SAVE_PATH)
    print(f"\n  📂 Destino: {rel_save}")
    
    descargas = []
    
    while True:
        # Resumen de sesión
        if descargas:
            _section(f"Sesión: {len(descargas)} descarga(s)")
            for i, d in enumerate(descargas, 1):
                print(f"  │  ✔ {d}")
        
        # Menú de acciones
        print(f"\n  ┌──────────────────────────────────────────────────────┐")
        print(f"  │  📂 Destino actual: {rel_save[:35]:<35} │")
        print(f"  ├──────────────────────────────────────────────────────┤")
        print(f"  │  Pega una URL para descargar:                       │")
        print(f"  │    • URL de ASES (con ?key=...)                     │")
        print(f"  │    • Iframe embed (iframe.mediadelivery.net/...)     │")
        print(f"  │    • m3u8 directo (vz-xxx.b-cdn.net/...)            │")
        print(f"  │                                                      │")
        print(f"  │  O escribe un comando:                              │")
        print(f"  │    cd  → Cambiar carpeta destino                    │")
        print(f"  │    q   → Salir                                      │")
        print(f"  └──────────────────────────────────────────────────────┘")
        
        user_input = input("\n  ▶ ").strip()
        if not user_input or user_input.lower() == "q":
            break
        
        # Cambiar carpeta destino
        if user_input.lower() == "cd":
            save_path = choose_save_directory()
            rel_save = os.path.relpath(save_path, BASE_SAVE_PATH)
            print(f"\n  📂 Nuevo destino: {rel_save}")
            continue
        
        # 1. Detectar tipo y extraer datos
        _section("PASO 1 · Extrayendo datos del vídeo")
        data = detect_and_extract(user_input)
        if not data:
            print("  ✖ No se pudieron extraer los datos del vídeo.")
            continue
        
        if not data["m3u8_url"]:
            print("  ✖ No se encontró la URL del m3u8.")
            continue
        
        # 2. Extraer PSSH del stream (automático)
        _section("PASO 2 · Extrayendo PSSH del stream")
        pssh_b64 = extract_pssh_from_m3u8(data["m3u8_url"])
        if not pssh_b64:
            print("  ✖ Extracción automática fallida.")
            pssh_b64 = input("  Pega el PSSH manualmente: ").strip()
            if not pssh_b64:
                continue
        else:
            print(f"  ✔ PSSH: {pssh_b64[:50]}...")
        
        # 3. Desencriptar las llaves (offline)
        _section("PASO 3 · Desencriptando llaves")
        keys = decrypt_keys_offline(data["license_url"], pssh_b64)
        if not keys:
            print("  ✖ No se pudieron extraer las llaves.")
            continue
        
        # 4. Nombre del archivo
        suggested = re.sub(r'[^\w\s\-]', '', data["title"]).strip().replace(" ", "_")
        nombre = input(f"\n  Nombre [{suggested}]: ").strip()
        if not nombre:
            nombre = suggested
        
        # 5. Descargar
        _section("PASO 4 · Descargando y desencriptando")
        success = download_video(data["m3u8_url"], keys, save_path, nombre)
        if success:
            descargas.append(nombre)
            print(f"\n  ╔══════════════════════════════════════╗")
            print(f"  ║  ✅  '{nombre}.mkv' descargado!      ║")
            print(f"  ╚══════════════════════════════════════╝")
        else:
            print(f"\n  ✖ Problema con la descarga de '{nombre}'.")
        
        continuar = input("\n  ¿Otro vídeo? (S/n): ").strip().lower()
        if continuar == "n":
            break
    
    # Resumen final
    print(f"\n  ╔══════════════════════════════════════════════════════╗")
    print(f"  ║  Sesión finalizada · {len(descargas)} vídeo(s) descargado(s)       ║")
    print(f"  ╚══════════════════════════════════════════════════════╝\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n  ✖ Cancelado.")
