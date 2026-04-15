/**
 * ASES DRM Extractor - Content Script
 * Se inyecta en las páginas de asesacademia.com/campus/*
 * Detecta el iframe de vídeo de Bunny CDN y ofrece copiarlo.
 */

(function () {
  "use strict";

  const STORAGE_KEY = "ases_drm_last_embed";
  let floatingBtn = null;
  let detectedUrl = null;
  let observer = null;

  // ── Buscar iframe embed en el DOM ──
  function findEmbedUrl() {
    // Método 1: buscar iframes directamente
    const iframes = document.querySelectorAll("iframe");
    for (const iframe of iframes) {
      const src = iframe.src || iframe.getAttribute("data-src") || "";
      if (src.includes("iframe.mediadelivery.net/embed/")) {
        return src;
      }
    }

    // Método 2: buscar en data-url u otros atributos
    const dataUrlEls = document.querySelectorAll("[data-url]");
    for (const el of dataUrlEls) {
      const url = el.getAttribute("data-url") || "";
      if (url.includes("iframe.mediadelivery.net/embed/")) {
        return url;
      }
    }

    // Método 3: buscar en el HTML raw (algunos frameworks renderizan tarde)
    const htmlText = document.documentElement.innerHTML;
    const match = htmlText.match(
      /https:\/\/iframe\.mediadelivery\.net\/embed\/\d+\/[a-f0-9\-]+[^"'\s<>]*/
    );
    if (match) {
      return match[0].replace(/&amp;/g, "&");
    }

    return null;
  }

  // ── Crear el botón flotante ──
  function createFloatingButton(embedUrl) {
    if (floatingBtn) {
      floatingBtn.remove();
    }

    floatingBtn = document.createElement("div");
    floatingBtn.id = "ases-drm-float";
    floatingBtn.innerHTML = `
      <div class="ases-drm-header">
        <span class="ases-drm-icon">🎬</span>
        <span class="ases-drm-title">ASES DRM</span>
        <button class="ases-drm-close" title="Cerrar">✕</button>
      </div>
      <div class="ases-drm-body">
        <div class="ases-drm-status">✅ Vídeo detectado</div>
        <div class="ases-drm-url-preview">${embedUrl.substring(0, 60)}...</div>
        <button class="ases-drm-copy-btn" id="ases-copy-embed">
          📋 Copiar Embed URL
        </button>
        <div class="ases-drm-feedback" id="ases-feedback"></div>
      </div>
    `;

    document.body.appendChild(floatingBtn);

    // Botón copiar
    document.getElementById("ases-copy-embed").addEventListener("click", () => {
      navigator.clipboard.writeText(embedUrl).then(() => {
        const fb = document.getElementById("ases-feedback");
        fb.textContent = "✅ ¡Copiado! Pégalo en el script.";
        fb.style.color = "#4caf50";
        setTimeout(() => {
          fb.textContent = "";
        }, 3000);
      });
    });

    // Botón cerrar
    floatingBtn.querySelector(".ases-drm-close").addEventListener("click", () => {
      floatingBtn.style.display = "none";
    });

    // Guardar en storage para el popup
    try {
      chrome.storage.local.set({
        [STORAGE_KEY]: {
          url: embedUrl,
          pageUrl: window.location.href,
          pageTitle: document.title,
          timestamp: Date.now(),
        },
      });
    } catch (e) {
      // storage puede no estar disponible
    }
  }

  // ── Escanear la página ──
  function scan() {
    const url = findEmbedUrl();
    if (url && url !== detectedUrl) {
      detectedUrl = url;
      createFloatingButton(url);
      console.log("[ASES DRM] Embed detectado:", url);
    }
  }

  // ── Observar cambios en el DOM (SPAs, carga dinámica) ──
  function startObserver() {
    scan(); // escaneo inicial

    observer = new MutationObserver(() => {
      scan();
    });

    observer.observe(document.body, {
      childList: true,
      subtree: true,
      attributes: true,
      attributeFilter: ["src", "data-src", "data-url"],
    });

    // Escaneo periódico por si acaso (cada 2s durante 30s)
    let attempts = 0;
    const interval = setInterval(() => {
      scan();
      attempts++;
      if (attempts >= 15 || detectedUrl) {
        clearInterval(interval);
      }
    }, 2000);
  }

  // ── Escuchar mensajes del popup ──
  chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    if (msg.type === "getEmbed") {
      scan(); // forzar escaneo
      sendResponse({ url: detectedUrl, pageTitle: document.title });
    }
  });

  // ── Inicio ──
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", startObserver);
  } else {
    startObserver();
  }
})();
