// Botón para alternar el sidebar
const toggleSidebarBtn = document.getElementById('toggleSidebarBtn');
const sidebar = document.querySelector('.sidebar');

toggleSidebarBtn.addEventListener('click', () => {
  sidebar.classList.toggle('collapsed'); // Alternar la clase 'collapsed'
});

document.getElementById("toggleSidebarBtn").addEventListener("click", function () {
  this.classList.toggle("active"); // Alterna la animación
});

// Capturar el evento de apertura del modal
const modal = document.getElementById('controlNominaModal');
const modalTitle = document.getElementById('modalTitle');
const cedulaIdInput = document.getElementById('cedulaIdInput');

// Escuchar el evento 'show.bs.modal'
modal.addEventListener('show.bs.modal', function (event) {
  const button = event.relatedTarget;
  const cedulaId = button.getAttribute('data-cedula-id');
  if (cedulaId) {
    modalTitle.textContent = 'Editar Datos';
    cedulaIdInput.value = cedulaId;
  } else {
    modalTitle.textContent = 'Ingresar Datos';
    cedulaIdInput.value = '';
  }
});

// Escuchar el evento 'hidden.bs.modal'
modal.addEventListener('hidden.bs.modal', function () {
  modalTitle.textContent = 'Ingresar Datos';
  cedulaIdInput.value = '';
  document.getElementById('nominaForm').reset();
});

// Función para mostrar el Control de Nómina
function mostrarControlNomina() {
  document.getElementById('control-nomina').style.display = 'block';
  document.getElementById('calendario-container').style.display = 'none';
}

// Función para mostrar el calendario

  // Mostrar calendario y ocultar la vista de nómina
  function mostrarCalendario() {
    document.querySelector('.main-content').style.display = 'none'; // Oculta control nómina
    document.getElementById('calendario-container').style.display = 'block'; // Muestra calendario

    if (!window.calendarInitialized) {
      const calendarEl = document.getElementById('calendar');
      const calendar = new FullCalendar.Calendar(calendarEl, {
        themeSystem: 'bootstrap',
        initialView: 'dayGridMonth',
        locale: 'es',
        headerToolbar: {
          left: 'prev,next today',
          center: 'title',
          right: 'dayGridMonth,timeGridWeek,timeGridDay'
        },
        events: '/eventos/json/', // Asegúrate que esta ruta esté disponible
      });
      calendar.render();
      window.calendarInitialized = true;
    }
  }

  // Mostrar vista de control de nómina y ocultar calendario
  function mostrarControlNomina() {
    document.querySelector('.main-content').style.display = 'block';
    document.getElementById('calendario-container').style.display = 'none';
  }


// Validación de nombre y apellido
function capitalizarYValidar(input) {
  input.value = input.value.replace(/[^A-Za-zÁÉÍÓÚáéíóúÑñ\s]/g, '');
  input.value = input.value
    .toLowerCase()
    .split(' ')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

// Validación de cédula
function validarCedula(input) {
  const tipoDocumento = document.getElementById('tipo_documento').value;
  let longitudMaxima = tipoDocumento === 'V' ? 8 : 10;
  input.value = input.value.replace(/\D/g, '');
  if (input.value.length > longitudMaxima) {
    input.value = input.value.slice(0, longitudMaxima);
  }
}