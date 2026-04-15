import os
import re
import sys
import time
import subprocess
import math
import xml.etree.ElementTree as ET
from pathlib import Path

# --- CONFIGURACIÓN ---
BASE_SAVE_PATH = r"C:\Users\marco\OneDrive - MSFT\UPC\VIDEOS_ASES"
PRESET_PERIODS = ["Parcial", "Intensivo Parcial", "Final", "Intensivo Final"]
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(SCRIPT_DIR)
FFMPEG = os.path.join(PARENT_DIR, "ffmpeg.exe")

# Detectar Chrome para renderizado de slides SVG
def _find_chrome():
    candidates = [
        r'C:\Program Files\Google\Chrome\Application\chrome.exe',
        r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
        os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Google', 'Chrome', 'Application', 'chrome.exe'),
        r'C:\Program Files\Microsoft\Edge\Application\msedge.exe',  # fallback Edge
    ]
    return next((p for p in candidates if os.path.exists(p)), None)

CHROME = _find_chrome()

# --- INSTALACIÓN DE DEPENDENCIAS ---
def install_if_missing(package_name, import_name=None):
    import_name = import_name or package_name
    try:
        __import__(import_name)
    except ImportError:
        print(f"  Instalando dependencia: {package_name}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package_name],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

install_if_missing("DrissionPage")
install_if_missing("requests")
install_if_missing("pycairo", "cairo")
install_if_missing("Pillow", "PIL")

from DrissionPage import ChromiumPage, ChromiumOptions
import requests
import cairo
from PIL import Image

# ==========================================
# SECCIÓN 1: GESTIÓN DE DIRECTORIOS
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
        header = rel if rel != "." else "(raíz)"
        print(f"\n  📁 {header}")
        
        subdirs = _list_subdirs(current_path)
        n_files = _count_files(current_path)
        
        if n_files > 0:
            print(f"     ({n_files} archivos en esta carpeta)")
        
        for i, d in enumerate(subdirs, 1):
            sub_path = os.path.join(current_path, d)
            sub_count = len(_list_subdirs(sub_path))
            file_count = _count_files(sub_path)
            info = []
            if sub_count > 0:
                info.append(f"{sub_count} subcarpetas")
            if file_count > 0:
                info.append(f"{file_count} archivos")
            extra = f"  ({', '.join(info)})" if info else ""
            print(f"  {i}. {d}{extra}")
        
        idx = len(subdirs)
        n_select = idx + 1
        n_new    = idx + 2
        n_rename = idx + 3
        n_delete = idx + 4
        n_back   = idx + 5
        
        print(f"  {n_select}. ✅ GUARDAR AQUÍ")
        print(f"  {n_new}. ➕ Nueva subcarpeta")
        if subdirs:
            print(f"  {n_rename}. ✏️  Renombrar carpeta")
            print(f"  {n_delete}. 🗑️  Eliminar carpeta")
        if current_path != BASE_SAVE_PATH:
            print(f"  {n_back}. ⬅  Volver atrás")
        
        choice = input("> ").strip()
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
                    suggestion = f" [Semana {next_week}]"
                name = input(f"  Nombre de la nueva carpeta{suggestion}:\n  > ").strip()
                if not name and suggestion:
                    name = f"Semana {len(existing_weeks) + 1}"
                if name:
                    new_path = os.path.join(current_path, name)
                    os.makedirs(new_path, exist_ok=True)
                    print(f"  [+] Creada: {name}")
                    current_path = new_path
                continue
            elif n == n_rename and subdirs:
                print("  ¿Qué carpeta quieres renombrar?")
                for i, d in enumerate(subdirs, 1):
                    print(f"    {i}. {d}")
                sel = input("  > ").strip()
                if sel.isdigit() and 1 <= int(sel) <= len(subdirs):
                    old_name = subdirs[int(sel) - 1]
                    new_name = input(f"  Nuevo nombre para '{old_name}':\n  > ").strip()
                    if new_name and new_name != old_name:
                        old_p = os.path.join(current_path, old_name)
                        new_p = os.path.join(current_path, new_name)
                        try:
                            os.rename(old_p, new_p)
                            print(f"  [+] '{old_name}' → '{new_name}'")
                        except Exception as e:
                            print(f"  [!] Error: {e}")
                continue
            elif n == n_delete and subdirs:
                print("  ¿Qué carpeta quieres eliminar?")
                for i, d in enumerate(subdirs, 1):
                    sub_path = os.path.join(current_path, d)
                    total = _count_files(sub_path) + len(_list_subdirs(sub_path))
                    warn = f"  ⚠️ {total} elementos dentro" if total > 0 else "  (vacía)"
                    print(f"    {i}. {d}{warn}")
                sel = input("  > ").strip()
                if sel.isdigit() and 1 <= int(sel) <= len(subdirs):
                    target_name = subdirs[int(sel) - 1]
                    target_path = os.path.join(current_path, target_name)
                    confirm = input(f"  ¿Seguro que quieres eliminar '{target_name}'? (s/N): ").strip().lower()
                    if confirm == "s":
                        import shutil
                        try:
                            shutil.rmtree(target_path)
                            print(f"  [+] '{target_name}' eliminada")
                        except Exception as e:
                            print(f"  [!] Error: {e}")
                continue
            elif n == n_back and current_path != BASE_SAVE_PATH:
                current_path = os.path.dirname(current_path)
                continue
        print("  [!] Opción no válida")

def manage_save_directory():
    print(f"\n{'='*50}")
    print(f"  📂 DIRECTORIO DE GUARDADO")
    print(f"  Base: {BASE_SAVE_PATH}")
    print(f"{'='*50}")
    if not os.path.exists(BASE_SAVE_PATH):
        os.makedirs(BASE_SAVE_PATH)
    return _show_folder_menu(BASE_SAVE_PATH)

# ==========================================
# SECCIÓN 2: EXTRACCIÓN DEL BBB SESSION ID
# ==========================================

CHROME_USER_DATA = os.path.join(os.environ.get('LOCALAPPDATA', ''),
                                'Google', 'Chrome', 'User Data')

def create_browser():
    """Crea un ChromiumPage usando el perfil de Chrome instalado (con sesiones guardadas)."""
    opts = ChromiumOptions()
    if os.path.exists(CHROME_USER_DATA):
        opts.set_user_data_path(CHROME_USER_DATA)
        print(f"  [+] Usando perfil de Chrome: {CHROME_USER_DATA}")
    else:
        print(f"  [!] Perfil de Chrome no encontrado en: {CHROME_USER_DATA}")
        print("      Abriendo Chrome sin sesión guardada.")
    opts.auto_port()
    return ChromiumPage(addr_or_opts=opts)

def extract_session_id_from_url(url):
    match = re.search(r'([a-f0-9]{40}-\d+)', url)
    return match.group(1) if match else None

def extract_session_id_from_page(page, url):
    print(f"  Navegando a: {url}")
    page.get(url)
    time.sleep(4)

    # Buscar botón de play y hacer clic si existe
    try:
        play_btn = page.ele('css:.bbb-icon-play', timeout=3)
        if play_btn:
            play_btn.click()
            time.sleep(2)
    except:
        pass

    # Intentar extraer del HTML
    try:
        html = page.html
        session_id = extract_session_id_from_url(html)
        if session_id:
            print(f"  [+] Session ID encontrado.")
            return session_id
    except:
        pass

    # Intentar desde recursos de red
    try:
        resources_json = page.run_js(
            'return JSON.stringify(performance.getEntriesByType("resource").map(e => e.name))'
        )
        session_id = extract_session_id_from_url(str(resources_json))
        if session_id:
            print(f"  [+] Session ID encontrado en network.")
            return session_id
    except:
        pass

    return None

def get_session_id(page):
    print("\n=== PASO 2: Obtener Session ID de BBB ===")
    print("Opciones de entrada:")
    print("  - URL de la grabacion en la academia (asesacademia.com/...)")
    print("  - Session ID directamente (40 hex chars-timestamp)")

    url_or_id = input("\nPega la URL o ID (Enter para salir):\n> ").strip()
    if not url_or_id:
        return None, page

    # Session ID directo
    if re.match(r'^[a-f0-9]{40}-\d+$', url_or_id):
        print(f"  [+] Session ID directo detectado.")
        return url_or_id, page

    # URL con session ID embebida
    session_id = extract_session_id_from_url(url_or_id)
    if session_id:
        print(f"  [+] Session ID extraído de la URL.")
        return session_id, page

    # URL de la academia -> navegar y extraer (abrimos navegador aquí si hace falta)
    if 'asesacademia.com' in url_or_id:
        if page is None:
            print("  Iniciando Chrome con tu perfil...")
            page = create_browser()
        session_id = extract_session_id_from_page(page, url_or_id)
        if session_id:
            return session_id, page

    print("[!] No se pudo extraer el session ID.")
    return None, page

# ==========================================
# SECCIÓN 3: DESCARGA DE ARCHIVOS BBB
# ==========================================

def get_bbb_base_url(session_id):
    return f"https://www.asesacademia.com/bbb-files/{session_id}/"

def download_file(url, dest_path, desc="archivo"):
    try:
        resp = requests.get(url, stream=True, timeout=120)
        resp.raise_for_status()
        total = int(resp.headers.get('content-length', 0))
        downloaded = 0
        with open(dest_path, 'wb') as f:
            for chunk in resp.iter_content(chunk_size=65536):
                f.write(chunk)
                downloaded += len(chunk)
                if total > 0:
                    pct = (downloaded / total) * 100
                    mb = downloaded / (1024 * 1024)
                    print(f"\r  Descargando {desc}: {mb:.1f} MB ({pct:.0f}%)", end="", flush=True)
        print(f"\r  [+] {desc}: {os.path.basename(dest_path)} ({downloaded / (1024*1024):.1f} MB)          ")
        return True
    except Exception as e:
        print(f"\n  [!] Error descargando {desc}: {e}")
        return False

def download_bbb_files(session_id, work_dir):
    base_url = get_bbb_base_url(session_id)
    print(f"\n=== PASO 3: Descargando archivos BBB ===")
    print(f"  Base URL: {base_url}")
    os.makedirs(work_dir, exist_ok=True)

    metadata_path = os.path.join(work_dir, "metadata.xml")
    download_file(base_url + "metadata.xml", metadata_path, "metadata.xml")

    shapes_path = os.path.join(work_dir, "shapes.svg")
    download_file(base_url + "shapes.svg", shapes_path, "shapes.svg")

    video_path = os.path.join(work_dir, "webcams.mp4")
    download_file(base_url + "video/webcams.mp4", video_path, "webcams.mp4")

    # Parsear shapes.svg para obtener URLs de las slides
    tree = ET.parse(shapes_path)
    root = tree.getroot()
    slide_hrefs = set()
    for elem in root.iter():
        tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
        if tag == 'image':
            href = elem.get('{http://www.w3.org/1999/xlink}href', '')
            if href and 'slide' in href.lower():
                slide_hrefs.add(href)

    print(f"\n  Encontradas {len(slide_hrefs)} diapositivas únicas.")
    for href in sorted(slide_hrefs):
        slide_url = base_url + href
        slide_local = os.path.join(work_dir, href.replace('/', os.sep))
        os.makedirs(os.path.dirname(slide_local), exist_ok=True)
        download_file(slide_url, slide_local, os.path.basename(href))

    return {
        'metadata': metadata_path,
        'shapes': shapes_path,
        'video': video_path,
        'work_dir': work_dir,
        'base_url': base_url,
    }

# ==========================================
# SECCIÓN 4: PARSEO SVG Y TIMELINE
# ==========================================

def parse_shapes(shapes_path):
    tree = ET.parse(shapes_path)
    root = tree.getroot()
    ET.register_namespace('', 'http://www.w3.org/2000/svg')
    ET.register_namespace('xlink', 'http://www.w3.org/1999/xlink')

    slides = []
    annotations = {}

    for elem in root:
        tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag

        if tag == 'image':
            cls = elem.get('class', '')
            if 'slide' in cls:
                href = elem.get('{http://www.w3.org/1999/xlink}href', '')
                slides.append({
                    'id': elem.get('id'),
                    'href': href,
                    'in': float(elem.get('in', 0)),
                    'out': float(elem.get('out', 0)),
                    'width': int(elem.get('width', 1600)),
                    'height': int(elem.get('height', 900)),
                })

        elif tag == 'g':
            cls = elem.get('class', '')
            if cls == 'canvas':
                image_id = elem.get('image', '')
                shapes = []
                for shape_elem in elem:
                    shape_tag = shape_elem.tag.split('}')[-1] if '}' in shape_elem.tag else shape_elem.tag
                    if shape_tag == 'g' and 'shape' in shape_elem.get('class', ''):
                        timestamp = float(shape_elem.get('timestamp', 0))
                        undo = float(shape_elem.get('undo', -1))
                        style_str = shape_elem.get('style', '')

                        # Parsear estilo SVG
                        style = parse_svg_style(style_str)

                        # Extraer paths y circles
                        paths = []
                        for child in shape_elem:
                            child_tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                            if child_tag == 'path':
                                paths.append({'type': 'path', 'd': child.get('d', '')})
                            elif child_tag == 'circle':
                                paths.append({
                                    'type': 'circle',
                                    'cx': float(child.get('cx', 0)),
                                    'cy': float(child.get('cy', 0)),
                                    'r': float(child.get('r', 1)),
                                })
                            elif child_tag == 'line':
                                paths.append({
                                    'type': 'line',
                                    'x1': float(child.get('x1', 0)),
                                    'y1': float(child.get('y1', 0)),
                                    'x2': float(child.get('x2', 0)),
                                    'y2': float(child.get('y2', 0)),
                                })
                            elif child_tag == 'rect':
                                paths.append({
                                    'type': 'rect',
                                    'x': float(child.get('x', 0)),
                                    'y': float(child.get('y', 0)),
                                    'width': float(child.get('width', 0)),
                                    'height': float(child.get('height', 0)),
                                })

                        shapes.append({
                            'id': shape_elem.get('id', ''),
                            'timestamp': timestamp,
                            'undo': undo,
                            'style': style,
                            'paths': paths,
                        })
                annotations[image_id] = shapes

    slides.sort(key=lambda s: s['in'])
    return slides, annotations

def parse_svg_style(style_str):
    """Parsea una cadena de estilo SVG en un diccionario."""
    style = {}
    for part in style_str.split(';'):
        part = part.strip()
        if ':' in part:
            key, value = part.split(':', 1)
            style[key.strip()] = value.strip()
    return style

def parse_color(color_str):
    """Convierte un color CSS/SVG a tupla (r, g, b) normalizada 0-1."""
    if not color_str or color_str == 'none':
        return None
    color_str = color_str.strip()
    if color_str.startswith('#'):
        hex_color = color_str[1:]
        if len(hex_color) == 3:
            hex_color = ''.join(c * 2 for c in hex_color)
        r = int(hex_color[0:2], 16) / 255.0
        g = int(hex_color[2:4], 16) / 255.0
        b = int(hex_color[4:6], 16) / 255.0
        return (r, g, b)
    # Colores con nombre básicos
    named = {
        'red': (1, 0, 0), 'green': (0, 0.5, 0), 'blue': (0, 0, 1),
        'black': (0, 0, 0), 'white': (1, 1, 1), 'yellow': (1, 1, 0),
        'orange': (1, 0.65, 0), 'purple': (0.5, 0, 0.5),
    }
    return named.get(color_str.lower(), (0, 0, 0))

def parse_svg_path_d(d):
    """Parsea un atributo 'd' de un SVG path en una lista de comandos."""
    if not d:
        return []
    # Tokenizar: separar por comandos (letras) y números
    tokens = re.findall(r'[MmLlHhVvCcSsQqTtAaZz]|[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?', d)
    commands = []
    i = 0
    current_cmd = None

    while i < len(tokens):
        token = tokens[i]
        if token.isalpha():
            current_cmd = token
            i += 1
        elif current_cmd is None:
            i += 1
            continue

        cmd = current_cmd

        if cmd in ('M', 'm'):
            if i + 1 < len(tokens):
                try:
                    x, y = float(tokens[i]), float(tokens[i + 1])
                    commands.append(('M' if cmd == 'M' else 'm', x, y))
                    i += 2
                    # Subsequent coordinates after M are implicit L
                    if cmd == 'M':
                        current_cmd = 'L'
                    else:
                        current_cmd = 'l'
                except (ValueError, IndexError):
                    i += 1
            else:
                i += 1

        elif cmd in ('L', 'l'):
            if i + 1 < len(tokens):
                try:
                    x, y = float(tokens[i]), float(tokens[i + 1])
                    commands.append((cmd, x, y))
                    i += 2
                except (ValueError, IndexError):
                    i += 1
            else:
                i += 1

        elif cmd == 'H':
            if i < len(tokens):
                try:
                    commands.append(('H', float(tokens[i])))
                    i += 1
                except ValueError:
                    i += 1
            else:
                i += 1

        elif cmd == 'h':
            if i < len(tokens):
                try:
                    commands.append(('h', float(tokens[i])))
                    i += 1
                except ValueError:
                    i += 1
            else:
                i += 1

        elif cmd == 'V':
            if i < len(tokens):
                try:
                    commands.append(('V', float(tokens[i])))
                    i += 1
                except ValueError:
                    i += 1
            else:
                i += 1

        elif cmd == 'v':
            if i < len(tokens):
                try:
                    commands.append(('v', float(tokens[i])))
                    i += 1
                except ValueError:
                    i += 1
            else:
                i += 1

        elif cmd in ('C', 'c'):
            if i + 5 < len(tokens):
                try:
                    vals = [float(tokens[i + j]) for j in range(6)]
                    commands.append((cmd, *vals))
                    i += 6
                except (ValueError, IndexError):
                    i += 1
            else:
                i += 1

        elif cmd in ('S', 's'):
            if i + 3 < len(tokens):
                try:
                    vals = [float(tokens[i + j]) for j in range(4)]
                    commands.append((cmd, *vals))
                    i += 4
                except (ValueError, IndexError):
                    i += 1
            else:
                i += 1

        elif cmd in ('Q', 'q'):
            if i + 3 < len(tokens):
                try:
                    vals = [float(tokens[i + j]) for j in range(4)]
                    commands.append((cmd, *vals))
                    i += 4
                except (ValueError, IndexError):
                    i += 1
            else:
                i += 1

        elif cmd in ('T', 't'):
            if i + 1 < len(tokens):
                try:
                    x, y = float(tokens[i]), float(tokens[i + 1])
                    commands.append((cmd, x, y))
                    i += 2
                except (ValueError, IndexError):
                    i += 1
            else:
                i += 1

        elif cmd in ('A', 'a'):
            if i + 6 < len(tokens):
                try:
                    vals = [float(tokens[i + j]) for j in range(7)]
                    commands.append((cmd, *vals))
                    i += 7
                except (ValueError, IndexError):
                    i += 1
            else:
                i += 1

        elif cmd in ('Z', 'z'):
            commands.append(('Z',))
            # No consume tokens adicionales

        else:
            i += 1

    return commands

def draw_svg_path_on_cairo(ctx, d_string):
    """Dibuja un path SVG en un contexto cairo."""
    commands = parse_svg_path_d(d_string)
    cx, cy = 0.0, 0.0  # Posición actual
    sx, sy = 0.0, 0.0  # Posición inicio del subpath
    last_cp = None  # Último punto de control (para S/s)
    last_qcp = None  # Último punto de control cuadrático (para T/t)

    for cmd_data in commands:
        cmd = cmd_data[0]

        if cmd == 'M':
            cx, cy = cmd_data[1], cmd_data[2]
            ctx.move_to(cx, cy)
            sx, sy = cx, cy
            last_cp = None
            last_qcp = None

        elif cmd == 'm':
            cx += cmd_data[1]
            cy += cmd_data[2]
            ctx.move_to(cx, cy)
            sx, sy = cx, cy
            last_cp = None
            last_qcp = None

        elif cmd == 'L':
            cx, cy = cmd_data[1], cmd_data[2]
            ctx.line_to(cx, cy)
            last_cp = None
            last_qcp = None

        elif cmd == 'l':
            cx += cmd_data[1]
            cy += cmd_data[2]
            ctx.line_to(cx, cy)
            last_cp = None
            last_qcp = None

        elif cmd == 'H':
            cx = cmd_data[1]
            ctx.line_to(cx, cy)
            last_cp = None
            last_qcp = None

        elif cmd == 'h':
            cx += cmd_data[1]
            ctx.line_to(cx, cy)
            last_cp = None
            last_qcp = None

        elif cmd == 'V':
            cy = cmd_data[1]
            ctx.line_to(cx, cy)
            last_cp = None
            last_qcp = None

        elif cmd == 'v':
            cy += cmd_data[1]
            ctx.line_to(cx, cy)
            last_cp = None
            last_qcp = None

        elif cmd == 'C':
            x1, y1, x2, y2, x, y = cmd_data[1:7]
            ctx.curve_to(x1, y1, x2, y2, x, y)
            last_cp = (x2, y2)
            cx, cy = x, y
            last_qcp = None

        elif cmd == 'c':
            x1, y1, x2, y2, x, y = cmd_data[1:7]
            ctx.curve_to(cx + x1, cy + y1, cx + x2, cy + y2, cx + x, cy + y)
            last_cp = (cx + x2, cy + y2)
            cx += x
            cy += y
            last_qcp = None

        elif cmd == 'S':
            x2, y2, x, y = cmd_data[1:5]
            if last_cp:
                x1 = 2 * cx - last_cp[0]
                y1 = 2 * cy - last_cp[1]
            else:
                x1, y1 = cx, cy
            ctx.curve_to(x1, y1, x2, y2, x, y)
            last_cp = (x2, y2)
            cx, cy = x, y
            last_qcp = None

        elif cmd == 's':
            x2, y2, x, y = cmd_data[1:5]
            if last_cp:
                x1 = 2 * cx - last_cp[0]
                y1 = 2 * cy - last_cp[1]
            else:
                x1, y1 = cx, cy
            ctx.curve_to(x1, y1, cx + x2, cy + y2, cx + x, cy + y)
            last_cp = (cx + x2, cy + y2)
            cx += x
            cy += y
            last_qcp = None

        elif cmd == 'Q':
            qx, qy, x, y = cmd_data[1:5]
            # Convertir curva cuadrática a cúbica para cairo
            cp1x = cx + 2.0 / 3.0 * (qx - cx)
            cp1y = cy + 2.0 / 3.0 * (qy - cy)
            cp2x = x + 2.0 / 3.0 * (qx - x)
            cp2y = y + 2.0 / 3.0 * (qy - y)
            ctx.curve_to(cp1x, cp1y, cp2x, cp2y, x, y)
            last_qcp = (qx, qy)
            cx, cy = x, y
            last_cp = None

        elif cmd == 'q':
            qx, qy, x, y = cmd_data[1:5]
            abs_qx, abs_qy = cx + qx, cy + qy
            abs_x, abs_y = cx + x, cy + y
            cp1x = cx + 2.0 / 3.0 * (abs_qx - cx)
            cp1y = cy + 2.0 / 3.0 * (abs_qy - cy)
            cp2x = abs_x + 2.0 / 3.0 * (abs_qx - abs_x)
            cp2y = abs_y + 2.0 / 3.0 * (abs_qy - abs_y)
            ctx.curve_to(cp1x, cp1y, cp2x, cp2y, abs_x, abs_y)
            last_qcp = (abs_qx, abs_qy)
            cx, cy = abs_x, abs_y
            last_cp = None

        elif cmd == 'Z' or cmd == 'z':
            ctx.close_path()
            cx, cy = sx, sy
            last_cp = None
            last_qcp = None

def build_timeline(slides, annotations):
    events = set()
    for slide in slides:
        events.add(slide['in'])
        events.add(slide['out'])
    for image_id, shapes in annotations.items():
        for shape in shapes:
            events.add(shape['timestamp'])
            if shape['undo'] > 0:
                events.add(shape['undo'])
    return sorted(events)

def get_state_at_time(t, slides, annotations):
    current_slide = None
    for slide in slides:
        if slide['in'] <= t < slide['out']:
            current_slide = slide
            break
    if not current_slide:
        return None, []
    visible_shapes = []
    image_id = current_slide['id']
    if image_id in annotations:
        for shape in annotations[image_id]:
            if shape['timestamp'] <= t:
                if shape['undo'] < 0 or shape['undo'] > t:
                    visible_shapes.append(shape)
    return current_slide, visible_shapes

# ==========================================
# SECCIÓN 5: RENDERIZADO CON PYCAIRO
# ==========================================

_svg_png_cache = {}  # cache: svg_path -> png_path

def svg_to_png(svg_path, width, height):
    """Extrae la imagen embebida del SVG de BBB o usa Chrome headless como fallback.
    
    Los SVGs de BBB contienen MÚLTIPLES imágenes base64:
    - Máscaras en modo L (grayscale) - totalmente blancas, descartarlas
    - Imágenes RGB reales (la diapositiva) - la que queremos
    Seleccionamos la imagen RGB más grande por área de píxeles.
    """
    cache_key = (svg_path, width, height)
    if cache_key in _svg_png_cache:
        return _svg_png_cache[cache_key]

    png_path = svg_path + f'__{width}x{height}.png'

    if not os.path.exists(png_path):
        converted = False

        # Método 1: Extraer la mejor imagen base64 del SVG
        try:
            with open(svg_path, 'r', encoding='utf-8') as f:
                svg_content = f.read()

            import base64, io

            # Encontrar TODAS las imágenes base64 embebidas
            all_matches = re.finditer(
                r'(?:xlink:href|href)="data:image/(\w+);base64,([A-Za-z0-9+/=\s]+)"',
                svg_content
            )

            best_img = None
            best_area = 0

            for m in all_matches:
                img_type = m.group(1)
                b64_data = m.group(2).replace('\n', '').replace(' ', '')
                try:
                    img_bytes = base64.b64decode(b64_data)
                    img = Image.open(io.BytesIO(img_bytes))
                    
                    # Descartar máscaras (grayscale mode L) - son las que salen blancas
                    if img.mode == 'L':
                        continue
                    
                    # Calcular área de píxeles
                    area = img.width * img.height
                    
                    # Verificar que tiene contenido real (no todo blanco)
                    img_rgb = img.convert('RGB')
                    # Muestrear varios puntos para ver si no es todo blanco
                    sample_points = [
                        (img.width // 2, img.height // 2),
                        (img.width // 4, img.height // 4),
                        (3 * img.width // 4, 3 * img.height // 4),
                    ]
                    has_content = any(
                        img_rgb.getpixel(p) != (255, 255, 255)
                        for p in sample_points
                        if 0 <= p[0] < img.width and 0 <= p[1] < img.height
                    )
                    
                    # Preferir imágenes con contenido, pero aceptar blancas si no hay nada mejor
                    score = area * (10 if has_content else 1)
                    
                    if score > best_area:
                        best_area = score
                        best_img = img
                except Exception:
                    continue

            if best_img:
                best_img = best_img.convert('RGBA')
                best_img = best_img.resize((width, height), Image.LANCZOS)
                best_img.save(png_path, 'PNG')
                converted = True

        except Exception:
            pass

        # Método 2: Chrome headless (fallback para SVGs complejos con <use> refs)
        if not converted and CHROME:
            try:
                svg_url = 'file:///' + svg_path.replace(os.sep, '/')
                # Wrapper HTML con object-fit para escalar correctamente
                html_content = f"""<!DOCTYPE html>
<html><head><style>
* {{ margin:0; padding:0; }}
body {{ width:{width}px; height:{height}px; overflow:hidden; background:#fff; }}
img {{ width:{width}px; height:{height}px; object-fit:contain; display:block; }}
</style></head>
<body><img src="{svg_url}"></body></html>"""
                html_path = svg_path + f'__{width}x{height}.html'
                with open(html_path, 'w', encoding='utf-8') as f:
                    f.write(html_content)

                cmd = [
                    CHROME, '--headless=new', '--disable-gpu', '--no-sandbox',
                    '--disable-extensions', '--hide-scrollbars',
                    '--force-device-scale-factor=1',
                    f'--window-size={width},{height}',
                    f'--screenshot={png_path}',
                    'file:///' + html_path.replace(os.sep, '/')
                ]
                subprocess.run(cmd, capture_output=True, timeout=20)
            except Exception as e:
                print(f'\n  [!] Error Chrome headless: {e}')

    if os.path.exists(png_path) and os.path.getsize(png_path) > 500:
        _svg_png_cache[cache_key] = png_path
        return png_path
    return None




def render_frame(slide_image_path, visible_annotations, output_path, width=1600, height=900):
    """Renderiza un frame: slide PNG + anotaciones → PNG usando pycairo."""
    # Crear surface de cairo
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
    ctx = cairo.Context(surface)

    # 1. Cargar la slide de fondo
    if os.path.exists(slide_image_path):
        try:
            # Obtener el PNG a cargar (convertir SVG si es necesario)
            if slide_image_path.lower().endswith('.svg'):
                png_path = svg_to_png(slide_image_path, width, height)
                if not png_path or not os.path.exists(png_path):
                    raise FileNotFoundError('No se pudo convertir SVG a PNG')
                load_path = png_path
            else:
                load_path = slide_image_path

            # Cargar con PIL para poder redimensionar
            pil_img = Image.open(load_path).convert('RGB')
            if pil_img.size != (width, height):
                pil_img = pil_img.resize((width, height), Image.LANCZOS)

            # Convertir RGB -> Cairo ARGB32 (formato: B G R 0xFF en memoria little-endian)
            r, g, b = pil_img.split()
            alpha = Image.new('L', pil_img.size, 255)
            # Cairo ARGB32 little-endian = bytes en orden B, G, R, A
            bgra = Image.merge('RGBA', (b, g, r, alpha))
            pixel_data = bytearray(bgra.tobytes())
            img_surface = cairo.ImageSurface.create_for_data(
                pixel_data, cairo.FORMAT_ARGB32, width, height, width * 4
            )
            ctx.set_source_surface(img_surface, 0, 0)
            ctx.paint()
        except Exception as e:
            print(f"\n  [!] Error cargando slide: {e}")
            ctx.set_source_rgb(1, 1, 1)  # fondo blanco si falla
            ctx.paint()
    else:
        ctx.set_source_rgb(1, 1, 1)  # fondo blanco si no existe
        ctx.paint()


    # 2. Dibujar anotaciones encima
    for ann in visible_annotations:
        style = ann['style']
        stroke_color = parse_color(style.get('stroke', 'none'))
        fill_color = parse_color(style.get('fill', 'none'))
        line_width = float(style.get('stroke-width', '2'))
        line_cap_str = style.get('stroke-linecap', 'round')
        line_join_str = style.get('stroke-linejoin', 'round')

        # Configurar line cap
        cap_map = {
            'round': cairo.LINE_CAP_ROUND,
            'square': cairo.LINE_CAP_SQUARE,
            'butt': cairo.LINE_CAP_BUTT,
        }
        join_map = {
            'round': cairo.LINE_JOIN_ROUND,
            'miter': cairo.LINE_JOIN_MITER,
            'bevel': cairo.LINE_JOIN_BEVEL,
        }
        ctx.set_line_cap(cap_map.get(line_cap_str, cairo.LINE_CAP_ROUND))
        ctx.set_line_join(join_map.get(line_join_str, cairo.LINE_JOIN_ROUND))
        ctx.set_line_width(line_width)

        for path_data in ann['paths']:
            if path_data['type'] == 'path':
                ctx.new_path()
                draw_svg_path_on_cairo(ctx, path_data['d'])

                if fill_color and fill_color != 'none':
                    ctx.set_source_rgb(*fill_color)
                    if stroke_color:
                        ctx.fill_preserve()
                    else:
                        ctx.fill()

                if stroke_color:
                    ctx.set_source_rgb(*stroke_color)
                    ctx.stroke()

            elif path_data['type'] == 'circle':
                ctx.new_path()
                ctx.arc(path_data['cx'], path_data['cy'], path_data['r'], 0, 2 * math.pi)
                if fill_color:
                    ctx.set_source_rgb(*fill_color)
                    if stroke_color:
                        ctx.fill_preserve()
                    else:
                        ctx.fill()
                if stroke_color:
                    ctx.set_source_rgb(*stroke_color)
                    ctx.stroke()

            elif path_data['type'] == 'line':
                ctx.new_path()
                ctx.move_to(path_data['x1'], path_data['y1'])
                ctx.line_to(path_data['x2'], path_data['y2'])
                if stroke_color:
                    ctx.set_source_rgb(*stroke_color)
                    ctx.stroke()

            elif path_data['type'] == 'rect':
                ctx.new_path()
                ctx.rectangle(path_data['x'], path_data['y'],
                              path_data['width'], path_data['height'])
                if fill_color:
                    ctx.set_source_rgb(*fill_color)
                    if stroke_color:
                        ctx.fill_preserve()
                    else:
                        ctx.fill()
                if stroke_color:
                    ctx.set_source_rgb(*stroke_color)
                    ctx.stroke()

    # 3. Guardar como PNG
    surface.write_to_png(output_path)

# ==========================================
# SECCIÓN 6: GENERACIÓN DEL VÍDEO MKV
# ==========================================

def get_audio_duration(ffmpeg_path, video_path):
    """Obtiene la duración del audio del webcam en segundos."""
    result = subprocess.run(
        [ffmpeg_path, '-i', video_path, '-hide_banner'],
        capture_output=True, text=True
    )
    # Buscar "Duration: HH:MM:SS.ms"
    match = re.search(r'Duration:\s*(\d+):(\d+):(\d+)\.(\d+)', result.stderr)
    if match:
        h, m, s, ms = match.groups()
        return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 100
    return 0

def generate_video(files_info, output_path, class_name):
    print(f"\n=== PASO 4: Generando vídeo compuesto ===")

    shapes_path = files_info['shapes']
    video_path = files_info['video']
    work_dir = files_info['work_dir']

    # 1. Obtener duración real del audio (para sincronizar)
    audio_duration = get_audio_duration(FFMPEG, video_path)
    print(f"  Duración del audio (webcam): {audio_duration:.1f}s ({int(audio_duration//60)}:{int(audio_duration%60):02d})")

    # 2. Parsear shapes.svg
    print("  Parseando shapes.svg...")
    slides, annotations = parse_shapes(shapes_path)
    print(f"  -> {len(slides)} slides encontradas")
    total_annotations = sum(len(v) for v in annotations.values())
    print(f"  -> {total_annotations} anotaciones encontradas")

    if not slides:
        print("  [!] No se encontraron slides. Abortando.")
        return False

    # 3. Construir timeline (limitada a la duración del audio)
    timeline = build_timeline(slides, annotations)
    min_t = slides[0]['in']
    max_t = slides[-1]['out']
    # Limitar al audio si es más corto
    effective_max = min(max_t, audio_duration) if audio_duration > 0 else max_t
    timeline = [t for t in timeline if min_t <= t <= effective_max]
    print(f"  -> Timeline: {len(timeline)} puntos ({min_t:.1f}s - {effective_max:.1f}s)")

    # 4. Generar frames únicos
    frames_dir = os.path.join(work_dir, "frames")
    # Limpiar frames anteriores para evitar reutilizar frames corruptos de runs previos
    import shutil
    shutil.rmtree(frames_dir, ignore_errors=True)
    os.makedirs(frames_dir, exist_ok=True)

    frames_data = []  # [(frame_path, duration_seconds)]
    prev_slide_id = None
    prev_ann_ids = set()
    frame_count = 0

    print("  Generando frames...")
    t_start = time.time()

    for i, t in enumerate(timeline):
        slide, visible_anns = get_state_at_time(t, slides, annotations)
        if slide is None:
            continue

        # Duración hasta el siguiente evento
        if i + 1 < len(timeline):
            duration = timeline[i + 1] - t
        else:
            duration = effective_max - t

        if duration <= 0:
            continue

        # Verificar si el estado visual cambió
        current_slide_id = slide['id']
        current_ann_ids = frozenset(a['id'] for a in visible_anns)

        if current_slide_id == prev_slide_id and current_ann_ids == prev_ann_ids:
            if frames_data:
                old_path, old_dur = frames_data[-1]
                frames_data[-1] = (old_path, old_dur + duration)
            continue

        prev_slide_id = current_slide_id
        prev_ann_ids = current_ann_ids

        # Renderizar frame
        slide_href = slide['href']
        slide_image_path = os.path.join(work_dir, slide_href.replace('/', os.sep))

        frame_path = os.path.join(frames_dir, f"frame_{frame_count:06d}.png")
        render_frame(slide_image_path, visible_anns, frame_path,
                     slide['width'], slide['height'])
        frames_data.append((frame_path, duration))
        frame_count += 1

        elapsed = time.time() - t_start
        if frame_count % 5 == 0 or i == len(timeline) - 1:
            print(f"\r  Frames: {frame_count} | Timeline: {t:.0f}s/{effective_max:.0f}s | "
                  f"Tiempo: {elapsed:.0f}s", end="", flush=True)

    elapsed = time.time() - t_start
    print(f"\n  [+] {frame_count} frames únicos en {elapsed:.1f}s")

    if not frames_data:
        print("  [!] No se generaron frames. Abortando.")
        return False

    # 5. Crear secuencia de frames a framerate fijo
    TARGET_FPS = 2
    seq_dir = os.path.join(work_dir, "seq_frames")
    os.makedirs(seq_dir, exist_ok=True)

    print(f"  Creando secuencia a {TARGET_FPS} fps...")
    seq_idx = 0
    for frame_path, duration in frames_data:
        num_copies = max(1, round(duration * TARGET_FPS))
        for _ in range(num_copies):
            seq_path = os.path.join(seq_dir, f"f_{seq_idx:06d}.png")
            try:
                os.link(frame_path, seq_path)
            except OSError:
                import shutil
                shutil.copy2(frame_path, seq_path)
            seq_idx += 1

    total_seq_dur = seq_idx / TARGET_FPS
    print(f"  [+] {seq_idx} frames en secuencia ({total_seq_dur:.0f}s)")

    # 6. PASADA ÚNICA: frames + audio → MKV directo
    print("  Generando MKV final (pasada única)...")

    # Verificar si webcams.mp4 tiene audio
    probe_result = subprocess.run(
        [FFMPEG, '-i', video_path, '-hide_banner'],
        capture_output=True, text=True
    )
    has_audio = 'Audio:' in probe_result.stderr

    if has_audio:
        cmd = [
            FFMPEG, '-y',
            '-framerate', str(TARGET_FPS),
            '-i', os.path.join(seq_dir, 'f_%06d.png'),
            '-i', video_path,
            '-map', '0:v:0',
            '-map', '1:a:0',
            '-vf', 'scale=1920:1080:force_original_aspect_ratio=decrease,'
                   'pad=1920:1080:(ow-iw)/2:(oh-ih)/2:black',
            '-r', '25',
            '-pix_fmt', 'yuv420p',
            '-c:v', 'libx264',
            '-preset', 'fast',
            '-crf', '23',
            '-g', '25',          # Keyframe cada 1s (25 frames a 25fps) → seeking preciso
            '-c:a', 'aac',
            '-b:a', '192k',
            '-shortest',         # Cortar en el stream más corto
            '-metadata', f'title={class_name}',
            output_path
        ]
    else:
        cmd = [
            FFMPEG, '-y',
            '-framerate', str(TARGET_FPS),
            '-i', os.path.join(seq_dir, 'f_%06d.png'),
            '-vf', 'scale=1920:1080:force_original_aspect_ratio=decrease,'
                   'pad=1920:1080:(ow-iw)/2:(oh-ih)/2:black',
            '-r', '25',
            '-pix_fmt', 'yuv420p',
            '-c:v', 'libx264',
            '-preset', 'fast',
            '-crf', '23',
            '-g', '25',
            '-metadata', f'title={class_name}',
            output_path
        ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  [!] Error creando MKV:")
        stderr_lines = result.stderr.strip().split('\n')
        for line in stderr_lines[-5:]:
            print(f"      {line}")
        return False

    print(f"  [+] ¡MKV generado!")

    # 7. Limpiar temporales
    import shutil
    try:
        shutil.rmtree(seq_dir, ignore_errors=True)
    except:
        pass

    return True

def get_class_name(metadata_path):
    try:
        tree = ET.parse(metadata_path)
        root = tree.getroot()
        for elem in root.iter():
            tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
            if tag == 'meetingName':
                if elem.text:
                    return elem.text
            if tag == 'meeting':
                name = elem.get('name', '')
                if name:
                    return name
    except:
        pass
    return "clase_sin_nombre"

def sanitize_filename(name):
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    name = name.strip('. ')
    return name[:100] if name else "clase"

# ==========================================
# MAIN
# ==========================================

if __name__ == '__main__':
    page = None
    descargas_exitosas = []
    final_save_path = None

    print("\n" + "=" * 55)
    print("   BBB DOWNLOADER - Slides + Anotaciones → MKV")
    print("=" * 55)

    if not os.path.exists(FFMPEG):
        print(f"[!] ffmpeg no encontrado en: {FFMPEG}")
        print("    Asegúrate de que ffmpeg.exe está en la carpeta padre (DRM_DOWNLOADER).")
        input("Presiona Enter para salir...")
        sys.exit(1)
    print(f"[OK] ffmpeg: {FFMPEG}")

    try:
        while True:
            if descargas_exitosas:
                print(f"\nVídeos generados esta sesión: {len(descargas_exitosas)}")
                for i, d in enumerate(descargas_exitosas, 1):
                    print(f"  {i}. {d}")
                print("-" * 50)

            # 1. Directorio
            if final_save_path is None:
                final_save_path = manage_save_directory()
            else:
                print(f"\nDirectorio actual: {final_save_path}")
                cambiar = input("¿Cambiar directorio? (s/N): ").strip().lower()
                if cambiar == 's':
                    final_save_path = manage_save_directory()

            # 2. Session ID
            print("\n--- NUEVA DESCARGA ---")

            session_id, page = get_session_id(page)
            if not session_id:
                continuar = input("\n¿Reintentar? (S/n): ").strip().lower()
                if continuar == 'n':
                    break
                continue

            print(f"  Session ID: {session_id}")

            # 3. Directorio de trabajo temporal
            work_dir = os.path.join(SCRIPT_DIR, "_temp_work", session_id[:16])
            os.makedirs(work_dir, exist_ok=True)

            # 4. Descargar archivos
            files_info = download_bbb_files(session_id, work_dir)

            # 5. Nombre de la clase
            class_name = get_class_name(files_info['metadata'])
            safe_name = sanitize_filename(class_name)
            print(f"\n  Clase: {class_name}")

            custom_name = input(f"  Nombre del MKV (Enter = '{safe_name}'):\n  > ").strip()
            if custom_name:
                safe_name = sanitize_filename(custom_name)

            output_path = os.path.join(final_save_path, f"{safe_name}.mkv")

            if os.path.exists(output_path):
                over = input(f"  [!] Ya existe '{safe_name}.mkv'. ¿Sobreescribir? (s/N): ").strip().lower()
                if over != 's':
                    counter = 1
                    while os.path.exists(output_path):
                        output_path = os.path.join(final_save_path, f"{safe_name}_{counter}.mkv")
                        counter += 1

            # 6. Generar vídeo
            success = generate_video(files_info, output_path, safe_name)

            if success:
                file_size = os.path.getsize(output_path) / (1024 * 1024)
                print(f"\n{'=' * 55}")
                print(f"  [OK] ¡DESCARGA COMPLETADA!")
                print(f"  Archivo: {output_path}")
                print(f"  Tamaño:  {file_size:.1f} MB")
                print(f"{'=' * 55}")
                descargas_exitosas.append(f"{safe_name}.mkv")
            else:
                print(f"\n  [!] Error generando el vídeo.")

            limpiar = input("\n¿Borrar archivos temporales? (S/n): ").strip().lower()
            if limpiar != 'n':
                import shutil
                try:
                    shutil.rmtree(work_dir)
                    print("  [+] Temporales eliminados.")
                except Exception as e:
                    print(f"  [!] Error limpiando: {e}")

            print("\n" + "-" * 40)
            continuar = input("¿Descargar otra clase? (S/n): ").strip().lower()
            if continuar == 'n':
                break

    except KeyboardInterrupt:
        print("\n\n[X] Sesión finalizada por el usuario.")
    finally:
        if page:
            print("\nCerrando navegador...")
            try:
                page.quit()
            except:
                pass
        print("¡Proceso finalizado!")
        time.sleep(2)
