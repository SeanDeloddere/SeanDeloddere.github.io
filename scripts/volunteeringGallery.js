document.addEventListener('DOMContentLoaded', function() {
    const galleries = document.querySelectorAll('.splide');
    galleries.forEach(gallery => {
        const splide = new Splide(gallery, {
            perPage: 3,
            focus: 'center',
            gap: '1rem',
            arrows: false,
            breakpoints: {
                768: {
                    perPage: 2,
                },
                576: {
                    perPage: 1,
                }
            },
            type: 'loop',
            rewind: true
        }).mount();

        const controls = document.createElement('div');
        controls.className = 'splide__arrows';

        const previousButton = document.createElement('button');
        previousButton.className = 'splide__arrow splide__arrow--prev';
        previousButton.type = 'button';
        previousButton.setAttribute('aria-label', 'Previous slide');
        previousButton.textContent = '‹';

        const nextButton = document.createElement('button');
        nextButton.className = 'splide__arrow splide__arrow--next';
        nextButton.type = 'button';
        nextButton.setAttribute('aria-label', 'Next slide');
        nextButton.textContent = '›';

        previousButton.addEventListener('click', () => splide.go('<'));
        nextButton.addEventListener('click', () => splide.go('>'));
        controls.append(previousButton, nextButton);
        gallery.prepend(controls);
    });
}); 