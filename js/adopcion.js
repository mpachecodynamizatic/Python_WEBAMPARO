// API URL leída desde <meta name="api-base"> para soportar distintos entornos
// En producción usa el origin actual, en desarrollo usa localhost
const API_BASE = document.querySelector('meta[name="api-base"]')?.content || window.location.origin;
const API_URL = API_BASE + '/api';
const BASE_URL = API_BASE;

// Devuelve la URL correcta de la imagen del animal, con fallback al placeholder
function getAnimalImage(animal) {
    if (animal.image) {
        // Imagen en base64 (almacenada en BD) → usar directamente
        if (animal.image.startsWith('data:image/')) {
            return animal.image;
        }
        // Imagen en disco → servida por Flask
        if (animal.image.startsWith('uploads/')) {
            return `${BASE_URL}/${animal.image}`;
        }
    }
    // Sin imagen real o ruta legacy → placeholder SVG según tipo
    const type = (animal.type === 'gato') ? 'gato' : 'perro';
    return `../images/animales/${type}.svg`;
}

// Estado de los filtros
let currentStatusTab = 'adoption'; // 'adoption' o 'foster'
let currentFilter = 'todos';
let currentSize = 'todos';
let searchQuery = '';
let allAnimals = [];
let compatFilters = { kids: false, cats: false, dogs: false, apt: false, urgent: false };

// Inicialización
document.addEventListener('DOMContentLoaded', function() {
    initStatusTabs();
    initFilters();
    initSizeFilters();
    initSearch();
    initCompatFilters();
    loadAnimals();
});

// Inicializar tabs de estado (adopción / acogida)
function initStatusTabs() {
    const tabs = document.querySelectorAll('.status-tab-btn');
    tabs.forEach(function(btn) {
        btn.addEventListener('click', function() {
            tabs.forEach(function(t) { t.classList.remove('active'); });
            this.classList.add('active');
            currentStatusTab = this.getAttribute('data-status');
            // Reiniciar filtros de tipo y tamaño al cambiar tab
            currentFilter = 'todos';
            currentSize = 'todos';
            searchQuery = '';
            document.getElementById('searchInput').value = '';
            document.querySelectorAll('.filter-btn').forEach(function(b) { b.classList.remove('active'); });
            document.querySelector('[data-filter="todos"]')?.classList.add('active');
            document.querySelectorAll('.size-btn').forEach(function(b) { b.classList.remove('active'); });
            document.querySelector('[data-size="todos"]')?.classList.add('active');
            loadAnimals();
        });
    });
}

// Inicializar filtros por tipo
function initFilters() {
    const filterButtons = document.querySelectorAll('.filter-btn');

    filterButtons.forEach(button => {
        button.addEventListener('click', function() {
            filterButtons.forEach(btn => btn.classList.remove('active'));
            this.classList.add('active');
            currentFilter = this.getAttribute('data-filter');
            filterAndDisplayAnimals();
        });
    });
}

// Inicializar filtros por tamaño
function initSizeFilters() {
    const sizeButtons = document.querySelectorAll('.size-btn');
    sizeButtons.forEach(button => {
        button.addEventListener('click', function() {
            sizeButtons.forEach(btn => btn.classList.remove('active'));
            this.classList.add('active');
            currentSize = this.getAttribute('data-size');
            filterAndDisplayAnimals();
        });
    });
}

// Inicializar búsqueda
function initSearch() {
    const searchInput = document.getElementById('searchInput');

    if (searchInput) {
        searchInput.addEventListener('input', function() {
            searchQuery = this.value.toLowerCase();
            filterAndDisplayAnimals();
        });
    }
}

function initCompatFilters() {
    const map = {
        'compat-kids':   'kids',
        'compat-cats':   'cats',
        'compat-dogs':   'dogs',
        'compat-apt':    'apt',
        'compat-urgent': 'urgent',
    };
    Object.entries(map).forEach(function([id, key]) {
        const el = document.getElementById(id);
        if (el) {
            el.addEventListener('change', function() {
                compatFilters[key] = this.checked;
                filterAndDisplayAnimals();
            });
        }
    });
}

// Cargar animales desde la API
async function loadAnimals() {
    const container = document.getElementById('animalsGrid');
    const noResults = document.getElementById('noResults');

    if (!container) return;

    // Mostrar mensaje de carga
    container.innerHTML = '<p style="text-align: center; padding: 3rem; grid-column: 1/-1;">Cargando animales...</p>';
    container.style.display = 'grid';

    try {
        const response = await fetch(`${API_URL}/animals?status=${currentStatusTab}`);

        if (!response.ok) {
            throw new Error('Error al cargar animales');
        }

        const data = await response.json();
        allAnimals = data.animals || [];

        // Abrir ficha del animal si viene ?id= en la URL
        const urlParams = new URLSearchParams(window.location.search);
        const animalId = urlParams.get('id');

        filterAndDisplayAnimals();

        if (animalId) {
            const animal = allAnimals.find(a => a.id === parseInt(animalId));
            if (animal) showAnimalDetails(animal.id);
        }
    } catch (error) {
        console.error('Error al cargar animales:', error);
        container.innerHTML = '<p style="text-align: center; padding: 3rem; color: #e74c3c; grid-column: 1/-1;">Error al cargar los animales. Por favor, asegúrate de que el servidor esté corriendo.</p>';
    }
}

// Filtrar y mostrar animales
function filterAndDisplayAnimals() {
    const container = document.getElementById('animalsGrid');
    const noResults = document.getElementById('noResults');
    const resultsCount = document.getElementById('resultsCount');

    if (!container) return;

    // Filtrar animales
    let filteredAnimals = allAnimals.filter(function(animal) {
        const typeMatch   = currentFilter === 'todos' || animal.type === currentFilter;
        const sizeMatch   = currentSize === 'todos' || animal.size === currentSize;
        const searchMatch = searchQuery === '' || animal.name.toLowerCase().includes(searchQuery);
        const kidsMatch   = !compatFilters.kids   || animal.good_with_kids;
        const catsMatch   = !compatFilters.cats   || animal.good_with_cats;
        const dogsMatch   = !compatFilters.dogs   || animal.good_with_dogs;
        const aptMatch    = !compatFilters.apt    || animal.apartment_ok;
        const urgentMatch = !compatFilters.urgent || animal.urgent;
        return typeMatch && sizeMatch && searchMatch && kidsMatch && catsMatch && dogsMatch && aptMatch && urgentMatch;
    });

    // Limpiar contenedor
    container.innerHTML = '';

    // Actualizar contador
    if (resultsCount) {
        const count = filteredAnimals.length;
        resultsCount.textContent = `Mostrando ${count} ${count === 1 ? 'animal' : 'animales'}`;
    }

    // Mostrar/ocultar mensaje de no resultados
    if (filteredAnimals.length === 0) {
        noResults.style.display = 'block';
        container.style.display = 'none';
    } else {
        noResults.style.display = 'none';
        container.style.display = 'grid';

        // Crear tarjetas de animales
        filteredAnimals.forEach(animal => {
            const card = createAnimalCardDetailed(animal);
            container.appendChild(card);
        });

        // Animar entrada
        animateCards();
    }
}

// Crear tarjeta de animal (versión detallada)
function createAnimalCardDetailed(animal) {
    const card = document.createElement('div');
    card.className = 'animal-card';
    card.setAttribute('data-id', animal.id);

    const type = (animal.type === 'gato') ? 'gato' : 'perro';
    const imgSrc = getAnimalImage(animal);
    const fallbackSrc = `../images/animales/${type}.svg`;
    const isReserved = animal.status === 'reserved';
    const photoCount = (animal.photos || []).length;
    const animalSlug = animal.name.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
    const animalUrl  = `/animal/${animal.id}/${animalSlug}`;

    // Compatibility tags (max 3 visible)
    const tags = [];
    if (animal.good_with_kids) tags.push('👶 Niños');
    if (animal.good_with_cats) tags.push('🐱 Gatos');
    if (animal.good_with_dogs) tags.push('🐕 Perros');
    if (animal.apartment_ok)   tags.push('🏠 Piso');
    if (animal.high_energy)    tags.push('⚡ Activo');
    const visibleTags = tags.slice(0, 3);

    // Health badges (max 2 visible)
    const healthTags = [];
    if (animal.vaccinated) healthTags.push('✓ Vacunado');
    if (animal.sterilized) healthTags.push('✓ Esterilizado');
    if (animal.chipped)    healthTags.push('✓ Chip');

    const tagsHtml = visibleTags.map(t =>
        `<span class="animal-compat-tag">${t}</span>`
    ).join('');
    const healthHtml = healthTags.slice(0, 2).map(t =>
        `<span class="animal-health-tag">${t}</span>`
    ).join('');

    card.innerHTML = `
        <div style="position:relative;">
            <img src="${imgSrc}" alt="${animal.name}" class="animal-image"
                 onerror="this.onerror=null;this.src='${fallbackSrc}'">
            ${animal.urgent ? '<span class="animal-urgent-badge">⚠ Urgente</span>' : ''}
            ${isReserved    ? '<span class="animal-reserved-badge"><i class="fas fa-lock"></i> Reservado</span>' : ''}
            ${photoCount > 0 ? `<span class="animal-photo-count">📷 ${photoCount + 1}</span>` : ''}
        </div>
        <div class="animal-info">
            <h3 class="animal-name">${animal.name}</h3>
            <div class="animal-details">
                <p><i class="fas fa-birthday-cake"></i> ${animal.age || 'Edad desconocida'}</p>
                <p><i class="fas fa-ruler-vertical"></i> ${animal.size || '—'}</p>
            </div>
            <div class="animal-tags-row">
                ${tagsHtml}${healthHtml}
            </div>
            <a href="${animalUrl}" class="btn btn-primary btn-small" style="margin-top:.75rem;display:inline-block;">
                <i class="fas fa-info-circle"></i> Ver ficha completa
            </a>
        </div>
    `;

    return card;
}

// Animar tarjetas
function animateCards() {
    const cards = document.querySelectorAll('.animal-card');

    cards.forEach((card, index) => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';

        setTimeout(() => {
            card.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
        }, index * 100);
    });
}

// Mostrar detalles del animal
function showAnimalDetails(animalId) {
    const animal = allAnimals.find(a => a.id === animalId);

    if (!animal) return;

    // Crear modal con información del animal
    const modal = document.createElement('div');
    modal.className = 'animal-modal';
    modal.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0,0,0,0.8);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 10000;
        padding: 2rem;
    `;

    const modalContent = document.createElement('div');
    modalContent.style.cssText = `
        background: white;
        border-radius: 20px;
        max-width: 600px;
        width: 100%;
        max-height: 90vh;
        overflow-y: auto;
        padding: 2rem;
        position: relative;
    `;

    const typeIcon = animal.type === 'perro' ? 'fa-dog' : 'fa-cat';
    const genderIcon = animal.gender === 'Macho' ? 'fa-mars' : 'fa-venus';
    const modalType = (animal.type === 'gato') ? 'gato' : 'perro';
    const modalImgSrc = getAnimalImage(animal);
    const modalFallback = `../images/animales/${modalType}.svg`;

    modalContent.innerHTML = `
        <button onclick="this.closest('.animal-modal').remove()" style="
            position: absolute;
            top: 1rem;
            right: 1rem;
            background: none;
            border: none;
            font-size: 2rem;
            cursor: pointer;
            color: #999;
        ">&times;</button>

        <img src="${modalImgSrc}" alt="${animal.name}" style="
            width: 100%;
            height: 300px;
            object-fit: cover;
            border-radius: 15px;
            margin-bottom: 1.5rem;
        " onerror="this.onerror=null; this.src='${modalFallback}'">

        <div style="display:flex; justify-content:space-between; align-items:start; flex-wrap:wrap; gap:.75rem; margin-bottom:1rem;">
            <h2 style="font-size: 2rem; margin:0; color: #333;">${animal.name}</h2>
            <a href="/animal/${animal.id}/${(animal.name||'').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'')}" target="_blank"
               style="background:#f5f0ea; color:#F4A460; padding:.4rem 1rem; border-radius:8px; text-decoration:none; font-size:.88rem; font-weight:600; white-space:nowrap;">
                <i class="fas fa-external-link-alt"></i> Ver ficha completa
            </a>
        </div>

        <div style="display: flex; gap: 1rem; flex-wrap: wrap; margin-bottom: 1.5rem;">
            <span style="background: #87CEEB; color: white; padding: 0.5rem 1rem; border-radius: 20px;">
                <i class="fas ${typeIcon}"></i> ${animal.type.charAt(0).toUpperCase() + animal.type.slice(1)}
            </span>
            <span style="background: #FFB6C1; color: white; padding: 0.5rem 1rem; border-radius: 20px;">
                <i class="fas fa-birthday-cake"></i> ${animal.age || 'Edad desconocida'}
            </span>
            <span style="background: #F4A460; color: white; padding: 0.5rem 1rem; border-radius: 20px;">
                <i class="fas ${genderIcon}"></i> ${animal.gender || 'No especificado'}
            </span>
            ${animal.size ? `
                <span style="background: #98D8C8; color: white; padding: 0.5rem 1rem; border-radius: 20px;">
                    <i class="fas fa-ruler-vertical"></i> ${animal.size}
                </span>
            ` : ''}
        </div>

        <p style="line-height: 1.8; color: #666; margin-bottom: 2rem;">
            ${animal.description || 'Sin descripción'}
        </p>

        <div style="margin-top: 2rem; border-top: 2px solid #f0f0f0; padding-top: 1.5rem;">
            <h3 style="color: #F4A460; margin-bottom: 1rem;">
                <i class="fas fa-paw"></i> Formulario de pre-adopción
            </h3>
            <p style="color: #666; font-size: 0.9rem; margin-bottom: 1.5rem;">
                Por favor, completa este formulario para que podamos conocerte mejor y asegurarnos de que ${animal.name} encontrará el hogar perfecto.
            </p>
            <form id="adopt-form-${animal.id}">
                <div style="margin-bottom: 1.5rem;">
                    <h4 style="color: #F4A460; font-size: 1rem; margin-bottom: 0.75rem;"><i class="fas fa-user"></i> Información personal</h4>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; margin-bottom: 0.75rem;">
                        <input type="text" id="name-${animal.id}" placeholder="Nombre completo *" required
                               style="padding:0.6rem; border:1px solid #ddd; border-radius:6px; font-size:0.9rem; width:100%; box-sizing:border-box;">
                        <input type="number" id="age-${animal.id}" placeholder="Edad *" required
                               style="padding:0.6rem; border:1px solid #ddd; border-radius:6px; font-size:0.9rem; width:100%; box-sizing:border-box;">
                    </div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; margin-bottom: 0.75rem;">
                        <input type="email" id="email-${animal.id}" placeholder="Email *" required
                               style="padding:0.6rem; border:1px solid #ddd; border-radius:6px; font-size:0.9rem; width:100%; box-sizing:border-box;">
                        <input type="tel" id="phone-${animal.id}" placeholder="Teléfono *" required
                               style="padding:0.6rem; border:1px solid #ddd; border-radius:6px; font-size:0.9rem; width:100%; box-sizing:border-box;">
                    </div>
                    <input type="text" id="address-${animal.id}" placeholder="Dirección *" required
                           style="padding:0.6rem; border:1px solid #ddd; border-radius:6px; font-size:0.9rem; width:100%; box-sizing:border-box; margin-bottom:0.75rem;">
                    <input type="text" id="city-${animal.id}" placeholder="Ciudad *" required
                           style="padding:0.6rem; border:1px solid #ddd; border-radius:6px; font-size:0.9rem; width:100%; box-sizing:border-box;">
                </div>

                <div style="margin-bottom: 1.5rem;">
                    <h4 style="color: #F4A460; font-size: 1rem; margin-bottom: 0.75rem;"><i class="fas fa-home"></i> Situación del hogar</h4>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; margin-bottom: 0.75rem;">
                        <select id="living-${animal.id}" required style="padding:0.6rem; border:1px solid #ddd; border-radius:6px; font-size:0.9rem; width:100%; box-sizing:border-box;">
                            <option value="">Tipo de vivienda *</option>
                            <option value="Casa">Casa</option>
                            <option value="Apartamento">Apartamento</option>
                            <option value="Chalet">Chalet</option>
                        </select>
                        <select id="own-rent-${animal.id}" required style="padding:0.6rem; border:1px solid #ddd; border-radius:6px; font-size:0.9rem; width:100%; box-sizing:border-box;">
                            <option value="">¿Propio o alquilado? *</option>
                            <option value="Propio">Propio</option>
                            <option value="Alquilado">Alquilado</option>
                        </select>
                    </div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem;">
                        <select id="yard-${animal.id}" style="padding:0.6rem; border:1px solid #ddd; border-radius:6px; font-size:0.9rem; width:100%; box-sizing:border-box;">
                            <option value="">¿Tienes jardín/patio?</option>
                            <option value="Sí">Sí</option>
                            <option value="No">No</option>
                        </select>
                        <select id="landlord-${animal.id}" style="padding:0.6rem; border:1px solid #ddd; border-radius:6px; font-size:0.9rem; width:100%; box-sizing:border-box;">
                            <option value="">¿Permiso del propietario? (si aplica)</option>
                            <option value="Sí">Sí</option>
                            <option value="No">No</option>
                            <option value="No aplica">No aplica</option>
                        </select>
                    </div>
                </div>

                <div style="margin-bottom: 1.5rem;">
                    <h4 style="color: #F4A460; font-size: 1rem; margin-bottom: 0.75rem;"><i class="fas fa-users"></i> Composición del hogar</h4>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; margin-bottom: 0.75rem;">
                        <input type="number" id="household-${animal.id}" placeholder="Nº de personas en casa" min="1"
                               style="padding:0.6rem; border:1px solid #ddd; border-radius:6px; font-size:0.9rem; width:100%; box-sizing:border-box;">
                        <select id="children-${animal.id}" style="padding:0.6rem; border:1px solid #ddd; border-radius:6px; font-size:0.9rem; width:100%; box-sizing:border-box;">
                            <option value="">¿Hay niños en casa?</option>
                            <option value="No">No</option>
                            <option value="Sí">Sí</option>
                        </select>
                    </div>
                    <input type="text" id="children-ages-${animal.id}" placeholder="Si hay niños, ¿qué edades tienen?"
                           style="padding:0.6rem; border:1px solid #ddd; border-radius:6px; font-size:0.9rem; width:100%; box-sizing:border-box;">
                </div>

                <div style="margin-bottom: 1.5rem;">
                    <h4 style="color: #F4A460; font-size: 1rem; margin-bottom: 0.75rem;"><i class="fas fa-paw"></i> Experiencia con animales</h4>
                    <textarea id="current-pets-${animal.id}" placeholder="¿Tienes mascotas actualmente? Descríbelas (tipo, edad, esterilizadas, vacunadas...)"
                              style="padding:0.6rem; border:1px solid #ddd; border-radius:6px; font-size:0.9rem; width:100%; box-sizing:border-box; height:60px; resize:vertical; margin-bottom:0.75rem;"></textarea>
                    <textarea id="pet-exp-${animal.id}" placeholder="¿Qué experiencia tienes con animales? ¿Has tenido mascotas antes?"
                              style="padding:0.6rem; border:1px solid #ddd; border-radius:6px; font-size:0.9rem; width:100%; box-sizing:border-box; height:60px; resize:vertical;"></textarea>
                </div>

                <div style="margin-bottom: 1.5rem;">
                    <h4 style="color: #F4A460; font-size: 1rem; margin-bottom: 0.75rem;"><i class="fas fa-briefcase"></i> Estilo de vida</h4>
                    <input type="text" id="work-${animal.id}" placeholder="¿Cuál es tu horario de trabajo/estudio?"
                           style="padding:0.6rem; border:1px solid #ddd; border-radius:6px; font-size:0.9rem; width:100%; box-sizing:border-box; margin-bottom:0.75rem;">
                    <input type="text" id="hours-home-${animal.id}" placeholder="¿Cuántas horas al día estarás en casa?"
                           style="padding:0.6rem; border:1px solid #ddd; border-radius:6px; font-size:0.9rem; width:100%; box-sizing:border-box; margin-bottom:0.75rem;">
                    <textarea id="why-${animal.id}" placeholder="¿Por qué quieres adoptar a ${animal.name}? *" required
                              style="padding:0.6rem; border:1px solid #ddd; border-radius:6px; font-size:0.9rem; width:100%; box-sizing:border-box; height:70px; resize:vertical;"></textarea>
                </div>

                <div style="margin-bottom: 1.5rem;">
                    <h4 style="color: #F4A460; font-size: 1rem; margin-bottom: 0.75rem;"><i class="fas fa-stethoscope"></i> Referencias (opcional)</h4>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; margin-bottom: 0.75rem;">
                        <input type="text" id="vet-name-${animal.id}" placeholder="Nombre de tu veterinario"
                               style="padding:0.6rem; border:1px solid #ddd; border-radius:6px; font-size:0.9rem; width:100%; box-sizing:border-box;">
                        <input type="tel" id="vet-phone-${animal.id}" placeholder="Teléfono del veterinario"
                               style="padding:0.6rem; border:1px solid #ddd; border-radius:6px; font-size:0.9rem; width:100%; box-sizing:border-box;">
                    </div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem;">
                        <input type="text" id="ref-name-${animal.id}" placeholder="Referencia personal (nombre)"
                               style="padding:0.6rem; border:1px solid #ddd; border-radius:6px; font-size:0.9rem; width:100%; box-sizing:border-box;">
                        <input type="tel" id="ref-phone-${animal.id}" placeholder="Teléfono de referencia"
                               style="padding:0.6rem; border:1px solid #ddd; border-radius:6px; font-size:0.9rem; width:100%; box-sizing:border-box;">
                    </div>
                </div>

                <div style="margin-bottom: 1.5rem;">
                    <textarea id="comments-${animal.id}" placeholder="Comentarios adicionales o información que quieras compartir..."
                              style="padding:0.6rem; border:1px solid #ddd; border-radius:6px; font-size:0.9rem; width:100%; box-sizing:border-box; height:70px; resize:vertical;"></textarea>
                </div>

                <button type="button" onclick="submitAdoptRequest(${animal.id}, '${animal.name}')"
                        style="background:#F4A460; color:white; border:none; padding:0.8rem 2rem; border-radius:8px; font-size:1rem; cursor:pointer; font-weight:600; width:100%;">
                    <i class="fas fa-paper-plane"></i> Enviar solicitud de pre-adopción
                </button>
                <p id="adopt-feedback-${animal.id}" style="display:none; margin-top:0.75rem; padding:0.6rem 1rem; border-radius:6px; font-weight:500;"></p>

                <!-- Solicitar visita -->
                <hr style="margin:1.75rem 0 1.25rem; border:none; border-top:2px solid #f0f0f0;">
                <div style="text-align:center; margin-bottom:.75rem;">
                    <p style="color:#888; font-size:.9rem; margin:0 0 .75rem;">
                        ¿Prefieres conocer a <strong>${animal.name}</strong> en persona antes de decidir?
                    </p>
                    <button type="button"
                            onclick="document.getElementById('visit-box-${animal.id}').style.display = document.getElementById('visit-box-${animal.id}').style.display === 'none' ? 'block' : 'none'"
                            style="background:#fff3cd; color:#856404; border:1px solid #f0d070; padding:.6rem 1.5rem; border-radius:8px; font-size:.95rem; cursor:pointer; font-weight:600;">
                        <i class="fas fa-calendar-check"></i> Concertar visita
                    </button>
                </div>
                <div id="visit-box-${animal.id}" style="display:none; background:#fffdf0; border:1px solid #f0d070; border-radius:10px; padding:1.25rem; margin-top:.5rem;">
                    <h4 style="margin:0 0 1rem; color:#856404;"><i class="fas fa-calendar-check"></i> Solicitar visita con ${animal.name}</h4>
                    <div style="display:grid; grid-template-columns:1fr 1fr; gap:.65rem; margin-bottom:.65rem;">
                        <input type="text" id="visit-name-${animal.id}" placeholder="Nombre completo *" required
                               style="padding:.55rem; border:1px solid #ddd; border-radius:6px; font-size:.9rem; box-sizing:border-box;">
                        <input type="email" id="visit-email-${animal.id}" placeholder="Email *" required
                               style="padding:.55rem; border:1px solid #ddd; border-radius:6px; font-size:.9rem; box-sizing:border-box;">
                    </div>
                    <div style="display:grid; grid-template-columns:1fr 1fr; gap:.65rem; margin-bottom:.65rem;">
                        <input type="tel" id="visit-phone-${animal.id}" placeholder="Teléfono"
                               style="padding:.55rem; border:1px solid #ddd; border-radius:6px; font-size:.9rem; box-sizing:border-box;">
                        <input type="date" id="visit-date-${animal.id}"
                               min="${new Date().toISOString().split('T')[0]}"
                               style="padding:.55rem; border:1px solid #ddd; border-radius:6px; font-size:.9rem; box-sizing:border-box; cursor:pointer;">
                    </div>
                    <select id="visit-time-${animal.id}"
                            style="width:100%; padding:.55rem; border:1px solid #ddd; border-radius:6px; font-size:.9rem; margin-bottom:.65rem; box-sizing:border-box;">
                        <option value="">Franja horaria preferida (opcional)</option>
                        <option value="10:00-12:00">Mañana (10:00–12:00)</option>
                        <option value="12:00-14:00">Mediodía (12:00–14:00)</option>
                        <option value="17:00-19:00">Tarde (17:00–19:00)</option>
                        <option value="19:00-20:00">Última hora (19:00–20:00)</option>
                    </select>
                    <input type="text" id="visit-notes-${animal.id}" placeholder="Notas adicionales (opcional)"
                           style="width:100%; padding:.55rem; border:1px solid #ddd; border-radius:6px; font-size:.9rem; margin-bottom:.75rem; box-sizing:border-box;">
                    <button type="button" onclick="submitVisitRequest(${animal.id}, '${animal.name}')"
                            style="background:#F4A460; color:white; border:none; padding:.65rem 1.5rem; border-radius:8px; font-size:.95rem; cursor:pointer; font-weight:600; width:100%;">
                        <i class="fas fa-paper-plane"></i> Enviar solicitud de visita
                    </button>
                    <p id="visit-feedback-${animal.id}" style="display:none; margin-top:.6rem; padding:.6rem 1rem; border-radius:6px; font-weight:500;"></p>
                </div>
            </form>
        </div>
    `;

    modal.appendChild(modalContent);
    document.body.appendChild(modal);

    // Cerrar al hacer clic fuera del modal
    modal.addEventListener('click', function(e) {
        if (e.target === modal) {
            modal.remove();
        }
    });
}

async function submitAdoptRequest(animalId, animalName) {
    // Recoger todos los campos del formulario
    const name = document.getElementById('name-' + animalId).value.trim();
    const email = document.getElementById('email-' + animalId).value.trim();
    const phone = document.getElementById('phone-' + animalId).value.trim();
    const age = document.getElementById('age-' + animalId).value.trim();
    const address = document.getElementById('address-' + animalId).value.trim();
    const city = document.getElementById('city-' + animalId).value.trim();
    const living_situation = document.getElementById('living-' + animalId).value;
    const own_or_rent = document.getElementById('own-rent-' + animalId).value;
    const has_yard = document.getElementById('yard-' + animalId).value;
    const landlord_permission = document.getElementById('landlord-' + animalId).value;
    const household_members = document.getElementById('household-' + animalId).value.trim();
    const has_children = document.getElementById('children-' + animalId).value;
    const children_ages = document.getElementById('children-ages-' + animalId).value.trim();
    const current_pets = document.getElementById('current-pets-' + animalId).value.trim();
    const pet_experience = document.getElementById('pet-exp-' + animalId).value.trim();
    const work_schedule = document.getElementById('work-' + animalId).value.trim();
    const hours_home_per_day = document.getElementById('hours-home-' + animalId).value.trim();
    const why_adopt = document.getElementById('why-' + animalId).value.trim();
    const vet_name = document.getElementById('vet-name-' + animalId).value.trim();
    const vet_phone = document.getElementById('vet-phone-' + animalId).value.trim();
    const reference_name = document.getElementById('ref-name-' + animalId).value.trim();
    const reference_phone = document.getElementById('ref-phone-' + animalId).value.trim();
    const comments = document.getElementById('comments-' + animalId).value.trim();

    const feedback = document.getElementById('adopt-feedback-' + animalId);

    // Validar campos obligatorios
    if (!name || !email || !phone || !age || !address || !city || !living_situation || !own_or_rent || !why_adopt) {
        feedback.style.display = 'block';
        feedback.style.background = '#fdecea';
        feedback.style.color = '#e74c3c';
        feedback.textContent = 'Por favor, completa todos los campos marcados con * (asterisco).';
        return;
    }

    // Validar email
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
        feedback.style.display = 'block';
        feedback.style.background = '#fdecea';
        feedback.style.color = '#e74c3c';
        feedback.textContent = 'Por favor, introduce un email válido.';
        return;
    }

    const btn = feedback.previousElementSibling;
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Enviando...';

    try {
        const res = await fetch(`${API_BASE}/api/adoption-request`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                animal_id: animalId,
                animal_name: animalName,
                name,
                email,
                phone,
                age: age ? parseInt(age) : null,
                address,
                city,
                living_situation,
                own_or_rent,
                has_yard,
                landlord_permission,
                household_members: household_members ? parseInt(household_members) : null,
                has_children,
                children_ages,
                current_pets,
                pet_experience,
                work_schedule,
                hours_home_per_day,
                why_adopt,
                vet_name,
                vet_phone,
                reference_name,
                reference_phone,
                comments,
                message: '' // campo legacy
            })
        });
        const data = await res.json();
        feedback.style.display = 'block';
        if (res.ok) {
            feedback.style.background = '#eafaf1';
            feedback.style.color = '#27ae60';
            feedback.innerHTML = '<i class="fas fa-check-circle"></i> ¡Solicitud enviada con éxito! Nos pondremos en contacto contigo pronto para continuar con el proceso de adopción.';
            btn.style.display = 'none';
            // Scroll al feedback
            feedback.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        } else {
            feedback.style.background = '#fdecea';
            feedback.style.color = '#e74c3c';
            feedback.textContent = data.error || 'Error al enviar la solicitud. Inténtalo de nuevo.';
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-paper-plane"></i> Enviar solicitud de pre-adopción';
        }
    } catch(e) {
        feedback.style.display = 'block';
        feedback.style.background = '#fdecea';
        feedback.style.color = '#e74c3c';
        feedback.textContent = 'Error de conexión. Por favor, verifica tu conexión a internet e inténtalo de nuevo.';
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-paper-plane"></i> Enviar solicitud de pre-adopción';
    }
}

async function submitVisitRequest(animalId, animalName) {
    const name  = document.getElementById('visit-name-'  + animalId).value.trim();
    const email = document.getElementById('visit-email-' + animalId).value.trim();
    const phone = document.getElementById('visit-phone-' + animalId).value.trim();
    const preferred_date = document.getElementById('visit-date-' + animalId).value;
    const preferred_time = document.getElementById('visit-time-' + animalId).value;
    const notes = document.getElementById('visit-notes-' + animalId).value.trim();
    const feedback = document.getElementById('visit-feedback-' + animalId);
    const btn = feedback.previousElementSibling;

    if (!name || !email) {
        feedback.style.cssText = 'display:block; background:#fdecea; color:#e74c3c; margin-top:.6rem; padding:.6rem 1rem; border-radius:6px; font-weight:500;';
        feedback.textContent = 'Por favor, introduce tu nombre y email.';
        return;
    }
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
        feedback.style.cssText = 'display:block; background:#fdecea; color:#e74c3c; margin-top:.6rem; padding:.6rem 1rem; border-radius:6px; font-weight:500;';
        feedback.textContent = 'Email no válido.';
        return;
    }

    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Enviando…';

    try {
        const res = await fetch(`${API_BASE}/api/visit-request`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ animal_id: animalId, animal_name: animalName, name, email, phone, preferred_date, preferred_time, notes })
        });
        const data = await res.json();
        feedback.style.display = 'block';
        if (res.ok) {
            feedback.style.cssText = 'display:block; background:#eafaf1; color:#27ae60; margin-top:.6rem; padding:.6rem 1rem; border-radius:6px; font-weight:500;';
            feedback.innerHTML = '<i class="fas fa-check-circle"></i> ¡Solicitud de visita enviada! Te confirmaremos la cita pronto.';
            btn.style.display = 'none';
            feedback.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        } else {
            feedback.style.cssText = 'display:block; background:#fdecea; color:#e74c3c; margin-top:.6rem; padding:.6rem 1rem; border-radius:6px; font-weight:500;';
            feedback.textContent = data.error || 'Error al enviar. Inténtalo de nuevo.';
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-paper-plane"></i> Enviar solicitud de visita';
        }
    } catch(e) {
        feedback.style.cssText = 'display:block; background:#fdecea; color:#e74c3c; margin-top:.6rem; padding:.6rem 1rem; border-radius:6px; font-weight:500;';
        feedback.textContent = 'Error de conexión. Inténtalo de nuevo.';
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-paper-plane"></i> Enviar solicitud de visita';
    }
}

// Función para obtener detalles de un animal específico desde la URL
// (ahora se llama directamente desde loadAnimals() tras cargar los datos)
