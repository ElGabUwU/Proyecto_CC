(function() {
    // Configuración centralizada
    const CONFIG = {
        WARNING_TIME: 270000,      // 4:30 minutos - Mostrar advertencia
        LOGOUT_DELAY: 30000,       // 30 segundos - Tiempo para responder
        PING_INTERVAL: 60000,      // 1 minuto - Verificar sesión con backend
        SESSION_CHECK_URL: '/check-session/',  // Endpoint para verificar sesión
        LOGOUT_URL: '/logout/'
    };

    let warningTimeout;
    let logoutTimeout;
    let pingInterval;
    let isWarningShown = false;
    let isActive = true;

    // Verificar si la sesión aún es válida en el backend
    const checkSession = async function() {
        try {
            const response = await fetch(CONFIG.SESSION_CHECK_URL, {
                method: 'GET',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'Content-Type': 'application/json'
                },
                credentials: 'same-origin'
            });
            
            if (!response.ok) {
                // Sesión expirada en backend
                forceLogout('Tu sesión ha expirado. Por favor inicia sesión nuevamente.');
            }
            return response.ok;
        } catch (error) {
            console.error('Error verificando sesión:', error);
            return false;
        }
    };

    // Forzar cierre de sesión con mensaje
    const forceLogout = function(message) {
        isActive = false;
        clearTimeout(warningTimeout);
        clearTimeout(logoutTimeout);
        clearInterval(pingInterval);
        
        // Cerrar cualquier modal Bootstrap abierto
        document.querySelectorAll('.modal').forEach(modal => {
            const bsModal = bootstrap.Modal.getInstance(modal);
            if (bsModal) {
                bsModal.hide();
            }
        });
        
        // Mostrar mensaje y redirigir
        Swal.fire({
            icon: 'warning',
            title: 'Sesión Expirada',
            text: message || 'Tu sesión ha expirado por inactividad.',
            confirmButtonText: 'Ir al Login',
            confirmButtonColor: '#3085d6',
            allowOutsideClick: false,
            allowEscapeKey: false
        }).then(() => {
            window.location.href = CONFIG.LOGOUT_URL;
        });
    };

    const startTimers = function () {
        clearTimeout(warningTimeout);
        clearTimeout(logoutTimeout);
        isWarningShown = false;
        
        // Iniciar timer de advertencia
        warningTimeout = setTimeout(showWarning, CONFIG.WARNING_TIME);
    };

    const showWarning = function () {
        if (!isActive || isWarningShown) return;
        
        isWarningShown = true;
        
        // Detener ping temporalmente
        clearInterval(pingInterval);
        
        Swal.fire({
            title: 'Tu sesión está a punto de expirar',
            text: 'Tu sesión se cerrará en 30 segundos por inactividad.',
            icon: 'warning',
            showCancelButton: true,
            confirmButtonColor: '#3085d6',
            cancelButtonColor: '#d33',
            confirmButtonText: 'Mantener sesión',
            cancelButtonText: 'Cerrar sesión',
            allowOutsideClick: false,
            allowEscapeKey: false,
            timer: CONFIG.LOGOUT_DELAY,
            timerProgressBar: true
        }).then((result) => {
            if (result.isConfirmed) {
                // Usuario quiere mantener sesión - verificar con backend
                keepSessionAlive();
            } else {
                // Usuario eligió cerrar o el timer expiró
                forceLogout('Sesión cerrada por inactividad.');
            }
        });
    };

    const keepSessionAlive = async function() {
        try {
            const response = await fetch(CONFIG.SESSION_CHECK_URL, {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken()
                },
                credentials: 'same-origin'
            });
            
            if (response.ok) {
                // Sesión renovada exitosamente
                Swal.fire({
                    icon: 'success',
                    title: '¡Sesión renovada!',
                    text: 'Tu sesión ha sido extendida.',
                    timer: 2000,
                    showConfirmButton: false
                });
                isActive = true;
                startTimers();
                startPingInterval();
            } else {
                forceLogout('No se pudo renovar la sesión. Por favor inicia sesión nuevamente.');
            }
        } catch (error) {
            console.error('Error renovando sesión:', error);
            forceLogout('Error de conexión. Por favor inicia sesión nuevamente.');
        }
    };

    const getCsrfToken = function() {
        const name = 'csrftoken';
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    };

    const startPingInterval = function() {
        clearInterval(pingInterval);
        pingInterval = setInterval(checkSession, CONFIG.PING_INTERVAL);
    };

    const resetTimer = function () {
        if (!isActive) return;
        
        // Solo resetear si no estamos mostrando la advertencia
        if (!isWarningShown) {
            startTimers();
        }
    };

    // Event listeners para actividad del usuario
    const activityEvents = ['mousemove', 'keypress', 'click', 'scroll', 'focus'];
    
    activityEvents.forEach(event => {
        document.addEventListener(event, resetTimer, { passive: true, capture: true });
    });

    // Verificar visibilidad de la pestaña
    document.addEventListener('visibilitychange', function() {
        if (document.visibilityState === 'visible') {
            // Pestaña visible - verificar sesión
            checkSession().then(valid => {
                if (valid) {
                    isActive = true;
                    startTimers();
                    startPingInterval();
                } else {
                    forceLogout('Tu sesión expiró mientras estabas en otra pestaña.');
                }
            });
        }
    });

    // Inicializar
    const init = function() {
        // Esperar a que el DOM esté listo
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', start);
        } else {
            start();
        }
    };

    const start = function() {
        startTimers();
        startPingInterval();
    };

    init();
})();
