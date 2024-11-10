document.addEventListener('DOMContentLoaded', function() {
    const galleries = document.querySelectorAll('.splide');
    galleries.forEach(gallery => {
        new Splide(gallery, {
            perPage: 3,
            focus: 'center',
            gap: '1rem',
            breakpoints: {
                768: {
                    perPage: 2,
                },
                576: {
                    perPage: 1,
                }
            }
        }).mount();
    });
}); 