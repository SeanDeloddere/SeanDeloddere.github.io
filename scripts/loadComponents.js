document.addEventListener("DOMContentLoaded", function() {
    console.log('script loaded');

    fetch('/components/nav.html')
        .then(response => {
            if (!response.ok) {
                throw new Error(`Network response was not ok: ${response.statusText}`);
            }
            return response.text();
        })
        .then(data => {
            document.getElementById('nav-placeholder').innerHTML = data;

            const nav = document.querySelector('nav');
            const navContainer = document.querySelector('.nav-container');

            document.addEventListener('mousemove', function(event) {
                if (event.clientY < 50 || window.scrollY === 0 || navContainer.matches(':hover')) {
                    nav.classList.add('show');
                } else {
                    nav.classList.remove('show');
                }
            });

            window.addEventListener('scroll', function() {
                if (window.scrollY === 0) {
                    nav.classList.add('show');
                } else {
                    nav.classList.remove('show');
                }
            });

            nav.addEventListener('mouseenter', function() {
                nav.classList.add('show');
            });
            nav.addEventListener('mouseleave', function() {
                if (window.scrollY !== 0) {
                    nav.classList.remove('show');
                }
            });
        })
        .catch(error => console.error('Error loading navigation:', error));

    fetch('/components/footer.html')
        .then(response => {
            if (!response.ok) {
                throw new Error(`Network response was not ok: ${response.statusText}`);
            }
            return response.text();
        })
        .then(data => {
            document.getElementById('footer-placeholder').innerHTML = data;
        })
        .catch(error => console.error('Error loading footer:', error));
});
