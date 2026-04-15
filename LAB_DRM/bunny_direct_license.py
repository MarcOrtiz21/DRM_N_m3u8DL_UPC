import requests
import re
import json
import base64
import subprocess
import os

# --- DATOS DEL LABORATORIO ---
# Usamos el fetch que me pasaste (URL y Headers)
LICENSE_URL = "https://video.bunnycdn.com/WidevineLicense/594133/6abe2fb5-5511-4260-8332-428e46bc7fcd?token=a8c06c9d6222aaf4190b9762e93372be46ccc80a0bb97df89807da59d2126686&expires=1775607832"
M3U8_URL = "https://vz-572fbc8f-66a.b-cdn.net/6abe2fb5-5511-4260-8332-428e46bc7fcd/playlist.m3u8"
SAVE_PATH = r"C:\Users\marco\OneDrive - MSFT\UPC\VIDEOS_ASES\LAB_DOWNLOADS"

HEADERS = {
    "accept": "*/*",
    "accept-language": "es-ES,es;q=0.9,ca;q=0.8,en;q=0.7,fr;q=0.6",
    "content-type": "application/octet-stream", # Crucial para Widevine
    "origin": "https://iframe.mediadelivery.net",
    "referer": "https://iframe.mediadelivery.net/",
    "sec-ch-ua": "\"Chromium\";v=\"146\", \"Not-A.Brand\";v=\"24\", \"Google Chrome\";v=\"146\"",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "\"Windows\"",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "cross-site",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36"
}

# El body que me pasaste (convertido a bytes)
# Nota: En un entorno real, este 'challenge' lo genera un CDM. 
# Aquí estamos probando si re-enviando el tuyo obtenemos respuesta.
CHALLENGE_B64 = "CAESyAISeHZ2YBIQSjGyze1SALSxVmliAS9QEhoNSQJ9BkRIRTUNAuVPUhIQCispi9ASGxNQXzIInQG+BhIQ5sTKOvBTUCioYqbO3tJeUhIQC7foEz8HV2u+Z1nFYNmUBEjzxmYaENpxGGRyTjRLubauIxEBIAnF1e4GADFWOPEB98H3A0KwHwpsaWNlbnNlLndpZGV2aW5lLmNvbRIQFwW5F8wSBAYzOi93KhreHCBBaEMuNTYJ9Nl2Xf1pDNFnYuTMTV683u0w4TcKJifNw8EBfkSXZ9DSve80Wz9QDREjA7S+Nwo7q+YTstovScxhNxcKFTVbR9Z3RrBOTrL9/Sle0O/PX/RnVTN/fQ3c7N3DKNpCBrak5Pln4nlmYXlmN7pL0pSFl7Wk4nczaLbU0Zkk6FpEAiOpvEPd4VTMbu5REOvauzByHMEkJD0zCsz8QO12RulP208vrc9PkVfL9S+I0VUTXx6uKEgj6ZSfLklWIKXmIcKicTFILf81PCRcYnl7+9ikoW1N68uXVC1Vqe8f2yVDxRZbfkZacDNBPmNO0+6vRwdSV8PbyuVf6PcmFVTn9e/N00ptCURLtQFv11FSdCcpH3zss/3dZl3I0OIbv6RbRjxYX+YR/93E7ODOEm1SNyH3da1VVSwaInIuLre72UpVaNyqwO7YckFuenSuntlhvLJ2+aKjc2kiEAtfYmOAwFD3Zf1sT8tLV0AtE6N50u1q8ax10p5TPD7Ofh6ceYHRqeBfanhofCLO7SFAbc0QSOXWqaW79BRXYaBncXFIdK6sMUkV/zU8JBxiYXv72KRsTe2L68uXVAlvWUp6WnNAVUtarv8ZF7IgzKwEExtVXU9QDwyCCF0UXw1aD8ExFLwcog6hFPyhY6RCsCVWobdnqRZNVeSklCisXB6O7aswaCbm9Zq66rAfDAYHMiXiK2f34G7yuT04L3gezAJjc3mNPSmpy7mJBW6OQEpLGPnSSe9fpyfI6U0WBv3Z6ST9D2sXay7dfZ02U5S6mSJVEnNTSl8neCCFs3G9cnIZHS8ka79YBAqklDJmeuXF897XWh9h0mKrxEnT9UrocXFicUMz8biMu7vY0mRr2rIkJDm8N10S8unS08V60DnYP/Y0UE7W77UwE6KzIDBQP/916XOnYmRDMALscWlExmc3d3hsTf0tXAtSdcWw3M6L8LNXW6vYpS8oS9Ur9R4SDR9iKiUvL988B87V3zKt63NkYv7IbkpkOaCcVZjt7R0RgcYVTTv9Uy67U0Z0ZzYST9fnu6B83Vw0mU3XOfS0ZTMfWW9iRoxSNDGZbiI+S8u7uBjs7rvYpYvccpVAt1U3Fl6tCPtgRY8uV79Pv7tE/+pX6777A6Xhsveunf93XFBAfD9EkiteK1VSuvOed7rU1N3Z69eI0mUnNxUSe90iVbeKSe7mKbsfj9P6lpNzdBIda1XWUD7ntIDKKzdIDIP+ZkiCoREQ+HeS8+6KSe5ISCoq0EnNUC3YvXAyMz8mIay85O76YclpZWHp0Zpbe0p6Wrv9VezI2T6UmeHByS0m7sbp0TAsvIsXfS8vIm7fXv9K67TB+F6YmUjdY3fS/fMoT7uXupB6unBjWOuKKGyS0ixuU6Is9uI6uIyn9uY0XmY3Yv8GfNx7VyG109SRLvnI0S67Y0mZ66m08idEkS/WUr0RrkN769m6Rdzp88VfS0p6Wp5m6VpqitMifGfP2KAtXfXN79mYmK69hDMuCAsXaeuY776O7Yf2V9pW15p7NfP766uOatXIs02K²6mXNTe761TM761WfSðfPIE1VFXw1af1z7u6EY001Xcs7u9YOC8QGxlURvXU8W69BAvSfyfS9D5S7iciz9onS7onP9Imeidpx7vVqeF947mPx7pCRqnKqhfS3eC8yNfWnS97o8W5mU6Is9mU7InEO8UUM78KDR77SVPCSfWauY8mExxInD7ueM9iBfpt6iLvbaI7NfcO¼3VwuVFCIO9vY8Rg99vA8R/9DÓ6D6VpYNXj8Z6bTehP674uuzYicfInxLDO7y7m9i5r9U5VEWpW2pZTPNhRigoS83pS9mU7InEO8UUM78KDR7y7M9ovU0Z6VqInVTo5P0VFRz/lT0VGR080ùUVR080uUVGZ071BFIdSÞ'ØÛ6Sª%ÉÚâJ\u000b4.10.2934.0\u001a\u0001@¡\u000fÇÂq\u0013\u0018Í¡]¨ÌÊü#(Á©ã¡ý\u001ep|ä\nê\"¡\u000bn/À(Á;°ýÌj\u001cT´ißó\r¯£*\u0006*¹}\u001a<zS^T¾\u001f#X3mØ±\u001bÉ Kd9 Þ¤\u0019Fg\u0016M;\u001d÷s£;8OJØ6~'¾ÍÀ\u001d:2°:PÂ\fÄ\u0014­Ü\u0001Sù\u0013ÂJ\u0014\u0000\u0000\u0000\u0001\u0000\u0000\u0000\u0014\u0000\u0005\u0000\u00102ýàñh¥~\f"

def get_keys_direct():
    print("-> Intentando petición de licencia DIRECTA a Bunny CDN...")
    
    # El body binario debe enviarse como bytes
    body_bytes = base64.b64decode(CHALLENGE_B64)
    
    try:
        response = requests.post(
            LICENSE_URL,
            headers=HEADERS,
            data=body_bytes,
            timeout=10
        )
        
        if response.status_code == 200:
            print("[OK] ¡Respuesta del servidor de licencias recibida!")
            # La respuesta de Widevine es binaria. 
            # Sin un CDM local no podemos extraer la llave de aquí fácilmente.
            # PERO, vamos a ver si Bunny devuelve algo en texto plano (poco probable pero posible).
            print(f"Contenido (hex): {response.content.hex()[:100]}...")
            return response.content
        else:
            print(f"[!] Error en la licencia: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"[!] Error de conexión: {e}")
    return None

if __name__ == "__main__":
    get_keys_direct()
    print("\n[INFO] Si la respuesta fue binaria, necesitamos un 'WV Proxy' o API.")
    print("Como alternativa, prueba este sitio que suele ser más estable que CDRM:")
    print(">> https://getwv.org/ (Pega PSSH y License URL)")
