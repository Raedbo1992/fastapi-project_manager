// =========================
// VARIABLES GLOBALES
// =========================
let creditoActual = null;
let creditoId = null;

// =========================
// INICIALIZACIÓN
// =========================
document.addEventListener('DOMContentLoaded', function() {
    // Obtener ID del crédito desde URL
    const urlParams = new URLSearchParams(window.location.search);
    creditoId = parseInt(urlParams.get('id'));

    if (!creditoId) {
        mostrarToast('Error: No se especificó un crédito', 'error');
        setTimeout(() => window.location.href = 'creditos_listado.html', 2000);
        return;
    }

    cargarCredito();
    configurarEventos();
});

// =========================
// CARGAR CRÉDITO
// =========================
function cargarCredito() {
    const creditos = JSON.parse(localStorage.getItem('creditos')) || [];
    creditoActual = creditos.find(c => c.id === creditoId);

    if (!creditoActual) {
        mostrarToast('Error: Crédito no encontrado', 'error');
        setTimeout(() => window.location.href = 'creditos_listado.html', 2000);
        return;
    }

    renderizarInformacion();
    renderizarResumen();
    renderizarProgreso();
    renderizarPagos();
}

// =========================
// RENDERIZAR INFORMACIÓN
// =========================
function renderizarInformacion() {
    // Estado
    const estadoBadge = document.getElementById('estadoCredito');
    estadoBadge.className = `badge-estado ${creditoActual.estado.toLowerCase()}`;
    estadoBadge.innerHTML = `
        <i class="fas fa-circle"></i>
        ${creditoActual.estado}
    `;

    // Información general
    document.getElementById('infoContacto').textContent = creditoActual.contacto;
    document.getElementById('infoMonto').textContent = `$${formatearNumero(creditoActual.monto)}`;
    document.getElementById('infoFechaInicio').textContent = formatearFecha(creditoActual.fechaInicio);
    
    const unidadPlazo = creditoActual.frecuencia === 'Mensual' ? 'meses' : 
                        creditoActual.frecuencia === 'Quincenal' ? 'quincenas' : 'semanas';
    document.getElementById('infoPlazo').textContent = `${creditoActual.plazo} ${unidadPlazo}`;
    
    document.getElementById('infoFrecuencia').textContent = creditoActual.frecuencia;
    document.getElementById('infoCuotaCredito').textContent = `$${formatearNumero(creditoActual.cuotaCredito)}`;
    document.getElementById('infoCuotaSeguro').textContent = `$${formatearNumero(creditoActual.cuotaSeguro)}`;
    
    const cuotaTotal = creditoActual.cuotaCredito + creditoActual.cuotaSeguro;
    document.getElementById('infoCuotaTotal').textContent = `$${formatearNumero(cuotaTotal)}`;

    // Configurar botón editar
    document.getElementById('btnEditar').href = `form_creditos.html?id=${creditoId}`;
}

// =========================
// RENDERIZAR RESUMEN
// =========================
function renderizarResumen() {
    const totalPagado = creditoActual.monto - creditoActual.saldo;
    const porcentaje = ((totalPagado / creditoActual.monto) * 100).toFixed(1);

    document.getElementById('resumenTotal').textContent = `$${formatearNumero(creditoActual.monto)}`;
    document.getElementById('resumenPagado').textContent = `$${formatearNumero(totalPagado)}`;
    document.getElementById('resumenSaldo').textContent = `$${formatearNumero(creditoActual.saldo)}`;
    document.getElementById('resumenProgreso').textContent = `${porcentaje}%`;
}

// =========================
// RENDERIZAR PROGRESO
// =========================
function renderizarProgreso() {
    const totalPagado = creditoActual.monto - creditoActual.saldo;
    const porcentaje = ((totalPagado / creditoActual.monto) * 100).toFixed(1);

    document.getElementById('progresoTexto').textContent = `${porcentaje}%`;
    
    const progresoFill = document.getElementById('progresoFill');
    setTimeout(() => {
        progresoFill.style.width = `${porcentaje}%`;
    }, 100);
}

// =========================
// RENDERIZAR PAGOS
// =========================
function renderizarPagos() {
    const tbody = document.getElementById('pagosTBody');
    const pagos = creditoActual.pagosRealizados || [];

    if (pagos.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="5" class="sin-pagos">
                    <i class="fas fa-inbox"></i>
                    <p>No hay pagos registrados</p>
                    <small>Realiza el primer pago para comenzar</small>
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = pagos.map((pago, index) => `
        <tr>
            <td class="pago-numero">#${index + 1}</td>
            <td class="pago-fecha">${formatearFecha(pago.fecha)}</td>
            <td class="pago-monto">$${formatearNumero(pago.monto)}</td>
            <td>
                <span class="pago-comprobante">
                    <i class="fas fa-receipt"></i>
                    ${pago.comprobante}
                </span>
            </td>
            <td>
                <button class="btn-delete-pago" onclick="eliminarPago(${pago.id})">
                    <i class="fas fa-trash"></i>
                    Eliminar
                </button>
            </td>
        </tr>
    `).join('');
}

// =========================
// CONFIGURAR EVENTOS
// =========================
function configurarEventos() {
    // Botón abrir modal
    document.getElementById('btnNuevoPago').addEventListener('click', function(e) {
        e.preventDefault();
        abrirModalPago();
    });

    // Botones cerrar modal
    document.getElementById('btnCerrarModal').addEventListener('click', cerrarModalPago);
    document.getElementById('btnCancelarPago').addEventListener('click', cerrarModalPago);

    // Cerrar modal al hacer click fuera
    document.getElementById('modalPago').addEventListener('click', function(e) {
        if (e.target === this) {
            cerrarModalPago();
        }
    });

    // Formulario de pago
    document.getElementById('formPago').addEventListener('submit', guardarPago);

    // Establecer fecha actual por defecto
    const hoy = new Date().toISOString().split('T')[0];
    document.getElementById('fechaPago').value = hoy;
}

// =========================
// ABRIR MODAL PAGO
// =========================
function abrirModalPago() {
    document.getElementById('saldoPendiente').textContent = formatearNumero(creditoActual.saldo);
    document.getElementById('modalPago').classList.add('active');
    
    // Limpiar formulario
    document.getElementById('formPago').reset();
    const hoy = new Date().toISOString().split('T')[0];
    document.getElementById('fechaPago').value = hoy;
}

// =========================
// CERRAR MODAL PAGO
// =========================
function cerrarModalPago() {
    document.getElementById('modalPago').classList.remove('active');
}

// =========================
// GUARDAR PAGO
// =========================
function guardarPago(e) {
    e.preventDefault();

    const fecha = document.getElementById('fechaPago').value;
    const monto = parseFloat(document.getElementById('montoPago').value);
    const comprobante = document.getElementById('comprobantePago').value.trim();

    // Validaciones
    if (!fecha || !monto || !comprobante) {
        mostrarToast('Por favor completa todos los campos', 'error');
        return;
    }

    if (monto <= 0) {
        mostrarToast('El monto debe ser mayor a cero', 'error');
        return;
    }

    if (monto > creditoActual.saldo) {
        mostrarToast('El monto no puede ser mayor al saldo pendiente', 'error');
        return;
    }

    // Crear nuevo pago
    const nuevoPago = {
        id: Date.now(),
        fecha: fecha,
        monto: monto,
        comprobante: comprobante
    };

    // Agregar pago al crédito
    if (!creditoActual.pagosRealizados) {
        creditoActual.pagosRealizados = [];
    }
    creditoActual.pagosRealizados.push(nuevoPago);

    // Actualizar saldo
    creditoActual.saldo -= monto;

    // Actualizar estado si se pagó todo
    if (creditoActual.saldo <= 0) {
        creditoActual.saldo = 0;
        creditoActual.estado = 'Pagado';
    }

    // Guardar en localStorage
    actualizarCreditoEnStorage();

    // Actualizar vista
    renderizarInformacion();
    renderizarResumen();
    renderizarProgreso();
    renderizarPagos();

    // Cerrar modal y mostrar mensaje
    cerrarModalPago();
    mostrarToast('Pago registrado exitosamente', 'success');
}

// =========================
// ELIMINAR PAGO
// =========================
function eliminarPago(pagoId) {
    if (!confirm('¿Estás seguro de que deseas eliminar este pago?')) {
        return;
    }

    // Encontrar el pago
    const pago = creditoActual.pagosRealizados.find(p => p.id === pagoId);
    if (!pago) return;

    // Restaurar saldo
    creditoActual.saldo += pago.monto;

    // Si el crédito estaba pagado, volver a activo
    if (creditoActual.estado === 'Pagado') {
        creditoActual.estado = 'Activo';
    }

    // Eliminar pago del array
    creditoActual.pagosRealizados = creditoActual.pagosRealizados.filter(p => p.id !== pagoId);

    // Guardar en localStorage
    actualizarCreditoEnStorage();

    // Actualizar vista
    renderizarInformacion();
    renderizarResumen();
    renderizarProgreso();
    renderizarPagos();

    mostrarToast('Pago eliminado correctamente', 'success');
}

// =========================
// ACTUALIZAR CRÉDITO EN STORAGE
// =========================
function actualizarCreditoEnStorage() {
    let creditos = JSON.parse(localStorage.getItem('creditos')) || [];
    const index = creditos.findIndex(c => c.id === creditoId);
    
    if (index !== -1) {
        creditos[index] = creditoActual;
        localStorage.setItem('creditos', JSON.stringify(creditos));
    }
}

// =========================
// UTILIDADES
// =========================
function formatearNumero(numero) {
    return new Intl.NumberFormat('es-CO', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(numero);
}

function formatearFecha(fecha) {
    const [año, mes, dia] = fecha.split('-');
    return `${dia}/${mes}/${año}`;
}

function mostrarToast(mensaje, tipo = 'success') {
    const toast = document.getElementById('toast');
    const toastMessage = document.getElementById('toastMessage');
    
    toast.className = `toast ${tipo}`;
    toastMessage.textContent = mensaje;
    toast.classList.add('show');
    
    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}