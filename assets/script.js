/**
 * GHOST IN THE MODELS - Interactive JavaScript
 * Native motion system with no third-party runtime dependencies.
 */
(function () {
    'use strict';

    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const supportsHover = window.matchMedia('(hover: hover) and (pointer: fine)').matches;

    function initReadingProgress() {
        const bar = document.createElement('div');
        bar.className = 'reading-progress';
        bar.setAttribute('aria-hidden', 'true');
        document.body.prepend(bar);

        function update() {
            const scrollTop = window.scrollY;
            const docHeight = document.documentElement.scrollHeight - window.innerHeight;
            const progress = docHeight > 0 ? Math.min((scrollTop / docHeight) * 100, 100) : 0;
            bar.style.width = `${progress}%`;
        }

        window.addEventListener('scroll', update, { passive: true });
        window.addEventListener('resize', update);
        update();
    }

    function initHeaderScroll() {
        const header = document.querySelector('.site-header');
        if (!header) {
            return;
        }

        function handleScroll() {
            header.classList.toggle('scrolled', window.scrollY > 40);
        }

        window.addEventListener('scroll', handleScroll, { passive: true });
        handleScroll();
    }

    function initRevealAnimations() {
        const groups = [
            ['.hero-copy > *', 0.08],
            ['.hero-visual', 0.12],
            ['.telemetry-card', 0.06],
            ['.post-card', 0.08],
            ['.author-card', 0.08],
            ['.about-section', 0.08],
            ['.author-profile', 0.1],
            ['.faq-item', 0.08],
            ['.step', 0.08],
            ['.archive-item', 0.04],
            ['.tag-section', 0.06],
            ['.stat-card', 0.08],
            ['.dispatch-ledger-row', 0.06],
            ['.overview-strip > div', 0.04],
            ['.post-body p, .post-body h2, .post-body ul, .post-body blockquote, .post-body table, .post-body pre', 0.02],
            ['.site-footer .disclaimer, .site-footer .copyright', 0.04]
        ];

        const seen = new Set();
        const targets = [];

        groups.forEach(([selector, step]) => {
            document.querySelectorAll(selector).forEach((element, index) => {
                if (seen.has(element)) {
                    return;
                }
                seen.add(element);
                element.classList.add('reveal-on-scroll');
                element.style.setProperty('--reveal-delay', `${index * step}s`);
                targets.push(element);
            });
        });

        if (prefersReducedMotion || !('IntersectionObserver' in window)) {
            targets.forEach((element) => element.classList.add('is-visible'));
            return;
        }

        const observer = new IntersectionObserver((entries) => {
            entries.forEach((entry) => {
                if (!entry.isIntersecting) {
                    return;
                }
                entry.target.classList.add('is-visible');
                observer.unobserve(entry.target);
            });
        }, {
            rootMargin: '0px 0px -10% 0px',
            threshold: 0.12
        });

        targets.forEach((element) => observer.observe(element));
    }

    function initHeroStageAnimation() {
        const stage = document.querySelector('.hero-stage');
        if (!stage) {
            return;
        }

        const title = stage.querySelector('.stage-title');
        const pulses = stage.querySelectorAll('.stage-loader span');
        if (!title || pulses.length === 0) {
            return;
        }

        if (prefersReducedMotion) {
            stage.classList.add('complete');
            return;
        }

        const phases = [
            { delay: 450, label: 'Signal alignment' },
            { delay: 1100, label: 'Intent ready' }
        ];

        phases.forEach((phase, index) => {
            window.setTimeout(() => {
                title.textContent = phase.label;
                stage.dataset.phase = String(index + 2);
            }, phase.delay);
        });

        window.setTimeout(() => {
            stage.classList.add('complete');
            stage.dataset.phase = 'done';
        }, 1750);
    }

    function initCursorGlow() {
        if (!supportsHover || prefersReducedMotion) {
            return;
        }

        const glow = document.createElement('div');
        glow.className = 'cursor-glow';
        glow.setAttribute('aria-hidden', 'true');
        document.body.appendChild(glow);

        let currentX = window.innerWidth / 2;
        let currentY = window.innerHeight / 2;
        let targetX = currentX;
        let targetY = currentY;
        let isVisible = false;

        function render() {
            currentX += (targetX - currentX) * 0.12;
            currentY += (targetY - currentY) * 0.12;
            glow.style.transform = `translate3d(${currentX}px, ${currentY}px, 0)`;
            requestAnimationFrame(render);
        }

        window.addEventListener('mousemove', (event) => {
            targetX = event.clientX;
            targetY = event.clientY;
            if (!isVisible) {
                glow.classList.add('is-visible');
                isVisible = true;
            }
        }, { passive: true });

        document.documentElement.addEventListener('mouseleave', () => {
            glow.classList.remove('is-visible');
            isVisible = false;
        });

        render();
    }

    function initCardSpotlight() {
        if (!supportsHover) {
            return;
        }

        document.querySelectorAll('.post-card').forEach((card) => {
            card.addEventListener('mousemove', (event) => {
                const rect = card.getBoundingClientRect();
                const x = ((event.clientX - rect.left) / rect.width) * 100;
                const y = ((event.clientY - rect.top) / rect.height) * 100;
                card.style.setProperty('--mouse-x', `${x}%`);
                card.style.setProperty('--mouse-y', `${y}%`);
            });
        });
    }

    function initMagneticButtons() {
        if (!supportsHover || prefersReducedMotion) {
            return;
        }

        document.querySelectorAll('.read-more, .nav-links a, .author-badge, .btn, .section-link').forEach((element) => {
            element.addEventListener('mousemove', (event) => {
                const rect = element.getBoundingClientRect();
                const x = ((event.clientX - rect.left) - (rect.width / 2)) * 0.18;
                const y = ((event.clientY - rect.top) - (rect.height / 2)) * 0.18;
                element.style.transform = `translate(${x}px, ${y}px)`;
            });

            element.addEventListener('mouseleave', () => {
                element.style.transform = '';
            });
        });
    }

    function initSmoothScroll() {
        document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
            anchor.addEventListener('click', function (event) {
                const id = this.getAttribute('href');
                if (!id || id === '#') {
                    return;
                }
                const target = document.querySelector(id);
                if (!target) {
                    return;
                }
                event.preventDefault();
                target.scrollIntoView({
                    behavior: prefersReducedMotion ? 'auto' : 'smooth',
                    block: 'start'
                });
            });
        });
    }

    function initKonamiCode() {
        const sequence = [
            'ArrowUp', 'ArrowUp', 'ArrowDown', 'ArrowDown',
            'ArrowLeft', 'ArrowRight', 'ArrowLeft', 'ArrowRight',
            'KeyB', 'KeyA'
        ];
        let index = 0;

        document.addEventListener('keydown', (event) => {
            if (event.code === sequence[index]) {
                index += 1;
                if (index === sequence.length) {
                    document.body.classList.add('konami-active');
                    window.setTimeout(() => document.body.classList.remove('konami-active'), 1800);
                    index = 0;
                }
                return;
            }
            index = 0;
        });
    }

    function init() {
        document.documentElement.classList.add('js-ready');
        initReadingProgress();
        initHeaderScroll();
        initSmoothScroll();
        initRevealAnimations();
        initHeroStageAnimation();
        initCursorGlow();
        initCardSpotlight();
        initMagneticButtons();
        initKonamiCode();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init, { once: true });
    } else {
        init();
    }
})();
