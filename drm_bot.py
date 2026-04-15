import os
import re
import subprocess
import time
import sys

# --- CONFIGURACIÓN DE DIRECTORIOS ---
BASE_SAVE_PATH = r"C:\Users\marco\OneDrive - MSFT\UPC\VIDEOS_ASES"
PRESET_PERIODS = ["Parcial", "Intensivo Parcial", "Final", "Intensivo Final"]

# --- INSTALACIÓN DE DEPENDENCIAS ---
try:
    from DrissionPage import ChromiumPage
except ImportError:
    print("Instalando dependencias faltantes para la automatización web...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "DrissionPage"])
    from DrissionPage import ChromiumPage

# ==========================================
# SECCIÓN 1: GESTIÓN DE DIRECTORIOS
# ==========================================

def print_menu(title, options):
    print(f"\n--- {title} ---")
    print(f"Directorio base: {BASE_SAVE_PATH}")
    for option in options:
        print(option)
    print("-------------------------------")

def select_from_disk(path):
    try:
        return [f for f in os.listdir(path) if os.path.isdir(os.path.join(path, f))]
    except FileNotFoundError:
        return []

def choose_subject_folder():
    while True:
        folders = select_from_disk(BASE_SAVE_PATH)
        folders.sort()

        options = []
        for i, f in enumerate(folders):
            options.append(f"{i + 1}. {f}")
        
        num_new = len(folders) + 1
        num_rename = len(folders) + 2
        options.append(f"{num_new}. [N] Crear nueva carpeta de asignatura")
        options.append(f"{num_rename}. [R] Renombrar una carpeta existente")

        print_menu("SELECCIÓN DE ASIGNATURA", options)
        
        try:
            choice = input("Elija una opción por número o carpeta de asignatura (Enter para salir):\n> ").strip()
            
            if not choice: 
                print("Saliendo...")
                sys.exit(0)

            if choice.isdigit():
                num_choice = int(choice)
                
                if 1 <= num_choice <= len(folders):
                    selected_name = folders[num_choice - 1]
                    final_path = os.path.join(BASE_SAVE_PATH, selected_name)
                    print(f"-> Carpeta seleccionada: {final_path}")
                    return final_path
                
                elif num_choice == num_new:
                    while True:
                        new_name = input("Introduzca el nombre de la nueva carpeta de asignatura (o Enter para cancelar):\n> ").strip()
                        if not new_name: break
                        new_path = os.path.join(BASE_SAVE_PATH, new_name)
                        if os.path.exists(new_path):
                            print(f"[!] Error: La carpeta '{new_name}' ya existe.")
                        else:
                            os.makedirs(new_path)
                            print(f"[+] Carpeta '{new_name}' creada con éxito.")
                            return new_path
                    continue

                elif num_choice == num_rename:
                    while True:
                        old_num = input("Introduzca el número de la carpeta a renombrar (o Enter para cancelar):\n> ").strip()
                        if not old_num: break
                        if old_num.isdigit() and 1 <= int(old_num) <= len(folders):
                            old_num = int(old_num)
                        else:
                            print("[!] Error: Número de carpeta inválido.")
                            continue
                        
                        old_name = folders[old_num - 1]
                        
                        new_name = input(f"Introduzca el nuevo nombre para '{old_name}' (o Enter para cancelar):\n> ").strip()
                        if not new_name or new_name == old_name: 
                            break
                        
                        old_path = os.path.join(BASE_SAVE_PATH, old_name)
                        new_path = os.path.join(BASE_SAVE_PATH, new_name)
                        
                        if os.path.exists(new_path):
                            print(f"[!] Error: Una carpeta con el nombre '{new_name}' ya existe.")
                        else:
                            os.rename(old_path, new_path)
                            print(f"[+] Carpeta '{old_name}' renombrada a '{new_name}' con éxito.")
                            break
                    continue

                else:
                    print("[!] Opción numérica inválida.")
            else:
                if choice in folders:
                    final_path = os.path.join(BASE_SAVE_PATH, choice)
                    print(f"-> Carpeta seleccionada: {final_path}")
                    return final_path
                else:
                    print("[!] No se encontró la carpeta. Compruebe el menú numerado.")

        except ValueError:
            print("[!] Error: Introduzca un número o carpeta válida.")

def choose_period_folder(subject_path):
    current_path = subject_path
    while True:
        subfolders = select_from_disk(current_path)
        subfolders.sort()
        
        options = []
        mapping = {}
        
        if current_path == subject_path:
            display_list = []
            for p in PRESET_PERIODS:
                display_list.append((p, p in subfolders))
            
            for f in subfolders:
                if f not in PRESET_PERIODS:
                    display_list.append((f, True))
            
            for i, (name, exists) in enumerate(display_list):
                item_num = i + 1
                status = "" if exists else " (se creará)"
                options.append(f"{item_num}. {name}{status}")
                mapping[item_num] = name
        else:
            for i, f in enumerate(subfolders):
                item_num = i + 1
                options.append(f"{item_num}. {f}")
                mapping[item_num] = f
        
        num_select = len(mapping) + 1
        num_new = len(mapping) + 2
        num_back = len(mapping) + 3
        
        options.append(f"{num_select}. [S] SELECCIONAR ESTA CARPETA")
        options.append(f"{num_new}. [N] Crear nueva subcarpeta")
        if current_path != subject_path:
            options.append(f"{num_back}. [B] Volver atrás")
        else:
            options.append(f"{num_back}. [V] Volver a selección de asignatura")
            
        rel_path = os.path.relpath(current_path, subject_path)
        subj_name = os.path.basename(subject_path)
        title_path = subj_name if rel_path == "." else f"{subj_name} > {rel_path}"
        print_menu(f"SELECCIÓN DE CARPETA DESTINO: {title_path}", options)
        
        choice = input("Elija una opción (Enter para salir):\n> ").strip().upper()
        
        if not choice:
            print("Saliendo...")
            sys.exit(0)
            
        if choice == 'S' or choice == str(num_select):
            if not os.path.exists(current_path):
                try:
                    os.makedirs(current_path)
                    print(f"[+] Carpeta creada: {current_path}")
                except Exception as e:
                    print(f"[!] Error al crear carpeta: {e}")
                    continue
            print(f"-> Carpeta seleccionada: {current_path}")
            return current_path
            
        if choice == 'N' or choice == str(num_new):
            new_name = input("Nombre de la nueva subcarpeta (Enter para cancelar):\n> ").strip()
            if new_name:
                new_path = os.path.join(current_path, new_name)
                if not os.path.exists(new_path):
                    try:
                        os.makedirs(new_path)
                        current_path = new_path
                        print(f"[+] Carpeta '{new_name}' creada.")
                    except Exception as e:
                        print(f"[!] Error al crear carpeta: {e}")
                else:
                    print("[!] La carpeta ya existe.")
                    current_path = new_path
            continue
            
        if choice == 'B' or choice == str(num_back):
            if current_path != subject_path:
                current_path = os.path.dirname(current_path)
                continue
            else:
                return "BACK_TO_SUBJECT"
            
        if choice == 'V':
            return "BACK_TO_SUBJECT"

        if choice.isdigit():
            num = int(choice)
            if num in mapping:
                selected = mapping[num]
                current_path = os.path.join(current_path, selected)
                continue
        
        print("[!] Opción inválida.")

def manage_save_directory_interactively():
    print("\n==========================================")
    print("GESTIÓN DE DIRECTORIOS INTERACTIVA")
    print("==========================================")
    
    while True:
        subject_path = choose_subject_folder()
        final_save_path = choose_period_folder(subject_path)
        
        if final_save_path == "BACK_TO_SUBJECT":
            continue
            
        return final_save_path

# ==========================================
# SECCIÓN 2: AUTOMATIZACIÓN DE DESCARGA
# ==========================================

def obtain_fetch_original():
    print("\n=== PASO 3: Pegar el Fetch ===")
    print("Pega tu 'Copy as fetch' aquí (Presiona Enter DOS veces al terminar):")
    fetch_text = ""
    while True:
        line = input()
        if not line: break
        fetch_text += line + "\n"
    return fetch_text

def automatizar_cdrm(fetch_text, page=None):
    """Lógica de extracción original (Punto 4 restaurado)"""
    print("\n=== PASO 4: Extrayendo Keys con el Bot ===")
    
    # Si no nos pasan una página abierta, la creamos (y la cerraremos al final)
    should_quit = False
    if page is None:
        print("Abriendo sesión aislada del navegador con 'DrissionPage'...")
        page = ChromiumPage()
        should_quit = True
    
    page.get('https://cdrm-project.com/')
    time.sleep(2)
    
    try:
        boton_paste = page.ele('xpath://button[text()="Paste from fetch"]')
        if boton_paste:
            page.run_js('window.prompt = function() { return arguments[0]; };', fetch_text)
            boton_paste.click()
            print("-> 'Paste from fetch' ejecutado con éxito.")
    except Exception as e:
        print(f"[!] Problema al usar 'Paste from fetch': {e}")

    time.sleep(2)
    
    try:
        textareas = page.eles('tag:textarea')
        caja_headers = None
        
        for ta in textareas:
            val = ta.value
            if val and '"accept"' in val:
                caja_headers = ta
                break
                
        if caja_headers:
            json_actual = caja_headers.value
            if json_actual.strip().endswith('}'):
                json_nuevo = json_actual.strip()[:-1] + ',"Origin":"https://iframe.mediadelivery.net","Referer":"https://iframe.mediadelivery.net/"}'
                caja_headers.clear()
                caja_headers.input(json_nuevo)
                print("-> Headers editados en la web con éxito.")
            else:
                print("[!] Error: El contenido de la caja Headers no tiene el formato esperado.")
        else:
            print("[!] Error: No se encontró la caja de Headers en la web.")
            
    except Exception as e:
        print(f"[!] Error modificando los headers en la página: {e}")

    time.sleep(1) 
    
    try:
        boton_submit = page.ele('xpath://button[text()="Submit"]')
        if boton_submit:
            boton_submit.click()
            print("-> Clic en Submit. Esperando las llaves del servidor...")
    except:
        print("[!] Error: No pude hacer clic en Submit.")

    time.sleep(6)
    
    texto_pagina = page.html
    keys_encontradas = re.findall(r'([a-fA-F0-9]{32}:[a-fA-F0-9]{32})', texto_pagina)
    
    if should_quit:
        page.quit()
    
    return list(set(keys_encontradas))

def descargar_video(m3u8, nombre, ruta, keys):
    print(f"\n=== PASO 5: Descarga Iniciada ({len(keys)} keys obtenidas) ===")
    
    comando = [
        "N_m3u8DL-RE", m3u8,
        "--save-dir", ruta,
        "--save-name", nombre,
        "-H", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
        "-H", "Origin: https://iframe.mediadelivery.net",
        "-H", "Referer: https://iframe.mediadelivery.net/",
        "--auto-select",
        "-M", "format=mkv"
    ]
    
    for k in keys:
        comando.extend(["--key", k])
        
    print(f"Ejecutando comando N_m3u8DL-RE para guardar en '{ruta}'...")
    subprocess.run(comando)

# --- EJECUCIÓN PRINCIPAL ---
if __name__ == '__main__':
    page = None
    descargas_exitosas = []
    final_save_path = None

    try:
        while True:
            print("\n" + "="*50)
            print("         DRM DOWNLOADER BOT - SESIÓN ACTIVA")
            print("="*50)
            
            if descargas_exitosas:
                print(f"Vídeos descargados en esta sesión: {len(descargas_exitosas)}")
                for i, d in enumerate(descargas_exitosas, 1):
                    print(f"  {i}. {d}")
                print("-" * 50)

            # 1. Selección de Directorio
            if final_save_path is None:
                final_save_path = manage_save_directory_interactively()
            else:
                print(f"Directorio actual: {final_save_path}")
                cambiar = input("¿Deseas cambiar el directorio de guardado? (s/N): ").strip().lower()
                if cambiar == 's':
                    final_save_path = manage_save_directory_interactively()

            # 2. Datos del vídeo
            print("\n--- NUEVA DESCARGA ---")
            m3u8_url = input("1. Pega el enlace m3u8 (o deja vacío para salir):\n> ").strip()
            if not m3u8_url:
                break
                
            nombre_archivo = input("2. Nombre del archivo a guardar:\n> ").strip()
            if not nombre_archivo:
                nombre_archivo = f"video_{int(time.time())}"
            
            # 3. Obtención del Fetch
            fetch_crudo = obtain_fetch_original()
            
            if not fetch_crudo.strip():
                print("\n[!] Error: No has pegado ningún fetch válido. Reintentando...")
                continue

            # 4. Automatización CDRM (Persistencia activada)
            if page is None:
                print("Iniciando navegador...")
                page = ChromiumPage()
            
            claves = automatizar_cdrm(fetch_crudo, page=page)
            
            if claves:
                descargar_video(m3u8_url, nombre_archivo, final_save_path, claves)
                descargas_exitosas.append(nombre_archivo)
                print(f"\n[OK] Descarga de '{nombre_archivo}' completada.")
            else:
                print("\n[!] Error: No se extrajeron keys. Compruebe si CDRM pidió Captcha o si caducó el fetch.")

            print("\n" + "-"*40)
            continuar = input("¿Deseas descargar otro vídeo? (S/n): ").strip().lower()
            if continuar == 'n':
                break

    except KeyboardInterrupt:
        print("\n\n[X] Sesión finalizada por el usuario.")
    finally:
        if page:
            print("\nCerrando navegador...")
            page.quit()
        print("¡Proceso finalizado!")
        time.sleep(2)
