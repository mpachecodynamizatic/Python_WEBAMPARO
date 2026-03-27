// Manejo del formulario de contacto

document.addEventListener('DOMContentLoaded', function() {
    const contactForm = document.getElementById('contactForm');

    if (contactForm) {
        contactForm.addEventListener('submit', handleFormSubmit);

        // Validación en tiempo real
        const inputs = contactForm.querySelectorAll('input, textarea, select');
        inputs.forEach(input => {
            input.addEventListener('blur', function() {
                validateField(this);
            });
        });
    }
});

// Manejar envío del formulario
async function handleFormSubmit(e) {
    e.preventDefault();

    const form = e.target;
    const formMessage = document.getElementById('formMessage');

    // Validar todos los campos
    if (!validateForm(form)) {
        showMessage('Por favor, corrige los errores en el formulario', 'error');
        return;
    }

    // Recopilar datos del formulario
    const formData = {
        name: form.name.value,
        email: form.email.value,
        phone: form.phone.value,
        subject: form.subject.value,
        message: form.message.value,
        privacy: form.privacy.checked
    };

    // Mostrar mensaje de envío
    const submitButton = form.querySelector('button[type="submit"]');
    const originalButtonText = submitButton.innerHTML;
    submitButton.disabled = true;
    submitButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Enviando...';

    try {
        // Simular envío (en producción, esto haría una llamada al backend)
        await sendContactForm(formData);

        // Mostrar mensaje de éxito
        showMessage('¡Mensaje enviado correctamente! Te responderemos lo antes posible.', 'success');

        // Limpiar formulario
        form.reset();

        // Scroll a mensaje
        formMessage.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    } catch (error) {
        showMessage('Hubo un error al enviar el mensaje. Por favor, inténtalo de nuevo.', 'error');
    } finally {
        submitButton.disabled = false;
        submitButton.innerHTML = originalButtonText;
    }
}

// Validar campo individual
function validateField(field) {
    const value = field.value.trim();
    let isValid = true;
    let errorMessage = '';

    // Limpiar errores previos
    field.classList.remove('error');
    const existingError = field.parentElement.querySelector('.error-message');
    if (existingError) {
        existingError.remove();
    }

    // Validar campo obligatorio
    if (field.hasAttribute('required') && !value) {
        isValid = false;
        errorMessage = 'Este campo es obligatorio';
    }

    // Validar email
    if (field.type === 'email' && value) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(value)) {
            isValid = false;
            errorMessage = 'Email no válido';
        }
    }

    // Validar teléfono (formato español básico)
    if (field.type === 'tel' && value) {
        const phoneRegex = /^[+]?[\d\s-]{9,}$/;
        if (!phoneRegex.test(value)) {
            isValid = false;
            errorMessage = 'Teléfono no válido';
        }
    }

    // Validar checkbox de privacidad
    if (field.type === 'checkbox' && field.hasAttribute('required') && !field.checked) {
        isValid = false;
        errorMessage = 'Debes aceptar la política de privacidad';
    }

    // Mostrar error si no es válido
    if (!isValid) {
        field.classList.add('error');
        const error = document.createElement('span');
        error.className = 'error-message';
        error.textContent = errorMessage;
        field.parentElement.appendChild(error);
    }

    return isValid;
}

// Validar formulario completo
function validateForm(form) {
    const requiredFields = form.querySelectorAll('[required]');
    let isValid = true;

    requiredFields.forEach(field => {
        if (!validateField(field)) {
            isValid = false;
        }
    });

    return isValid;
}

// Mostrar mensaje
function showMessage(message, type) {
    const formMessage = document.getElementById('formMessage');

    if (formMessage) {
        formMessage.textContent = message;
        formMessage.className = `form-message ${type}`;
        formMessage.style.display = 'block';

        // Ocultar mensaje después de 5 segundos
        setTimeout(() => {
            formMessage.style.display = 'none';
        }, 5000);
    }
}

// Enviar formulario al backend
async function sendContactForm(formData) {
    const apiBase = document.querySelector('meta[name="api-base"]')?.content || 'http://localhost:5000';
    const response = await fetch(`${apiBase}/api/contact`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
    });

    const result = await response.json();

    if (!response.ok) {
        throw new Error(result.error || 'Error al enviar el formulario');
    }

    return result;
}
