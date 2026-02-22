/**
 * SYNTHETIC THOUGHTS — Interactive JavaScript
 * Premium dark theme with cinematic scroll animations
 *
 * Features:
 * - GSAP ScrollTrigger with staggered reveals
 * - Cinematic hero entrance
 * - Hero stage boot sequence
 * - Reading progress bar
 * - Header scroll effect
 * - Parallax depth layers
 * - Cursor glow (desktop)
 * - Card spotlight tracking
 * - Magnetic micro-interactions
 * - Konami easter egg
 */

(function () {
    'use strict';

    // ========================================
    // READING PROGRESS BAR
    // ========================================

    function initReadingProgress() {
        const bar = document.createElement('div');
        bar.className = 'reading-progress';
        bar.setAttribute('aria-hidden', 'true');
        document.body.prepend(bar);

        function update() {
            const scrollTop = window.scrollY;
            const docHeight = document.documentElement.scrollHeight - window.innerHeight;
            bar.style.width = docHeight > 0 ? `${Math.min((scrollTop / docHeight) * 100, 100)}%` : '0%';
        }

        window.addEventListener('scroll', update, { passive: true });
        update();
    }

    // ========================================
    // HEADER SCROLL
    // ========================================

    function initHeaderScroll() {
        const header = document.querySelector('.site-header');
        if (!header) return;

        function handleScroll() {
            header.classList.toggle('scrolled', window.scrollY > 40);
        }

        window.addEventListener('scroll', handleScroll, { passive: true });
        handleScroll();
    }

    // ========================================
    // GSAP SCROLL ANIMATIONS
    // ========================================

    function initGSAPAnimations() {
        if (typeof gsap === 'undefined' || typeof ScrollTrigger === 'undefined') {
            initFallbackAnimations();
            return;
        }

        gsap.registerPlugin(ScrollTrigger);

        // --- Hero entrance ---
        const hero = document.querySelector('.hero');
        if (hero) {
            const heroCopy = hero.querySelector('.hero-copy');
            const heroVisual = hero.querySelector('.hero-visual');

            if (heroCopy) {
                const tl = gsap.timeline({ defaults: { ease: 'power3.out' } });

                tl.from(heroCopy.querySelector('.section-title'), {
                    opacity: 0, y: 20, duration: 0.6
                })
                .from(heroCopy.querySelector('h1'), {
                    opacity: 0, y: 40, duration: 0.8
                }, '-=0.3')
                .from(heroCopy.querySelectorAll('p:not(.section-title)'), {
                    opacity: 0, y: 20, duration: 0.6
                }, '-=0.4')
                .from(heroCopy.querySelector('.hero-actions'), {
                    opacity: 0, y: 20, duration: 0.6
                }, '-=0.3');
            }

            if (heroVisual) {
                gsap.from(heroVisual, {
                    opacity: 0,
                    scale: 0.95,
                    y: 30,
                    duration: 1,
                    delay: 0.3,
                    ease: 'power3.out'
                });
            }

            // Parallax on scroll (subtle vertical shift, no opacity fade)
            gsap.to(hero, {
                scrollTrigger: {
                    trigger: hero,
                    start: 'top top',
                    end: 'bottom top',
                    scrub: true
                },
                y: 60,
                ease: 'none'
            });
        }

        // --- Section titles ---
        document.querySelectorAll('.section-title').forEach(title => {
            if (hero && hero.contains(title)) return; // skip hero title
            gsap.from(title, {
                scrollTrigger: { trigger: title, start: 'top 90%', toggleActions: 'play none none none' },
                opacity: 0, x: -20, duration: 0.5, ease: 'power2.out'
            });
        });

        // --- Post cards — staggered reveal ---
        const postCards = document.querySelectorAll('.post-card');
        postCards.forEach((card, i) => {
            gsap.from(card, {
                scrollTrigger: { trigger: card, start: 'top 92%', toggleActions: 'play none none none' },
                opacity: 0,
                y: 50,
                scale: 0.97,
                duration: 0.7,
                delay: i * 0.08,
                ease: 'power3.out'
            });
        });

        // --- Author cards ---
        document.querySelectorAll('.author-card').forEach((card, i) => {
            gsap.from(card, {
                scrollTrigger: { trigger: card, start: 'top 88%', toggleActions: 'play none none none' },
                opacity: 0,
                y: 40,
                x: i % 2 === 0 ? -20 : 20,
                rotation: i % 2 === 0 ? -3 : 3,
                duration: 0.65,
                delay: i * 0.1,
                ease: 'back.out(1.4)'
            });
        });

        // --- About sections ---
        document.querySelectorAll('.about-section').forEach((section, i) => {
            gsap.from(section, {
                scrollTrigger: { trigger: section, start: 'top 85%', toggleActions: 'play none none none' },
                opacity: 0, y: 40, duration: 0.7, delay: i * 0.08, ease: 'power2.out'
            });
        });

        // --- Author profiles ---
        document.querySelectorAll('.author-profile').forEach((profile, i) => {
            gsap.from(profile, {
                scrollTrigger: { trigger: profile, start: 'top 85%', toggleActions: 'play none none none' },
                opacity: 0, x: -40, duration: 0.6, delay: i * 0.12, ease: 'power2.out'
            });
        });

        // --- FAQ items ---
        document.querySelectorAll('.faq-item').forEach((item, i) => {
            gsap.from(item, {
                scrollTrigger: { trigger: item, start: 'top 88%', toggleActions: 'play none none none' },
                opacity: 0, y: 25, duration: 0.5, delay: i * 0.08, ease: 'power2.out'
            });
        });

        // --- Steps ---
        document.querySelectorAll('.step').forEach((step, i) => {
            gsap.from(step, {
                scrollTrigger: { trigger: step, start: 'top 88%', toggleActions: 'play none none none' },
                opacity: 0, x: -30, duration: 0.5, delay: i * 0.08, ease: 'power2.out'
            });
        });

        // --- Archive items ---
        document.querySelectorAll('.archive-item').forEach((item, i) => {
            gsap.from(item, {
                scrollTrigger: { trigger: item, start: 'top 92%', toggleActions: 'play none none none' },
                opacity: 0, x: -25, duration: 0.4, delay: i * 0.06, ease: 'power2.out'
            });
        });

        // --- Stat cards ---
        document.querySelectorAll('.stat-card').forEach((card, i) => {
            gsap.from(card, {
                scrollTrigger: { trigger: card, start: 'top 88%', toggleActions: 'play none none none' },
                opacity: 0, y: 30, scale: 0.92, duration: 0.5, delay: i * 0.1, ease: 'back.out(1.3)'
            });
        });

        // --- Post body elements (article pages) ---
        document.querySelectorAll('.post-body p, .post-body h2, .post-body ul, .post-body blockquote').forEach(el => {
            gsap.from(el, {
                scrollTrigger: { trigger: el, start: 'top 92%', toggleActions: 'play none none none' },
                opacity: 0, y: 18, duration: 0.45, ease: 'power2.out'
            });
        });

        // --- Footer ---
        const footer = document.querySelector('.site-footer');
        if (footer) {
            gsap.from(footer, {
                scrollTrigger: { trigger: footer, start: 'top 95%', toggleActions: 'play none none none' },
                opacity: 0, y: 25, duration: 0.6, ease: 'power2.out'
            });
        }
    }

    // ========================================
    // FALLBACK (no GSAP)
    // ========================================

    function initFallbackAnimations() {
        const els = document.querySelectorAll(
            '.post-card, .author-card, .about-section, .faq-item, .step'
        );
        els.forEach((el, i) => {
            el.classList.add('reveal');
            el.style.transitionDelay = `${i * 0.08}s`;
        });

        const observer = new IntersectionObserver(entries => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('active');
                    observer.unobserve(entry.target);
                }
            });
        }, { rootMargin: '0px 0px -40px 0px', threshold: 0.1 });

        els.forEach(el => observer.observe(el));
    }

    // ========================================
    // HERO STAGE BOOT SEQUENCE
    // ========================================

    function initHeroStageAnimation() {
        const stage = document.querySelector('.hero-stage');
        if (!stage) return;

        const title = stage.querySelector('.stage-title');
        const pulses = stage.querySelectorAll('.stage-loader span');
        if (!title || !pulses.length) return;

        if (typeof gsap === 'undefined') {
            setTimeout(() => stage.classList.add('complete'), 1200);
            return;
        }

        const tl = gsap.timeline({
            defaults: { ease: 'power2.inOut' },
            onComplete: () => stage.classList.add('complete')
        });

        gsap.set(pulses, { scaleY: 0.3, opacity: 0.5 });

        // Phase 1: Neural pulse ignition
        tl.to(pulses, { scaleY: 1, opacity: 1, duration: 0.35, stagger: 0.08 })
          .to(pulses, { scaleY: 0.3, opacity: 0.5, duration: 0.35, stagger: 0.08 })

          // Phase 2: Signal alignment
          .to(title, { opacity: 0, y: -8, duration: 0.25, onComplete: () => title.textContent = 'Signal alignment' }, '+=0.05')
          .to(title, { opacity: 1, y: 0, duration: 0.25 })
          .to(pulses, { scaleY: 0.8, backgroundColor: '#55efc4', duration: 0.25, stagger: 0.04 }, '<')

          // Phase 3: Intent ready
          .to(title, { opacity: 0, y: -8, duration: 0.25, delay: 0.5, onComplete: () => title.textContent = 'Intent ready' })
          .to(title, { opacity: 1, y: 0, duration: 0.25 })
          .to(pulses, {
              scaleY: 1.3,
              backgroundColor: '#ffffff',
              boxShadow: '0 0 12px rgba(255,255,255,0.5)',
              duration: 0.35,
              stagger: 0,
              ease: 'power4.out'
          }, '<');
    }

    // ========================================
    // PARALLAX SHAPES
    // ========================================

    function initParallax() {
        if (typeof gsap === 'undefined') return;

        [
            { selector: '.shape-one', speed: -80 },
            { selector: '.shape-two', speed: -160 },
            { selector: '.shape-three', speed: -40 }
        ].forEach(item => {
            const el = document.querySelector(item.selector);
            if (!el) return;

            gsap.to(el, {
                y: item.speed,
                ease: 'none',
                scrollTrigger: {
                    trigger: document.body,
                    start: 'top top',
                    end: 'bottom bottom',
                    scrub: 1
                }
            });
        });
    }

    // ========================================
    // CURSOR GLOW (desktop only)
    // ========================================

    function initCursorGlow() {
        if ('ontouchstart' in window || typeof gsap === 'undefined') return;

        const glow = document.createElement('div');
        glow.setAttribute('aria-hidden', 'true');
        glow.style.cssText = `
            position: fixed;
            width: 400px;
            height: 400px;
            background: radial-gradient(circle, rgba(0,232,255,0.04) 0%, transparent 65%);
            pointer-events: none;
            z-index: -1;
            transform: translate(-50%, -50%);
            opacity: 0;
        `;
        document.body.appendChild(glow);

        const xTo = gsap.quickTo(glow, 'x', { duration: 0.5, ease: 'power3' });
        const yTo = gsap.quickTo(glow, 'y', { duration: 0.5, ease: 'power3' });

        window.addEventListener('mousemove', e => {
            xTo(e.clientX);
            yTo(e.clientY);
            if (glow.style.opacity === '0') {
                gsap.to(glow, { opacity: 1, duration: 0.4 });
            }
        });

        document.documentElement.addEventListener('mouseleave', () => {
            gsap.to(glow, { opacity: 0, duration: 0.4 });
        });
    }

    // ========================================
    // CARD SPOTLIGHT TRACKING
    // ========================================

    function initCardSpotlight() {
        if ('ontouchstart' in window) return;

        document.querySelectorAll('.post-card').forEach(card => {
            card.addEventListener('mousemove', e => {
                const rect = card.getBoundingClientRect();
                const x = ((e.clientX - rect.left) / rect.width) * 100;
                const y = ((e.clientY - rect.top) / rect.height) * 100;
                card.style.setProperty('--mouse-x', `${x}%`);
                card.style.setProperty('--mouse-y', `${y}%`);
            });
        });
    }

    // ========================================
    // MAGNETIC MICRO-INTERACTIONS
    // ========================================

    function initMagneticButtons() {
        if ('ontouchstart' in window || typeof gsap === 'undefined') return;

        document.querySelectorAll('.read-more, .nav-links a, .author-badge').forEach(el => {
            const xTo = gsap.quickTo(el, 'x', { duration: 0.5, ease: 'elastic.out(1, 0.4)' });
            const yTo = gsap.quickTo(el, 'y', { duration: 0.5, ease: 'elastic.out(1, 0.4)' });

            el.addEventListener('mousemove', e => {
                const rect = el.getBoundingClientRect();
                xTo((e.clientX - rect.left - rect.width / 2) * 0.25);
                yTo((e.clientY - rect.top - rect.height / 2) * 0.25);
            });

            el.addEventListener('mouseleave', () => { xTo(0); yTo(0); });
        });
    }

    // ========================================
    // SMOOTH ANCHOR SCROLL
    // ========================================

    function initSmoothScroll() {
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', function (e) {
                const id = this.getAttribute('href');
                if (id === '#') return;
                const target = document.querySelector(id);
                if (target) {
                    e.preventDefault();
                    target.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }
            });
        });
    }

    // ========================================
    // KONAMI CODE EASTER EGG
    // ========================================

    function initKonamiCode() {
        const seq = [
            'ArrowUp', 'ArrowUp', 'ArrowDown', 'ArrowDown',
            'ArrowLeft', 'ArrowRight', 'ArrowLeft', 'ArrowRight',
            'KeyB', 'KeyA'
        ];
        let idx = 0;

        document.addEventListener('keydown', e => {
            if (e.code === seq[idx]) {
                idx++;
                if (idx === seq.length) {
                    document.body.style.animation = 'hueRotate 2s ease-in-out';
                    setTimeout(() => { document.body.style.animation = ''; }, 2000);
                    idx = 0;
                }
            } else {
                idx = 0;
            }
        });
    }

    // ========================================
    // INIT
    // ========================================

    function init() {
        initReadingProgress();
        initHeaderScroll();
        initSmoothScroll();
        initGSAPAnimations();
        initHeroStageAnimation();
        initParallax();
        initCursorGlow();
        initCardSpotlight();
        initMagneticButtons();
        initKonamiCode();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Easter egg keyframes
    const style = document.createElement('style');
    style.textContent = `
        @keyframes hueRotate {
            0% { filter: hue-rotate(0deg); }
            50% { filter: hue-rotate(180deg); }
            100% { filter: hue-rotate(360deg); }
        }
    `;
    document.head.appendChild(style);

})();
