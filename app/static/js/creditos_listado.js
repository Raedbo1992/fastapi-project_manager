// =========================
// DATOS DE EJEMPLO (simula base de datos)
// =========================
let creditos = [
    {
        id: 1,
        contacto: "Juan Pérez",
        monto: 5000.00,
        cuotaCredito: 250.00,
        cuotaSeguro: 50.00,
        saldo: 3500.00,
        estado: "Activo",
        frecuencia: "Mensual",
        fechaInicio: "2024-01-15",
        plazo: 24,
        pagosRealizados: [
            { id: 1, fecha: "2024-02-15", monto: 300.00, comprobante: "COMP-001" },
            { id: 2, fecha: "2024-03-15", monto: 300.00, comprobante: "COMP-002" },
            { id: 3, fecha: "2024-04-15", monto: 300.00, comprobante: "COMP-003" },
            { id: 4, fecha: "2024-05-15", monto: 300.00, comprobante: "COMP-004" },
            { id: 5, fecha: "2024-06-15", monto: 300.00, comprobante: "COMP-005" }
        ]
    },
    {
        id: 2,
        contacto: "María González",
        monto: 10000.00,
        cuotaCredito: 500.00,
        cuotaSeguro: 100.00,
        saldo: 0.00,
        estado: "Pagado",
        frecuencia: "Quincenal",
        fechaInicio: "2023-06-01",
        plazo: 20,
        pagosRealizados: [
            { id: 1, fecha: "2023-06-15", monto: 600.00, comprobante: "COMP-006" },
            { id: 2, fecha: "2023-07-01", monto: 600.00, comprobante: "COMP-007" }
        ]
    },
    {
        id: 3,
        contacto: "Carlos Rodríguez",
        monto: 3000.00,
        cuotaCredito: 150.00,
        cuotaSeguro: 30.00,
        saldo: 2100.00,
        estado: "Vencido",
        frecuencia: "Mensual",
        fechaInicio: "2024-02-20",
        plazo: 18,
        pagosRealizados: [
            { id: 1, fecha: "2024-03-20", monto: 180.00, comprobante: "COMP-008" },
            { id: 2, fecha: "2024-04-20", monto: 180.00, comprobante: "COMP-009" },
            { id: 3, fecha: "2024-05-20", monto: 180.00, comprobante: "COMP-010" },
            { id: 4, fecha: "2024-06-20", monto: 180.00, comprobante: "COMP-011" },
            { id: 5, fecha: "2024-07-20", monto: 180.00, comprobante: "COMP-012" }
        ]
    }
];

// Guardar en localStorage
function guardarCreditos() {
    localStorage.setItem('creditos', JSON.stringify(creditos));
}

// Cargar de localStorage
function cargarCreditos() {
    const stored = localStorage.getItem('creditos');
    if (stored) {
        creditos = JSON.parse(stored);
    } else {
        guardarCreditos();
    }
}

// =========================
// VARIABLES GLOBALES
// =========================
let creditosFiltrados = [];
const itemsPorPagina = 10;
let paginaActual = 1;

// =========================
// INICIALIZACIÓN
// =========================
document.addEventListener('DOMContentLoaded', function() {
    cargarCreditos();
    aplicarFiltros();
    configurarEventos();
    verificarScroll();
});

// =========================
// CONFIGURAR EVENTOS
// =========================
function configurarEventos() {
    // Filtros
    document.getElementById('filtroEstado').addEventListener('change', aplicarFiltros);
    document.getElementById('filtroFrecuencia').addEventListener('change', aplicarFiltros);

    // Scroll hint
    const tablaScroll = document.getElementById('tablaScroll');
    const scrollHint = document.getElementById('scrollHint');

    tablaScroll.addEventListener('scroll', function() {
        if (this.scrollLeft > 50) {
            scrollHint.style.opacity = '0';
            setTimeout(() => scrollHint.style.display = 'none', 300);
        }
    });

    scrollHint.addEventListener('click', function() {
        tablaScroll.scrollTo({ left: 200, behavior: 'smooth' });
    });

    window.addEventListener('resize', verificarScroll);
}

// =========================
// VERIFICAR SI NECESITA SCROLL
// =========================
function verificarScroll() {
    const tablaScroll = document.getElementById('tablaScroll');
    const scrollHint = document.getElementById('scrollHint');
    
    if (tablaScroll.scrollWidth > tablaScroll.clientWidth) {
        scrollHint.style.display = 'flex';
    } else {
        scrollHint.style.display = 'none';
    }
}

// =========================
// APLICAR FILTROS
// =========================
function aplicarFiltros() {
    const estado = document.getElementById('filtroEstado').value;
    const frecuencia = document.getElementById('filtroFrecuencia').value;

    creditosFiltrados = creditos.filter(credito => {
        let cumpleEstado = !estado || credito.estado === estado;
        let cumpleFrecuencia = !frecuencia || credito.frecuencia === frecuencia;
        return cumpleEstado && cumpleFrecuencia;
    });

    paginaActual = 1;
    renderizarTabla();
    renderizarPaginacion();
}

// =========================
// RENDERIZAR TABLA
// =========================
function renderizarTabla() {
    const tbody = document.getElementById('creditosTableBody');
    const inicio = (paginaActual - 1) * itemsPorPagina;
    const fin = inicio + itemsPorPagina;
    const creditosPagina = creditosFiltrados.slice(inicio, fin);

    if (creditosPagina.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" class="no-data">
                    <i class="fas fa-hand-holding-usd"></i>
                    <div>No hay créditos registrados</div>
                    <div class="no-data-sub">Comienza creando un nuevo crédito</div>
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = creditosPagina.map(credito => {
        const cuotaTotal = credito.cuotaCredito + credito.cuotaSeguro;
        const pagado = credito.monto - credito.saldo;
        const porcentaje = ((pagado / credito.monto) * 100).toFixed(1);
        
        return `
            <tr>
                <td class="sticky-col">
                    <div class="contacto-content">
                        <div class="nombre-contacto">
                            <span class="nombre-text">${credito.contacto}</span>
                        </div>
                    </div>
                </td>
                <td>
                    <div class="credito-content">
                        <div class="credito-monto">$${formatearNumero(credito.monto)}</div>
                        <div class="credito-plazo">${credito.plazo} ${credito.frecuencia === 'Mensual' ? 'meses' : credito.frecuencia === 'Quincenal' ? 'quincenas' : 'semanas'}</div>
                    </div>
                </td>
                <td>
                    <div class="cuota-total">$${formatearNumero(cuotaTotal)}</div>
                </td>
                <td>
                    <div class="saldo-content">
                        <div class="saldo-monto ${credito.saldo > 0 ? 'positivo' : 'cero'}">
                            $${formatearNumero(credito.saldo)}
                        </div>
                        <div class="saldo-progreso">${porcentaje}% pagado</div>
                    </div>
                </td>
                <td>
                    <span class="badge-estado ${credito.estado.toLowerCase()}">
                        <i class="fas fa-circle"></i>
                        ${credito.estado}
                    </span>
                </td>
                <td>
                    <div class="fecha-content">
                        <i class="fas fa-calendar-alt"></i>
                        <span class="fecha-text">${formatearFecha(credito.fechaInicio)}</span>
                    </div>
                </td>
                <td class="sticky-actions acciones-cell">
                    <div class="acciones">
                        <a href="credito_detalle.html?id=${credito.id}" class="btn-icon view" title="Ver detalle">
                            <i class="fas fa-eye"></i>
                        </a>
                        <a href="form_creditos.html?id=${credito.id}" class="btn-icon edit" title="Editar">
                            <i class="fas fa-edit"></i>
                        </a>
                        <button class="btn-icon delete" onclick="confirmarEliminar(${credito.id})" title="Eliminar">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}

// =========================
// RENDERIZAR PAGINACIÓN
// =========================
function renderizarPaginacion() {
    const totalPaginas = Math.ceil(creditosFiltrados.length / itemsPorPagina);
    const paginacion = document.getElementById('paginacion');

    if (totalPaginas <= 1) {
        paginacion.innerHTML = '';
        return;
    }

    let html = `
        <a href="#" class="pag-btn pag-nav ${paginaActual === 1 ? 'disabled' : ''}" onclick="cambiarPagina(${paginaActual - 1}); return false;">
            <i class="fas fa-chevron-left"></i>
        </a>
        <div class="pag-info-mobile">${paginaActual} / ${totalPaginas}</div>
        <div class="pag-numbers">
    `;

    if (totalPaginas <= 7) {
        for (let i = 1; i <= totalPaginas; i++) {
            html += `<a href="#" class="pag-btn ${i === paginaActual ? 'active' : ''}" onclick="cambiarPagina(${i}); return false;">${i}</a>`;
        }
    } else {
        html += `<a href="#" class="pag-btn ${1 === paginaActual ? 'active' : ''}" onclick="cambiarPagina(1); return false;">1</a>`;
        
        if (paginaActual > 3) html += `<span class="pag-dots">...</span>`;
        
        for (let i = Math.max(2, paginaActual - 1); i <= Math.min(totalPaginas - 1, paginaActual + 1); i++) {
            html += `<a href="#" class="pag-btn ${i === paginaActual ? 'active' : ''}" onclick="cambiarPagina(${i}); return false;">${i}</a>`;
        }
        
        if (paginaActual < totalPaginas - 2) html += `<span class="pag-dots">...</span>`;
        
        html += `<a href="#" class="pag-btn ${totalPaginas === paginaActual ? 'active' : ''}" onclick="cambiarPagina(${totalPaginas}); return false;">${totalPaginas}</a>`;
    }

    html += `
        </div>
        <a href="#" class="pag-btn pag-nav ${paginaActual === totalPaginas ? 'disabled' : ''}" onclick="cambiarPagina(${paginaActual + 1}); return false;">
            <i class="fas fa-chevron-right"></i>
        </a>
    `;

    paginacion.innerHTML = html;
}

// =========================
// CAMBIAR PÁGINA
// =========================
function cambiarPagina(nuevaPagina) {
    const totalPaginas = Math.ceil(creditosFiltrados.length / itemsPorPagina);
    if (nuevaPagina < 1 || nuevaPagina > totalPaginas) return;
    
    paginaActual = nuevaPagina;
    renderizarTabla();
    renderizarPaginacion();
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// =========================
// CONFIRMAR ELIMINAR
// =========================
function confirmarEliminar(id) {
    if (confirm('¿Estás seguro de que deseas eliminar este crédito?')) {
        eliminarCredito(id);
    }
}

function eliminarCredito(id) {
    creditos = creditos.filter(c => c.id !== id);
    guardarCreditos();
    aplicarFiltros();
    mostrarToast('Crédito eliminado correctamente', 'success');
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
    const toast = document.getElementById('copyToast');
    const toastMessage = document.getElementById('toastMessage');
    
    toastMessage.textContent = mensaje;
    toast.className = 'copy-toast show';
    
    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}