/**
 * Certification Carousel
 * Handles carousel functionality for certification groups
 */

document.addEventListener('DOMContentLoaded', function() {
    initializeCarousels();
});

function initializeCarousels() {
    const carouselGroups = document.querySelectorAll('.cert-carousel-group');
    
    carouselGroups.forEach((group) => {
        const track = group.querySelector('.carousel-track');
        const slides = group.querySelectorAll('.carousel-slide');
        const prevBtn = group.querySelector('.carousel-prev');
        const nextBtn = group.querySelector('.carousel-next');
        const dotsContainer = group.querySelector('.carousel-dots');
        const infoPanel = group.querySelector('.carousel-info-panel');
        
        if (!track || slides.length === 0) return;
        
        let currentIndex = 0;
        
        // Create dot indicators
        slides.forEach((_, index) => {
            const dot = document.createElement('button');
            dot.classList.add('carousel-dot');
            dot.setAttribute('aria-label', `Go to certification ${index + 1}`);
            if (index === 0) dot.classList.add('active');
            dot.addEventListener('click', () => goToSlide(index));
            dotsContainer.appendChild(dot);
        });
        
        const dots = dotsContainer.querySelectorAll('.carousel-dot');
        
        // Update the carousel position and info panel
        function updateCarousel() {
            const slideWidth = slides[0].offsetWidth;
            track.style.transform = `translateX(-${currentIndex * slideWidth}px)`;
            
            // Update active states
            slides.forEach((slide, index) => {
                slide.classList.toggle('active', index === currentIndex);
            });
            
            dots.forEach((dot, index) => {
                dot.classList.toggle('active', index === currentIndex);
            });
            
            // Update info panel
            updateInfoPanel(slides[currentIndex]);
            
            // Update button states (optional: disable at ends for non-looping)
            // For infinite feel, we keep all buttons enabled
        }
        
        function updateInfoPanel(slide) {
            const title = slide.dataset.title || '';
            const date = slide.dataset.date || '';
            const description = slide.dataset.description || '';
            const link = slide.dataset.link || '';
            
            const titleEl = infoPanel.querySelector('.info-title');
            const dateEl = infoPanel.querySelector('.info-date');
            const descEl = infoPanel.querySelector('.info-description');
            const linkEl = infoPanel.querySelector('.info-link');
            
            // Add fade effect
            infoPanel.style.opacity = '0';
            
            setTimeout(() => {
                titleEl.textContent = title;
                dateEl.textContent = date;
                descEl.textContent = description;
                
                if (link) {
                    linkEl.href = link;
                    linkEl.classList.remove('hidden');
                } else {
                    linkEl.classList.add('hidden');
                }
                
                infoPanel.style.opacity = '1';
            }, 150);
        }
        
        function goToSlide(index) {
            if (index < 0) {
                currentIndex = slides.length - 1;
            } else if (index >= slides.length) {
                currentIndex = 0;
            } else {
                currentIndex = index;
            }
            updateCarousel();
        }
        
        function nextSlide() {
            goToSlide(currentIndex + 1);
        }
        
        function prevSlide() {
            goToSlide(currentIndex - 1);
        }
        
        // Event listeners
        prevBtn.addEventListener('click', prevSlide);
        nextBtn.addEventListener('click', nextSlide);
        
        // Keyboard navigation
        group.addEventListener('keydown', (e) => {
            if (e.key === 'ArrowLeft') {
                prevSlide();
            } else if (e.key === 'ArrowRight') {
                nextSlide();
            }
        });
        
        // Touch/Swipe support
        let touchStartX = 0;
        let touchEndX = 0;
        
        track.addEventListener('touchstart', (e) => {
            touchStartX = e.changedTouches[0].screenX;
        }, { passive: true });
        
        track.addEventListener('touchend', (e) => {
            touchEndX = e.changedTouches[0].screenX;
            handleSwipe();
        }, { passive: true });
        
        function handleSwipe() {
            const swipeThreshold = 50;
            const diff = touchStartX - touchEndX;
            
            if (Math.abs(diff) > swipeThreshold) {
                if (diff > 0) {
                    nextSlide();
                } else {
                    prevSlide();
                }
            }
        }
        
        // Mouse wheel support (horizontal scrolling)
        group.addEventListener('wheel', (e) => {
            if (Math.abs(e.deltaX) > Math.abs(e.deltaY)) {
                e.preventDefault();
                if (e.deltaX > 0) {
                    nextSlide();
                } else {
                    prevSlide();
                }
            }
        }, { passive: false });
        
        // Handle window resize
        let resizeTimeout;
        window.addEventListener('resize', () => {
            clearTimeout(resizeTimeout);
            resizeTimeout = setTimeout(() => {
                updateCarousel();
            }, 100);
        });
        
        // Initialize first slide
        updateCarousel();
    });
}
