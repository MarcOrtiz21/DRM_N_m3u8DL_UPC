/**
 * ASES DRM Extractor - Popup Script
 * Muestra el estado del embed detectado y permite copiarlo.
 */

const contentEl = document.getElementById("content");
const statusEl = document.getElementById("status");

async function init() {
  try {
    // Obtener la pestaña activa
    const [tab] = await chrome.tabs.query({
      active: true,
      currentWindow: true,
    });

    if (!tab) {
      showError("No se pudo acceder a la pestaña activa.");
      return;
    }

    // Verificar que estamos en ASES
    if (!tab.url || !tab.url.includes("asesacademia.com")) {
      showNotAses();
      return;
    }

    // Pedir al content script que busque el embed
    try {
      const response = await chrome.tabs.sendMessage(tab.id, {
        type: "getEmbed",
      });

      if (response && response.url) {
        showFound(response.url, response.pageTitle || tab.title);
      } else {
        showNotFound();
      }
    } catch (e) {
      // Content script no cargado, intentar inyectarlo
      try {
        const results = await chrome.scripting.executeScript({
          target: { tabId: tab.id },
          func: () => {
            // Búsqueda inline por si el content script no está
            const html = document.documentElement.innerHTML;
            const match = html.match(
              /https:\/\/iframe\.mediadelivery\.net\/embed\/\d+\/[a-f0-9\-]+[^"'\s<>]*/
            );
            return match ? match[0].replace(/&amp;/g, "&") : null;
          },
        });

        const url = results?.[0]?.result;
        if (url) {
          showFound(url, tab.title);
        } else {
          showNotFound();
        }
      } catch (e2) {
        showNotFound();
      }
    }
  } catch (e) {
    showError("Error: " + e.message);
  }
}

function showFound(embedUrl, pageTitle) {
  statusEl.className = "status found";
  statusEl.innerHTML = "✅ Vídeo detectado";

  contentEl.innerHTML = `
    <div class="status found" id="status">✅ Vídeo detectado</div>
    <div class="title-info">
      <strong>Página:</strong> ${escapeHtml(pageTitle || "Sin título")}
    </div>
    <div class="url-box" id="url-display">${escapeHtml(embedUrl)}</div>
    <button class="btn btn-primary" id="btn-copy-embed">
      📋 Copiar Embed URL
    </button>
    <button class="btn btn-secondary" id="btn-copy-full">
      📝 Copiar como comando
    </button>
    <div class="feedback" id="feedback"></div>
    <div class="help">
      Pega la URL en <strong>Lanzar_DRM_Offline.bat</strong> para descargar.
    </div>
  `;

  // Copiar embed URL
  document.getElementById("btn-copy-embed").addEventListener("click", () => {
    navigator.clipboard.writeText(embedUrl).then(() => {
      showFeedback("✅ ¡Embed URL copiada!");
    });
  });

  // Copiar como comando Python
  document.getElementById("btn-copy-full").addEventListener("click", () => {
    const cmd = `python LAB_DRM\\bunny_lab_offline.py`;
    const fullText = `URL: ${embedUrl}\n\nEjecuta: ${cmd}\nY pega la URL de arriba cuando te lo pida.`;
    navigator.clipboard.writeText(embedUrl).then(() => {
      showFeedback("✅ ¡Copiado! Pégalo en el script.");
    });
  });
}

function showNotFound() {
  contentEl.innerHTML = `
    <div class="status not-found" id="status">
      ⚠️ No se detectó vídeo Bunny CDN en esta página
    </div>
    <div class="help">
      Navega a una clase de ASES con grabación y abre el vídeo.<br><br>
      Si ya estás viendo el vídeo, haz clic en 
      <strong>"Ver grabación"</strong> o <strong>"Abrir grabación"</strong>.
    </div>
  `;
}

function showNotAses() {
  contentEl.innerHTML = `
    <div class="status not-found" id="status">
      📌 No estás en ASES Academia
    </div>
    <div class="help">
      Navega a <strong>asesacademia.com/campus</strong> 
      y abre una clase con vídeo grabado.
    </div>
  `;
}

function showError(msg) {
  contentEl.innerHTML = `
    <div class="status error" id="status">❌ ${escapeHtml(msg)}</div>
  `;
}

function showFeedback(msg) {
  const fb = document.getElementById("feedback");
  if (fb) {
    fb.textContent = msg;
    setTimeout(() => {
      fb.textContent = "";
    }, 3000);
  }
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

init();
