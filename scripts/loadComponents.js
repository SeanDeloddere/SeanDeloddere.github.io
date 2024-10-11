document.addEventListener("DOMContentLoaded", function() {
    // Fetch and load the navigation bar
    fetch('/components/nav.html')
        .then(response => response.text())
        .then(data => {
            document.getElementById('nav-placeholder').innerHTML = data;

            // Add hover effect for the navigation bar
            const nav = document.querySelector('nav');
            const navContainer = document.querySelector('.nav-container');

            document.addEventListener('mousemove', function(event) {
                if (event.clientY < 50 || window.scrollY === 0 || navContainer.matches(':hover')) {
                    nav.classList.add('show');
                } else {
                    nav.classList.remove('show');
                }
            });

            // Ensure nav is visible at the top of the page
            window.addEventListener('scroll', function() {
                if (window.scrollY === 0) {
                    nav.classList.add('show');
                } else {
                    nav.classList.remove('show');
                }
            });

            // Keep nav visible when hovering over it or its dropdowns
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

    // Fetch and load the footer
    fetch('/components/footer.html')
        .then(response => response.text())
        .then(data => {
            document.getElementById('footer-placeholder').innerHTML = data;
        })
        .catch(error => console.error('Error loading footer:', error));
});
