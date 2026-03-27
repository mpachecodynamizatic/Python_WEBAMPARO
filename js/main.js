// ===================================
// Configuración y variables globales
// ===================================
const API_URL = 'http://localhost:5000/api'; // URL base para el backend

// Traducciones (básicas)
const translations = {
    es: {
        adopt: 'Adopta',
        donate: 'Dona',
        volunteer: 'Voluntariado',
    },
    val: {
        adopt: 'Adopta',
        donate: 'Dona',
        volunteer: 'Voluntariat',
    }
};

// ===================================
// DOM Ready
// ===================================
document.addEventListener('DOMContentLoaded', function() {
    initMobileMenu();
    initScrollToTop();
    initLanguageSelector();
    loadFeaturedAnimals();
    loadLatestNews();
    initDropdowns();
    initAnimations();
});

// ===================================
// Menú móvil
// ===================================
function initMobileMenu() {
    const menuToggle = document.querySelector('.menu-toggle');
    const mainNav = document.querySelector('.main-nav');

    if (!menuToggle || !mainNav) return;

    menuToggle.addEventListener('click', () => {
        mainNav.classList.toggle('active');
        menuToggle.classList.toggle('active');
    });

    // Close menu when clicking outside
    document.addEventListener('click', (e) => {
        if (!menuToggle.contains(e.target) && !mainNav.contains(e.target)) {
            mainNav.classList.remove('active');
            menuToggle.classList.remove('active');
        }
    });
}

// ===================================
// Scroll to top
// ===================================
function initScrollToTop() {
    const scrollBtn = document.getElementById('scrollToTop');

    if (scrollBtn) {
        window.addEventListener('scroll', function() {
            if (window.pageYOffset > 300) {
                scrollBtn.classList.add('visible');
            } else {
                scrollBtn.classList.remove('visible');
            }
        });

        scrollBtn.addEventListener('click', function() {
            window.scrollTo({
                top: 0,
                behavior: 'smooth'
            });
        });
    }
}

// ===================================
// Selector de idioma
// ===================================
function initLanguageSelector() {
    const langButtons = document.querySelectorAll('.lang-btn');

    langButtons.forEach(button => {
        button.addEventListener('click', function() {
            langButtons.forEach(btn => btn.classList.remove('active'));
            this.classList.add('active');
            const lang = this.getAttribute('data-lang');
            changeLanguage(lang);
            localStorage.setItem('preferred-language', lang);
        });
    });

    const savedLang = localStorage.getItem('preferred-language');
    if (savedLang) {
        document.querySelector(`[data-lang="${savedLang}"]`)?.click();
    }
}

function changeLanguage(lang) {
    console.log('Idioma cambiado a:', lang);
}

// ===================================
// Cargar animales destacados desde API
// ===================================
async function loadFeaturedAnimals() {
    const container = document.getElementById('featured-animals');
    if (!container) return;

    container.innerHTML = '<p style="text-align: center; padding: 2rem;">Cargando animales...</p>';

    try {
        const response = await fetch(`${API_URL}/animals?status=adoption`);

        if (!response.ok) {
            throw new Error('Error al cargar animales');
        }

        const data = await response.json();
        const animals = data.animals || [];

        container.innerHTML = '';

        if (animals.length === 0) {
            container.innerHTML = '<p style="text-align: center; color: #666;">No hay animales disponibles en este momento.</p>';
            return;
        }

        // Mostrar solo los primeros 4 animales
        const animalsToShow = animals.slice(0, 4);

        animalsToShow.forEach(animal => {
            const card = createAnimalCard(animal);
            container.appendChild(card);
        });
    } catch (error) {
        console.error('Error al cargar animales:', error);
        container.innerHTML = '<p style="text-align: center; color: #e74c3c;">Error al cargar los animales. Intenta recargar la página.</p>';
    }
}

function createAnimalCard(animal) {
    const card = document.createElement('div');
    card.className = 'animal-card';

    const typeCapitalized = animal.type.charAt(0).toUpperCase() + animal.type.slice(1);
    const animalType = (animal.type === 'gato') ? 'gato' : 'perro';
    const animalImgSrc = (animal.image && animal.image.startsWith('uploads/'))
        ? `http://localhost:5000/${animal.image}`
        : `images/animales/${animalType}.svg`;
    const animalFallback = `images/animales/${animalType}.svg`;

    card.innerHTML = `
        <img src="${animalImgSrc}" alt="${animal.name}" class="animal-image"
             onerror="this.onerror=null; this.src='${animalFallback}'">`
        <div class="animal-info">
            <span class="animal-type">${typeCapitalized}</span>
            <h3 class="animal-name">${animal.name}</h3>
            <div class="animal-details">
                <p><i class="fas fa-birthday-cake"></i> ${animal.age || 'Edad desconocida'}</p>
                <p><i class="fas fa-venus-mars"></i> ${animal.gender || 'No especificado'}</p>
            </div>
            <p>${animal.description || 'Sin descripción'}</p>
            <a href="pages/adopcion.html?id=${animal.id}" class="btn btn-primary btn-small">
                Conocer más
            </a>
        </div>
    `;

    return card;
}

// ===================================
// Cargar noticias desde API
// ===================================
async function loadLatestNews() {
    const container = document.getElementById('latest-news');
    if (!container) return;

    container.innerHTML = '<p style="text-align: center; padding: 2rem;">Cargando noticias...</p>';

    try {
        const response = await fetch(`${API_URL}/news?limit=3`);

        if (!response.ok) {
            throw new Error('Error al cargar noticias');
        }

        const data = await response.json();
        const news = data.news || [];

        container.innerHTML = '';

        if (news.length === 0) {
            container.innerHTML = '<p style="text-align: center; color: #666;">No hay noticias disponibles en este momento.</p>';
            return;
        }

        news.forEach(item => {
            const card = createNewsCard(item);
            container.appendChild(card);
        });
    } catch (error) {
        console.error('Error al cargar noticias:', error);
        container.innerHTML = '<p style="text-align: center; color: #e74c3c;">Error al cargar las noticias. Intenta recargar la página.</p>';
    }
}

function createNewsCard(news) {
    const card = document.createElement('div');
    card.className = 'news-card';

    const formattedDate = formatDate(news.date);

    const newsImgSrc = (news.image && news.image.startsWith('uploads/'))
        ? `http://localhost:5000/${news.image}`
        : 'images/noticia.svg';

    card.innerHTML = `
        <img src="${newsImgSrc}" alt="${news.title}" class="news-image"
             onerror="this.onerror=null; this.src='images/noticia.svg'">
        <div class="news-content">`
            <p class="news-date"><i class="fas fa-calendar"></i> ${formattedDate}</p>
            <h3 class="news-title">${news.title}</h3>
            <p class="news-excerpt">${news.excerpt || news.content.substring(0, 150) + '...'}</p>
            <a href="pages/actualidad.html?id=${news.id}" class="btn btn-outline btn-small">
                Leer más
            </a>
        </div>
    `;

    return card;
}

// ===================================
// Utilidades
// ===================================
function formatDate(dateString) {
    const options = { year: 'numeric', month: 'long', day: 'numeric' };
    const date = new Date(dateString);
    return date.toLocaleDateString('es-ES', options);
}

// ===================================
// Dropdowns (mobile click; desktop via CSS :hover)
// ===================================
function initDropdowns() {
    document.querySelectorAll('.dropdown > a').forEach(link => {
        link.addEventListener('click', (e) => {
            if (window.innerWidth <= 768) {
                e.preventDefault();
                link.closest('.dropdown').classList.toggle('open');
            }
        });
    });
}

// ===================================
// Animaciones al hacer scroll
// ===================================
function initAnimations() {
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -100px 0px'
    };

    const observer = new IntersectionObserver(function(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }
        });
    }, observerOptions);

    const animatedElements = document.querySelectorAll('.service-card, .animal-card, .news-card');

    animatedElements.forEach(element => {
        element.style.opacity = '0';
        element.style.transform = 'translateY(20px)';
        element.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
        observer.observe(element);
    });
}

// ===================================
// Funciones para el CMS (admin)
// ===================================
async function uploadImage(file, type) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('type', type);

    try {
        const response = await fetch(`${API_URL}/upload`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) throw new Error('Error al subir la imagen');

        const data = await response.json();
        return data.url;
    } catch (error) {
        console.error('Error:', error);
        throw error;
    }
}

async function saveAnimal(animalData) {
    try {
        const response = await fetch(`${API_URL}/animals`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(animalData)
        });

        if (!response.ok) throw new Error('Error al guardar el animal');

        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error:', error);
        throw error;
    }
}

async function saveNews(newsData) {
    try {
        const response = await fetch(`${API_URL}/news`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(newsData)
        });

        if (!response.ok) throw new Error('Error al guardar la noticia');

        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error:', error);
        throw error;
    }
}

// ===================================
// Validación de formularios
// ===================================
function validateForm(formId) {
    const form = document.getElementById(formId);
    if (!form) return false;

    const inputs = form.querySelectorAll('input[required], textarea[required], select[required]');
    let isValid = true;

    inputs.forEach(input => {
        if (!input.value.trim()) {
            isValid = false;
            input.classList.add('error');

            let errorMsg = input.nextElementSibling;
            if (!errorMsg || !errorMsg.classList.contains('error-message')) {
                errorMsg = document.createElement('span');
                errorMsg.className = 'error-message';
                errorMsg.textContent = 'Este campo es obligatorio';
                input.parentNode.insertBefore(errorMsg, input.nextSibling);
            }
        } else {
            input.classList.remove('error');
            const errorMsg = input.nextElementSibling;
            if (errorMsg && errorMsg.classList.contains('error-message')) {
                errorMsg.remove();
            }
        }
    });

    const emailInputs = form.querySelectorAll('input[type="email"]');
    emailInputs.forEach(input => {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (input.value && !emailRegex.test(input.value)) {
            isValid = false;
            input.classList.add('error');
        }
    });

    return isValid;
}

// ===================================
// Manejo de cookies
// ===================================
function checkCookieConsent() {
    const consent = localStorage.getItem('cookie-consent');
    if (!consent) {
        showCookieBanner();
    }
}

function showCookieBanner() {
    const banner = document.createElement('div');
    banner.className = 'cookie-banner';
    banner.innerHTML = `
        <div class="cookie-content">
            <p>Utilizamos cookies propias y de terceros para mejorar nuestros servicios.
            <a href="pages/cookies.html">Más información</a></p>
            <button class="btn btn-primary btn-small" onclick="acceptCookies()">Aceptar</button>
        </div>
    `;

    banner.style.cssText = `
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        background: #2C3E50;
        color: white;
        padding: 1rem;
        z-index: 9999;
        box-shadow: 0 -2px 10px rgba(0,0,0,0.2);
    `;

    document.body.appendChild(banner);
}

function acceptCookies() {
    localStorage.setItem('cookie-consent', 'true');
    const banner = document.querySelector('.cookie-banner');
    if (banner) {
        banner.remove();
    }
}

setTimeout(checkCookieConsent, 1000);
