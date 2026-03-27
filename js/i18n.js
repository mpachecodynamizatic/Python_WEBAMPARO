/**
 * i18n.js — Módulo de traducción ES/VAL
 * Soporta cambio de idioma en toda la web sin necesidad de atributos data-i18n en el HTML.
 * Lee el texto original de los nodos de texto y los sustituye usando una tabla de traducciones.
 * El idioma se aplica a nav links, acciones del header, enlaces del footer y encabezados del footer.
 */
(function () {
    'use strict';

    /** Tabla de traducciones ES → VAL */
    const DICT = {
        val: {
            // Navegación principal
            'Inicio': 'Inici',
            'Adopción': 'Adopció',
            'En adopción': 'En adopció',
            'Adoptados': 'Adoptats',
            'Colabora': 'Col·labora',
            'Voluntariado': 'Voluntariat',
            'Hazte socio': 'Fes-te soci',
            'Acogida': 'Acollida',
            'Padrino/Madrina': 'Padrí/Padrina',
            'Dona': 'Dona',
            'Actualidad': 'Actualitat',
            'Nosotros': 'Nosaltres',
            'Contacto': 'Contacte',
            'Campañas': 'Campanyes',
            'Eventos': 'Esdeveniments',
            'Blog': 'Blog',
            // Acciones del header
            'Adopta': 'Adopta',
            'Voluntariado': 'Voluntariat',
            // Footer — títulos de sección
            'Sobre nosotros': 'Sobre nosaltres',
            'Nos apoyan': 'Ens recolzen',
            'Contacto': 'Contacte',
            'Voluntariado': 'Voluntariat',
            // Footer — enlaces legales
            'Aviso Legal': 'Avís Legal',
            'Política de Privacidad': 'Política de Privadesa',
            'Política de Cookies': 'Política de Galetes',
            // Botones comunes
            'Ver animales': 'Veure animals',
            'Ver todos los animales': 'Veure tots els animals',
            'Ver todas las noticias': 'Veure totes les notícies',
            'Leer más': 'Llegir més',
            'Más información': 'Més informació',
            'Conocer más': 'Conéixer més',
        }
    };

    /**
     * Extrae el texto de los nodos de tipo TEXT_NODE de un elemento,
     * ignorando los nodos de elementos hijos (p. ej. iconos <i>).
     */
    function extractTextNodes(el) {
        const nodes = [];
        for (const node of el.childNodes) {
            if (node.nodeType === Node.TEXT_NODE && node.textContent.trim()) {
                nodes.push(node);
            }
        }
        return nodes;
    }

    /**
     * Traduce un nodo de texto concreto.
     * Conserva el espacio en blanco que lo rodea.
     */
    function translateNode(node, table) {
        const trimmed = node.textContent.trim();
        if (!trimmed) return;

        const translation = table[trimmed];
        if (!translation) return;

        // Guardar original si no está guardado aún
        if (!node._i18nOrig) node._i18nOrig = node.textContent;

        const leading  = node.textContent.match(/^\s*/)[0];
        const trailing = node.textContent.match(/\s*$/)[0];
        node.textContent = leading + translation + trailing;
    }

    /**
     * Restaura el texto original de un nodo.
     */
    function restoreNode(node) {
        if (node._i18nOrig !== undefined) {
            node.textContent = node._i18nOrig;
        }
    }

    /**
     * Aplica las traducciones al idioma indicado ('val' o 'es').
     * Actúa sobre: .main-nav a, .main-actions a, .footer h3, .footer a
     */
    function applyI18n(lang) {
        const isVal = lang === 'val';
        const table = isVal ? DICT.val : null;

        const SCOPE = '.main-nav a, .main-actions a, .footer h3, .footer a';
        document.querySelectorAll(SCOPE).forEach(function (el) {
            const textNodes = extractTextNodes(el);
            textNodes.forEach(function (node) {
                if (isVal) {
                    translateNode(node, table);
                } else {
                    restoreNode(node);
                }
            });
        });

        // Actualizar atributo lang en <html>
        document.documentElement.lang = lang === 'val' ? 'ca' : 'es';
    }

    // Exponer globalmente para que main.js y las páginas sin main.js puedan llamarlo
    window.applyI18n = applyI18n;

    // Aplicar idioma guardado en localStorage al cargar la página
    document.addEventListener('DOMContentLoaded', function () {
        const saved = localStorage.getItem('preferred-language');
        if (saved && saved !== 'es') {
            applyI18n(saved);
        }
    });
})();
