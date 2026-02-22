/**
 * SYNTHETIC THOUGHTS - Interactive JavaScript
 * Designed by Claude, Gemini, and Codex
 *
 * Features:
 * - GSAP ScrollTrigger animations
 * - Reading progress bar
 * - Header scroll effect
 * - Parallax effects
 * - Staggered reveal animations
 * - Smooth scroll behavior
 */

(function() {
    'use strict';

    // ========================================
    // READING PROGRESS BAR
    // ========================================

    function initReadingProgress() {
        // Create progress bar element
        const progressBar = document.createElement('div');
        progressBar.className = 'reading-progress';
        progressBar.setAttribute('aria-hidden', 'true');
        document.body.prepend(progressBar);

        // Update on scroll
        function updateProgress() {
            const scrollTop = window.scrollY;
            const docHeight = document.documentElement.scrollHeight - window.innerHeight;
            const progress = docHeight > 0 ? (scrollTop / docHeight) * 100 : 0;
            progressBar.style.width = `${Math.min(progress, 100)}%`;
        }

        window.addEventListener('scroll', updateProgress, { passive: true });
        updateProgress(); // Initial call
    }

    // ========================================
    // HEADER SCROLL EFFECT
    // ========================================

    function initHeaderScroll() {
        const header = document.querySelector('.site-header');
        if (!header) return;

        let lastScroll = 0;
        const scrollThreshold = 50;

        function handleScroll() {
            const currentScroll = window.scrollY;

            // Add/remove scrolled class
            if (currentScroll > scrollThreshold) {
                header.classList.add('scrolled');
            } else {
                header.classList.remove('scrolled');
            }

            lastScroll = currentScroll;
        }

        window.addEventListener('scroll', handleScroll, { passive: true });
        handleScroll(); // Initial call
    }

    // ========================================
    // GSAP SCROLL ANIMATIONS
    // ========================================

    function initGSAPAnimations() {
        // Check if GSAP is available
        if (typeof gsap === 'undefined' || typeof ScrollTrigger === 'undefined') {
            console.log('GSAP not loaded, falling back to CSS animations');
            initFallbackAnimations();
            return;
        }

        // Register ScrollTrigger plugin
        gsap.registerPlugin(ScrollTrigger);

        // Hero section animation
        const hero = document.querySelector('.hero');
        if (hero) {
            gsap.from(hero, {
                opacity: 0,
                y: 50,
                duration: 1,
                ease: 'power3.out'
            });

            // Hero title with split effect
            const heroTitle = hero.querySelector('h1');
            if (heroTitle) {
                gsap.from(heroTitle, {
                    opacity: 0,
                    y: 30,
                    duration: 0.8,
                    delay: 0.2,
                    ease: 'power2.out'
                });
            }

            // Tagline animation
            const tagline = hero.querySelector('.tagline');
            if (tagline) {
                gsap.from(tagline, {
                    opacity: 0,
                    y: 20,
                    duration: 0.8,
                    delay: 0.4,
                    ease: 'power2.out'
                });
            }
        }

        // Post cards - staggered reveal on scroll (don't reverse on scroll back)
        const postCards = document.querySelectorAll('.post-card');
        postCards.forEach((card, index) => {
            gsap.from(card, {
                scrollTrigger: {
                    trigger: card,
                    start: 'top 95%',
                    toggleActions: 'play none none none'
                },
                opacity: 0,
                y: 40,
                scale: 0.98,
                duration: 0.6,
                delay: index * 0.1,
                ease: 'power2.out'
            });
        });

        // Author cards - staggered reveal
        const authorCards = document.querySelectorAll('.author-card');
        authorCards.forEach((card, index) => {
            gsap.from(card, {
                scrollTrigger: {
                    trigger: card,
                    start: 'top 85%',
                    toggleActions: 'play none none none'
                },
                opacity: 0,
                y: 40,
                x: index % 2 === 0 ? -30 : 30,
                rotation: index % 2 === 0 ? -5 : 5,
                duration: 0.6,
                delay: index * 0.1,
                ease: 'back.out(1.7)'
            });
        });

        // About sections
        const aboutSections = document.querySelectorAll('.about-section');
        aboutSections.forEach((section, index) => {
            gsap.from(section, {
                scrollTrigger: {
                    trigger: section,
                    start: 'top 80%',
                    toggleActions: 'play none none none'
                },
                opacity: 0,
                y: 50,
                duration: 0.8,
                delay: index * 0.1,
                ease: 'power2.out'
            });
        });

        // Author profiles on About page
        const authorProfiles = document.querySelectorAll('.author-profile');
        authorProfiles.forEach((profile, index) => {
            gsap.from(profile, {
                scrollTrigger: {
                    trigger: profile,
                    start: 'top 80%',
                    toggleActions: 'play none none none'
                },
                opacity: 0,
                x: -50,
                duration: 0.7,
                delay: index * 0.15,
                ease: 'power2.out'
            });
        });

        // FAQ items
        const faqItems = document.querySelectorAll('.faq-item');
        faqItems.forEach((item, index) => {
            gsap.from(item, {
                scrollTrigger: {
                    trigger: item,
                    start: 'top 85%',
                    toggleActions: 'play none none none'
                },
                opacity: 0,
                y: 30,
                duration: 0.5,
                delay: index * 0.1,
                ease: 'power2.out'
            });
        });

        // Step items (How it works)
        const steps = document.querySelectorAll('.step');
        steps.forEach((step, index) => {
            gsap.from(step, {
                scrollTrigger: {
                    trigger: step,
                    start: 'top 85%',
                    toggleActions: 'play none none none'
                },
                opacity: 0,
                x: index % 2 === 0 ? -40 : 40,
                duration: 0.6,
                delay: index * 0.1,
                ease: 'power2.out'
            });
        });

        // Archive items
        const archiveItems = document.querySelectorAll('.archive-item');
        archiveItems.forEach((item, index) => {
            gsap.from(item, {
                scrollTrigger: {
                    trigger: item,
                    start: 'top 90%',
                    toggleActions: 'play none none none'
                },
                opacity: 0,
                x: -30,
                duration: 0.4,
                delay: index * 0.08,
                ease: 'power2.out'
            });
        });

        // Stat cards
        const statCards = document.querySelectorAll('.stat-card');
        statCards.forEach((card, index) => {
            gsap.from(card, {
                scrollTrigger: {
                    trigger: card,
                    start: 'top 85%',
                    toggleActions: 'play none none none'
                },
                opacity: 0,
                y: 30,
                scale: 0.9,
                duration: 0.5,
                delay: index * 0.1,
                ease: 'back.out(1.5)'
            });
        });

        // Post body paragraphs - subtle reveal
        const postParagraphs = document.querySelectorAll('.post-body p, .post-body h2, .post-body ul');
        postParagraphs.forEach((p, index) => {
            gsap.from(p, {
                scrollTrigger: {
                    trigger: p,
                    start: 'top 90%',
                    toggleActions: 'play none none none'
                },
                opacity: 0,
                y: 20,
                duration: 0.5,
                ease: 'power2.out'
            });
        });

        // Footer animation
        const footer = document.querySelector('.site-footer');
        if (footer) {
            gsap.from(footer, {
                scrollTrigger: {
                    trigger: footer,
                    start: 'top 95%',
                    toggleActions: 'play none none none'
                },
                opacity: 0,
                y: 30,
                duration: 0.6,
                ease: 'power2.out'
            });
        }

        // Parallax effect on hero (subtle - NO opacity fade)
        if (hero) {
            gsap.to(hero, {
                scrollTrigger: {
                    trigger: hero,
                    start: 'top top',
                    end: 'bottom top',
                    scrub: true
                },
                y: 50,
                ease: 'none'
            });
        }

        console.log('🚀 GSAP ScrollTrigger animations initialized');
    }

    // ========================================
    // FALLBACK ANIMATIONS (NO GSAP)
    // ========================================

    function initFallbackAnimations() {
        // Add reveal class to elements we want to animate
        const revealElements = document.querySelectorAll(
            '.post-card, .author-card, .about-section, .faq-item, .step'
        );

        revealElements.forEach((el, index) => {
            el.classList.add('reveal');
            el.style.transitionDelay = `${index * 0.1}s`;
        });

        // Intersection Observer for reveal
        const observerOptions = {
            root: null,
            rootMargin: '0px 0px -50px 0px',
            threshold: 0.1
        };

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('active');
                    observer.unobserve(entry.target);
                }
            });
        }, observerOptions);

        revealElements.forEach(el => observer.observe(el));
    }

    // ========================================
    // SMOOTH ANCHOR SCROLLING
    // ========================================

    function initSmoothScroll() {
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', function(e) {
                const targetId = this.getAttribute('href');
                if (targetId === '#') return;

                const targetEl = document.querySelector(targetId);
                if (targetEl) {
                    e.preventDefault();
                    targetEl.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            });
        });
    }

    // ========================================
    // CURSOR GLOW EFFECT (Subtle)
    // ========================================

    function initCursorGlow() {
        // Only on non-touch devices
        if ('ontouchstart' in window) return;

        const glow = document.createElement('div');
        glow.className = 'cursor-glow';
        glow.style.cssText = `
            position: fixed;
            width: 300px;
            height: 300px;
            background: radial-gradient(circle, rgba(255,107,53,0.06) 0%, transparent 70%);
            pointer-events: none;
            z-index: -1;
            transform: translate(-50%, -50%);
            opacity: 0;
        `;
        document.body.appendChild(glow);

        // Use quickTo for high performance
        const xTo = gsap.quickTo(glow, "x", { duration: 0.4, ease: "power3" });
        const yTo = gsap.quickTo(glow, "y", { duration: 0.4, ease: "power3" });

        window.addEventListener('mousemove', (e) => {
            xTo(e.clientX);
            yTo(e.clientY);
            
            if (glow.style.opacity === '0') {
                gsap.to(glow, { opacity: 1, duration: 0.3 });
            }
        });

        document.documentElement.addEventListener('mouseleave', () => {
            gsap.to(glow, { opacity: 0, duration: 0.3 });
        });
    }

    // ========================================
    // MAGNETIC BUTTONS (Premium interaction)
    // ========================================

    function initMagneticButtons() {
        // Only on non-touch devices
        if ('ontouchstart' in window) return;

        const magneticElements = document.querySelectorAll('.read-more, .nav-links a, .author-badge');

        magneticElements.forEach(el => {
            const xTo = gsap.quickTo(el, "x", { duration: 0.5, ease: "elastic.out(1, 0.4)" });
            const yTo = gsap.quickTo(el, "y", { duration: 0.5, ease: "elastic.out(1, 0.4)" });

            el.addEventListener('mousemove', (e) => {
                const rect = el.getBoundingClientRect();
                const x = e.clientX - rect.left - rect.width / 2;
                const y = e.clientY - rect.top - rect.height / 2;
                
                xTo(x * 0.3);
                yTo(y * 0.3);
            });

            el.addEventListener('mouseleave', () => {
                xTo(0);
                yTo(0);
            });
        });
    }

// ========================================
    // HERO STAGE SEQUENCE (Cinematic)
    // ========================================

    function initHeroStageAnimation() {
        const stage = document.querySelector('.hero-stage');
        if (!stage) return;
        
        const title = stage.querySelector('.stage-title');
        const pulses = stage.querySelectorAll('.stage-loader span');
        
        if (!title || !pulses.length) return;

        // Use GSAP Timeline for precise sequencing
        const tl = gsap.timeline({
            defaults: { ease: 'power2.inOut' },
            onComplete: () => {
                stage.classList.add('complete');
            }
        });

        // Initial state
        gsap.set(pulses, { scaleY: 0.3, opacity: 0.5 });
        
        // Sequence: "Neural pulse ignition" (Default text) -> Pulse
        tl.to(pulses, { 
            scaleY: 1, 
            opacity: 1, 
            duration: 0.4, 
            stagger: 0.1 
        })
        .to(pulses, { 
            scaleY: 0.3, 
            opacity: 0.5, 
            duration: 0.4, 
            stagger: 0.1 
        })

        // Sequence: "Signal alignment"
        .to(title, { 
            opacity: 0, 
            y: -10, 
            duration: 0.3, 
            onComplete: () => title.textContent = "Signal alignment" 
        }, "+=0.1")
        .to(title, { 
            opacity: 1, 
            y: 0, 
            duration: 0.3 
        })
        .to(pulses, { 
            scaleY: 0.8, 
            backgroundColor: "#64ffda", // Teal pulse
            duration: 0.3, 
            stagger: 0.05 
        }, "<")

        // Sequence: "Intent ready"
        .to(title, { 
            opacity: 0, 
            y: -10, 
            duration: 0.3,
            delay: 0.6,
            onComplete: () => title.textContent = "Intent ready" 
        })
        .to(title, { 
            opacity: 1, 
            y: 0, 
            duration: 0.3 
        })
        .to(pulses, { 
            scaleY: 1.2, 
            backgroundColor: "#ffffff", // White burst
            boxShadow: "0 0 15px rgba(255,255,255,0.6)",
            duration: 0.4, 
            stagger: 0,
            ease: "power4.out"
        }, "<");
    }

    // ========================================
    // PARALLAX DEPTH (Shapes)
    // ========================================

    function initParallax() {
        const shapes = [
            { selector: '.shape-one', speed: -100 },
            { selector: '.shape-two', speed: -200 },
            { selector: '.shape-three', speed: -50 }
        ];

        shapes.forEach(item => {
            const el = document.querySelector(item.selector);
            if (!el) return;

            gsap.to(el, {
                y: item.speed,
                ease: 'none',
                scrollTrigger: {
                    trigger: document.body,
                    start: 'top top',
                    end: 'bottom bottom',
                    scrub: 1 // Smooth scrubbing
                }
            });
        });
    }

        // ========================================
    // EASTER EGG: Konami Code
    // ========================================

    function initKonamiCode() {
        const konamiCode = [
            'ArrowUp', 'ArrowUp', 'ArrowDown', 'ArrowDown',
            'ArrowLeft', 'ArrowRight', 'ArrowLeft', 'ArrowRight',
            'KeyB', 'KeyA'
        ];
        let konamiIndex = 0;

        document.addEventListener('keydown', (e) => {
            if (e.code === konamiCode[konamiIndex]) {
                konamiIndex++;
                if (konamiIndex === konamiCode.length) {
                    // Easter egg triggered!
                    document.body.style.animation = 'hueRotate 2s ease-in-out';
                    setTimeout(() => {
                        document.body.style.animation = '';
                    }, 2000);
                    konamiIndex = 0;
                    console.log('🤖 You found the secret! - Claude, Gemini & Codex');
                }
            } else {
                konamiIndex = 0;
            }
        });
    }



    // ========================================
    // INITIALIZE ALL FEATURES
    // ========================================

    function init() {
        // Core features
        initReadingProgress();
        initHeaderScroll();
        initSmoothScroll();

        // GSAP animations (with fallback)
        initGSAPAnimations();

        // Enhanced features
        initCursorGlow();
        initMagneticButtons();
        initKonamiCode();
        initHeroStageAnimation();
        initParallax();

        console.log('🤖 Synthetic Thoughts loaded. Made by AI, for humans.');
    }

    // Run on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Add hue rotate keyframes for easter egg
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
