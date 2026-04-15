/**
 * ASES DRM Extractor - Background Service Worker
 * Mantiene el estado y gestiona comunicaciones.
 */

// Escuchar cuando se instala la extensión
chrome.runtime.onInstalled.addListener(() => {
  console.log("[ASES DRM] Extensión instalada correctamente.");
});

// Escuchar mensajes del content script o popup
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.type === "embedFound") {
    // Guardar el último embed encontrado
    chrome.storage.local.set({
      ases_drm_last_embed: {
        url: msg.url,
        tabId: sender.tab?.id,
        pageUrl: sender.tab?.url,
        pageTitle: sender.tab?.title,
        timestamp: Date.now(),
      },
    });

    // Cambiar el badge del icono para indicar que hay un vídeo
    if (sender.tab?.id) {
      chrome.action.setBadgeText({ text: "1", tabId: sender.tab.id });
      chrome.action.setBadgeBackgroundColor({
        color: "#7209b7",
        tabId: sender.tab.id,
      });
    }
  }

  return true; // keep message channel open
});
