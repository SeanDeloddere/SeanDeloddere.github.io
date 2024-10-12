document.addEventListener("DOMContentLoaded", function() {
    // Determine the base path
    let basePath = '';
    const pathSegments = window.location.pathname.split('/').filter(segment => segment.length > 0);
    if (pathSegments.length > 1) {
        basePath = '../'.repeat(pathSegments.length - 1);
    }

    // Adjust base path for GitHub Pages
    if (window.location.hostname === 'seandeloddere.github.io') {
        basePath = '/Sean-Deloddere-Website/' + basePath;
    }

    // Function to adjust paths for links and images
    function adjustPaths(containerId) {
        document.querySelectorAll(`#${containerId} a, #${containerId} img`).forEach(element => {
            const attr = element.tagName === 'A' ? 'href' : 'src';
            const value = element.getAttribute(attr);
            if (value && !value.startsWith('http') && !value.startsWith('#')) {
                element.setAttribute(attr, basePath + value);
            }
        });
    }

    // Fetch and load the navigation bar
    fetch(basePath + 'components/nav.html')
        .then(response => {
            if (!response.ok) {
                throw new Error(`Network response was not ok: ${response.statusText}`);
            }
            return response.text();
        })
        .then(data => {
            document.getElementById('nav-placeholder').innerHTML = data;
            adjustPaths('nav-placeholder');

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
    fetch(basePath + 'components/footer.html')
        .then(response => {
            if (!response.ok) {
                throw new Error(`Network response was not ok: ${response.statusText}`);
            }
            return response.text();
        })
        .then(data => {
            document.getElementById('footer-placeholder').innerHTML = data;
            adjustPaths('footer-placeholder');
        })
        .catch(error => console.error('Error loading footer:', error));
});
