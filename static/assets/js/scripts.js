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


// ============================================
// 🆕 NUEVO: Funciones para Gestión Comunitaria
// ============================================

// Función para validar formato de cédula venezolana
function validarCedulaVenezolana(input) {
  const value = input.value.trim();
  // Formato: V-12345678 o E-12345678
  const pattern = /^[VE]-\d{6,8}$/;
  
  if (!pattern.test(value)) {
    input.setCustomValidity('Formato inválido. Use V-12345678 o E-12345678');
    input.classList.add('is-invalid');
  } else {
    input.setCustomValidity('');
    input.classList.remove('is-invalid');
  }
}

// 🆕 NUEVO: Función para calcular saldo en tiempo real (finanzas)
function calcularSaldoEnTiempoReal() {
  const ingresosElement = document.getElementById('total-ingresos');
  const egresosElement = document.getElementById('total-egresos');
  const saldoElement = document.getElementById('saldo-actual');
  
  if (!ingresosElement || !egresosElement || !saldoElement) return;
  
  const ingresos = parseFloat(ingresosElement.textContent.replace('Bs. ', '').replace(',', '')) || 0;
  const egresos = parseFloat(egresosElement.textContent.replace('Bs. ', '').replace(',', '')) || 0;
  const saldo = ingresos - egresos;
  
  saldoElement.textContent = `Bs. ${saldo.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ',')}`;
  
  // Actualizar color según saldo
  if (saldo < 0) {
    saldoElement.classList.remove('text-success');
    saldoElement.classList.add('text-danger');
  } else {
    saldoElement.classList.remove('text-danger');
    saldoElement.classList.add('text-success');
  }
}

// 🆕 NUEVO: Función para generar reporte PDF de constancia
function generarConstanciaResidencia(familiaId) {
  Swal.fire({
    title: 'Generando Constancia',
    text: 'Por favor espere...',
    allowOutsideClick: false,
    didOpen: () => {
      Swal.showLoading();
    }
  });
  
  fetch(`/documentacion/constancia/${familiaId}/`)
    .then(response => response.blob())
    .then(blob => {
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `constancia_familia_${familiaId}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      
      Swal.fire({
        icon: 'success',
        title: 'Constancia generada',
        text: 'El documento se ha descargado correctamente'
      });
    })
    .catch(error => {
      Swal.fire({
        icon: 'error',
        title: 'Error',
        text: 'No se pudo generar la constancia'
      });
    });
}

// 🆕 NUEVO: Función para filtrar habitantes por familia
function filtrarHabitantesPorFamilia(familiaId) {
  const tabla = document.getElementById('tabla-habitantes');
  if (!tabla) return;
  
  const filas = tabla.getElementsByTagName('tr');
  
  for (let i = 1; i < filas.length; i++) {
    const fila = filas[i];
    const familiaFila = fila.getAttribute('data-familia-id');
    
    if (familiaId === 'todos' || familiaFila === familiaId) {
      fila.style.display = '';
    } else {
      fila.style.display = 'none';
    }
  }
}

// 🔄 MODIFICADO: Extender función de validación de nombre para caracteres especiales venezolanos
function capitalizarYValidarComunitario(input) {
  // Permitir caracteres venezolanos: áéíóúñüÁÉÍÓÚÑÜ
  input.value = input.value.replace(/[^A-Za-zÁÉÍÓÚáéíóúÑñÜü\s]/g, '');
  input.value = input.value
    .toLowerCase()
    .split(' ')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

// 🆕 NUEVO: Función para actualizar contador de habitantes en tiempo real
function actualizarContadorHabitantes() {
  const checkboxes = document.querySelectorAll('input[name="habitantes"]:checked');
  const contador = document.getElementById('contador-habitantes');
  if (contador) {
    contador.textContent = `${checkboxes.length} habitantes seleccionados`;
  }
}

// 🆕 NUEVO: Función para formatear montos monetarios
function formatearMonto(input) {
  let value = input.value.replace(/[^0-9.]/g, '');
  if (value) {
    const number = parseFloat(value);
    if (!isNaN(number)) {
      input.value = number.toFixed(2);
    }
  }
}

// Inicializar funciones cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', function() {
  // Inicializar validaciones para formularios comunitarios
  const cedulaInputs = document.querySelectorAll('input[data-validar-cedula="true"]');
  cedulaInputs.forEach(input => {
    input.addEventListener('blur', function() {
      validarCedulaVenezolana(this);
    });
  });
  
  // Inicializar filtro de familias si existe
  const filtroFamilia = document.getElementById('filtro-familia');
  if (filtroFamilia) {
    filtroFamilia.addEventListener('change', function() {
      filtrarHabitantesPorFamilia(this.value);
    });
  }
  
  // Inicializar contador de habitantes
  const checkboxesHabitantes = document.querySelectorAll('input[name="habitantes"]');
  checkboxesHabitantes.forEach(checkbox => {
    checkbox.addEventListener('change', actualizarContadorHabitantes);
  });
  
  // Calcular saldo inicial si estamos en la página de finanzas
  if (document.getElementById('saldo-actual')) {
    calcularSaldoEnTiempoReal();
  }
  
  // Formatear montos monetarios
  const montoInputs = document.querySelectorAll('input[data-formatear-monto="true"]');
  montoInputs.forEach(input => {
    input.addEventListener('blur', function() {
      formatearMonto(this);
    });
  });
  
  // 🔄 MODIFICADO: Extender validación de nombres para formularios comunitarios
  const nombreInputsComunitarios = document.querySelectorAll('input[data-validar-nombre-comunitario="true"]');
  nombreInputsComunitarios.forEach(input => {
    input.addEventListener('blur', function() {
      capitalizarYValidarComunitario(this);
    });
  });
});

// 🆕 NUEVO: Función para exportar datos a Excel
function exportarAExcel(tablaId, nombreArchivo) {
  const tabla = document.getElementById(tablaId);
  if (!tabla) return;
  
  let csv = [];
  const filas = tabla.querySelectorAll('tr');
  
  for (let i = 0; i < filas.length; i++) {
    const fila = [];
    const columnas = filas[i].querySelectorAll('td, th');
    
    for (let j = 0; j < columnas.length; j++) {
      // Excluir columnas de acciones
      if (!columnas[j].querySelector('button, form')) {
        fila.push(columnas[j].innerText.replace(/,/g, ''));
      }
    }
    
    csv.push(fila.join(','));
  }
  
  const csvContent = csv.join('\n');
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `${nombreArchivo}_${new Date().toISOString().split('T')[0]}.csv`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}