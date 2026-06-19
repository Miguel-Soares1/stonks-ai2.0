/**
 * Stonks AI — Landing Page Scripts
 * Particle effect + scroll reveal animations
 */

document.addEventListener('DOMContentLoaded', () => {
    createParticles();
    initScrollReveal();
});

// ── Floating Particles ──────────────────────────────────
function createParticles() {
    const container = document.getElementById('particles');
    if (!container) return;

    const count = 25;
    const fragment = document.createDocumentFragment();

    for (let i = 0; i < count; i++) {
        const particle = document.createElement('div');
        particle.className = 'particle';

        // Random position
        particle.style.left = Math.random() * 100 + '%';
        particle.style.top = Math.random() * 100 + '%';

        // Random size (2-5px)
        const size = 2 + Math.random() * 3;
        particle.style.width = size + 'px';
        particle.style.height = size + 'px';

        // Random animation duration (6-14s) and delay
        particle.style.animationDuration = (6 + Math.random() * 8) + 's';
        particle.style.animationDelay = Math.random() * 8 + 's';

        // Random opacity
        particle.style.opacity = (0.1 + Math.random() * 0.3).toString();

        fragment.appendChild(particle);
    }

    container.appendChild(fragment);
}

// ── Scroll Reveal ───────────────────────────────────────
function initScrollReveal() {
    const elements = document.querySelectorAll(
        '.feature-card, .step, .pricing-card, .privacy-card, .cta-container'
    );

    const observer = new IntersectionObserver(
        (entries) => {
            entries.forEach((entry) => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('visible');
                }
            });
        },
        {
            threshold: 0.15,
            rootMargin: '0px 0px -40px 0px',
        }
    );

    elements.forEach((el) => {
        el.classList.add('reveal');
        observer.observe(el);
    });
}

// ── Smooth parallax on hero glow ────────────────────────
document.addEventListener('mousemove', (e) => {
    const glow = document.querySelector('.hero-glow');
    if (!glow) return;

    const x = (e.clientX / window.innerWidth - 0.5) * 30;
    const y = (e.clientY / window.innerHeight - 0.5) * 30;

    glow.style.transform = `translate(calc(-50% + ${x}px), ${y}px)`;
    glow.style.transition = 'transform 0.8s ease-out';
});

// ── Terminal typing effect ──────────────────────────────
const commands = [
    'stonks quote AAPL -e NYSE',
    'stonks analyze VALE3',
    'stonks compare PETR4 ITUB4',
    'stonks watchlist --add AAPL',
    'stonks chat "O que é P/L?"',
];

let cmdIndex = 0;
let charIndex = 0;
let isDeleting = false;
let typingElement = null;

function initTerminalTyping() {
    typingElement = document.querySelector('.terminal-body .terminal-prompt:last-of-type');
    if (!typingElement) {
        // Fallback: find the text after last prompt
        const body = document.querySelector('.terminal-body');
        if (body) {
            const textNodes = body.childNodes;
            // Simple: just cycle through
        }
        return;
    }
    typeCommand();
}

function typeCommand() {
    const cmd = commands[cmdIndex];

    if (!isDeleting) {
        // Typing
        if (typingElement.nextSibling) {
            typingElement.nextSibling.textContent = cmd.substring(0, charIndex);
        }
        charIndex++;

        if (charIndex > cmd.length) {
            isDeleting = true;
            setTimeout(typeCommand, 2000);
            return;
        }
    } else {
        // Deleting
        charIndex--;
        if (typingElement.nextSibling) {
            typingElement.nextSibling.textContent = cmd.substring(0, charIndex);
        }

        if (charIndex === 0) {
            isDeleting = false;
            cmdIndex = (cmdIndex + 1) % commands.length;
        }
    }

    const speed = isDeleting ? 40 : 80 + Math.random() * 60;
    setTimeout(typeCommand, speed);
}

// Start typing after a delay
setTimeout(initTerminalTyping, 2000);
