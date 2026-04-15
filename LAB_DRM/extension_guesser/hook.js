// Este script corre DENTRO de la página y puede ver el tráfico DRM
(function() {
    console.log("[LAB] EME Hooking activado...");

    const originalGenerateRequest = MediaKeySession.prototype.generateRequest;
    MediaKeySession.prototype.generateRequest = function(initDataType, initData) {
        if (initDataType === 'cenc') {
            const pssh = btoa(String.fromCharCode.apply(null, new Uint8Array(initData)));
            console.log("[LAB] PSSH Detectado (Base64):", pssh);
            
            // Crear un aviso visual en la web para que el usuario no tenga que abrir la consola
            const div = document.createElement('div');
            div.style = "position:fixed;top:10px;right:10px;z-index:999999;background:black;color:yellow;padding:15px;border:2px solid red;font-family:monospace;max-width:400px;word-break:break-all;";
            div.innerHTML = `<strong>¡PSSH DETECTADO!</strong><br><small>Cópialo para CDRM-Project:</small><br><br>${pssh}<br><br><button onclick="this.parentElement.remove()">Cerrar</button>`;
            document.body.appendChild(div);
        }
        return originalGenerateRequest.apply(this, arguments);
    };
})();
