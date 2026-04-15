import re
import json
import subprocess

def procesar_headers_cdrm():
    print("=== PASO 1: Formatear Headers para CDRM-Project ===")
    print("Pega tu 'Copy as fetch' aquí (Presiona Enter DOS veces cuando termines de pegar):")
    fetch_text = ""
    while True:
        line = input()
        if not line: break
        fetch_text += line + "\n"
    
    if fetch_text.strip():
        # Extraemos solo el bloque de los headers del fetch
        headers_match = re.search(r'"headers"\s*:\s*(\{.*?\})', fetch_text, re.DOTALL)
        if headers_match:
            headers_str = headers_match.group(1)
            headers_dict = {}
            
            # Extraemos clave-valor ignorando corchetes y comas para evitar errores de sintaxis
            pares = re.findall(r'"([^"]+)"\s*:\s*"([^"]+)"', headers_str)
            for k, v in pares:
                headers_dict[k] = v
            
            # Añadimos las cabeceras requeridas
            headers_dict["Origin"] = "https://iframe.mediadelivery.net"
            headers_dict["Referer"] = "https://iframe.mediadelivery.net/"
            
            # Convertimos a JSON en una sola línea para CDRM
            cdrm_json = json.dumps(headers_dict, separators=(',', ':'))
            print("\n[EXITO] Copia este texto y pégalo en la web de CDRM-Project:")
            print("-" * 60)
            print(cdrm_json)
            print("-" * 60 + "\n")
        else:
            print("\n[!] No se detectaron headers. Asegúrate de haber pegado el 'Copy as fetch' completo.\n")
    else:
        print("\nSaltando paso de headers...\n")

def descargar_video():
    print("=== PASO 2: Descarga con N_m3u8DL-RE ===")
    m3u8 = input("1. Pega el enlace m3u8:\n> ").strip()
    nombre = input("2. Nombre del archivo a guardar:\n> ").strip()
    
    # Ruta por defecto modificable
    ruta_defecto = r"C:\Users\marco\Videos"
    ruta = input(f"3. Ruta de guardado (Presiona Enter para usar {ruta_defecto}):\n> ").strip()
    if not ruta:
        ruta = ruta_defecto
        
    print("4. Pega las KEYS que te dio CDRM (Pega todo de golpe y presiona Enter DOS veces):")
    keys_text = ""
    while True:
        line = input()
        if not line: break
        keys_text += line + " "
        
    # El script busca automáticamente cualquier patrón que parezca una key (32 hex : 32 hex)
    keys_encontradas = re.findall(r'([a-fA-F0-9]{32}:[a-fA-F0-9]{32})', keys_text)
    
    # Construcción del comando
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
    
    # Añadimos cada key encontrada al comando
    for k in keys_encontradas:
        comando.extend(["--key", k])
        
    print(f"\nSe encontraron {len(keys_encontradas)} keys. Iniciando descarga...")
    print("-" * 60)
    
    # Ejecuta el comando en la terminal
    subprocess.run(comando)

if __name__ == '__main__':
    try:
        procesar_headers_cdrm()
        if input("¿Continuar a la descarga? (s/n): ").strip().lower() == 's':
            descargar_video()
    except KeyboardInterrupt:
        print("\nProceso cancelado por el usuario.")
    
    input("\nPresiona Enter para cerrar la ventana...")