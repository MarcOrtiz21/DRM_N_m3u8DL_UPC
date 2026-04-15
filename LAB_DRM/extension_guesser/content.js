// Inyecta el hook.js en el contexto real de la página
const s = document.createElement('script');
s.src = chrome.runtime.getURL('hook.js');
s.onload = function() { this.remove(); };
(document.head || document.documentElement).appendChild(s);

console.log("[LAB] Content Script: Hook inyectado.");
