// API URL
const API_URL = 'http://localhost:5000/api';
const BASE_URL = 'http://localhost:5000';

// Devuelve la URL correcta de la imagen del animal, con fallback al placeholder
function getAnimalImage(animal) {
    if (animal.image && animal.image.startsWith('uploads/')) {
        // Imagen subida por el admin → servida por Flask en puerto 5000
        return `${BASE_URL}/${animal.image}`;
    }
    // Sin imagen real o ruta legacy → placeholder SVG según tipo
    const type = (animal.type === 'gato') ? 'gato' : 'perro';
    return `../images/animales/${type}.svg`;
}

// Estado de los filtros
let currentFilter = 'todos';
let currentSize = 'todos';
let searchQuery = '';
let allAnimals = [];

// Inicialización
document.addEventListener('DOMContentLoaded', function() {
    initFilters();
    initSizeFilters();
    initSearch();
    loadAnimals();
});

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

// Cargar animales desde la API
async function loadAnimals() {
    const container = document.getElementById('animalsGrid');
    const noResults = document.getElementById('noResults');

    if (!container) return;

    // Mostrar mensaje de carga
    container.innerHTML = '<p style="text-align: center; padding: 3rem; grid-column: 1/-1;">Cargando animales...</p>';
    container.style.display = 'grid';

    try {
        const response = await fetch(`${API_URL}/animals?status=adoption`);

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
    let filteredAnimals = allAnimals.filter(animal => {
        const typeMatch = currentFilter === 'todos' || animal.type === currentFilter;
        const sizeMatch = currentSize === 'todos' || animal.size === currentSize;
        const searchMatch = searchQuery === '' || animal.name.toLowerCase().includes(searchQuery);
        return typeMatch && sizeMatch && searchMatch;
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

    const typeIcon = animal.type === 'perro' ? 'fa-dog' : 'fa-cat';
    const genderIcon = animal.gender === 'Macho' ? 'fa-mars' : 'fa-venus';
    const typeCapitalized = animal.type.charAt(0).toUpperCase() + animal.type.slice(1);

    const imgSrc = getAnimalImage(animal);
    const type = (animal.type === 'gato') ? 'gato' : 'perro';
    const fallbackSrc = `../images/animales/${type}.svg`;

    card.innerHTML = `
        <img src="${imgSrc}" alt="${animal.name}" class="animal-image"
             onerror="this.onerror=null; this.src='${fallbackSrc}'">
        <div class="animal-info">
            <span class="animal-type">
                <i class="fas ${typeIcon}"></i> ${typeCapitalized}
            </span>
            <h3 class="animal-name">${animal.name}</h3>
            <div class="animal-details">
                <p><i class="fas fa-birthday-cake"></i> ${animal.age || 'Edad desconocida'}</p>
                <p><i class="fas ${genderIcon}"></i> ${animal.gender || 'No especificado'}</p>
                ${animal.size ? `<p><i class="fas fa-ruler-vertical"></i> ${animal.size}</p>` : ''}
            </div>
            <p>${animal.description || 'Sin descripción'}</p>
            <a href="javascript:void(0)" class="btn btn-primary btn-small" onclick="showAnimalDetails(${animal.id})">
                <i class="fas fa-info-circle"></i> Más información
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

        <h2 style="font-size: 2rem; margin-bottom: 1rem; color: #333;">${animal.name}</h2>

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

        <div style="text-align: center;">
            <a href="../pages/contacto.html" class="btn btn-primary btn-large">
                <i class="fas fa-envelope"></i> Contactar para adoptar a ${animal.name}
            </a>
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

// Función para obtener detalles de un animal específico desde la URL
// (ahora se llama directamente desde loadAnimals() tras cargar los datos)
