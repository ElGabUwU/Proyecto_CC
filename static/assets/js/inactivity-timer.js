(function() {
    const inactivityTime = function () {
        let warningTimeout;
        let logoutTimeout;

        const startTimers = function () {
            warningTimeout = setTimeout(warn, 270000); // 4 minutes and 30 seconds
        };

        const warn = function () {
            Swal.fire({
                title: 'Tu sesión está a punto de expirar',
                text: "Tu sesión se cerrará en 30 segundos por inactividad.",
                icon: 'warning',
                showCancelButton: true,
                confirmButtonColor: '#3085d6',
                cancelButtonColor: '#d33',
                confirmButtonText: 'Mantener sesión',
                cancelButtonText: 'Cerrar sesión'
            }).then((result) => {
                if (result.isConfirmed) {
                    resetTimer();
                } else {
                    logout();
                }
            });

            logoutTimeout = setTimeout(logout, 30000); // 30 seconds
        };

        const logout = function () {
            window.location.href = '/logout/';
        };

        const resetTimer = function () {
            clearTimeout(warningTimeout);
            clearTimeout(logoutTimeout);
            startTimers();
        };

        window.onload = resetTimer;
        document.onmousemove = resetTimer;
        document.onkeypress = resetTimer;
        document.onclick = resetTimer;
        document.onscroll = resetTimer;
        document.onfocus = resetTimer;

        startTimers();
    };

    inactivityTime();
})();
