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

            // Add mobile menu toggle functionality
            const menuToggle = document.querySelector('.menu-toggle');
            if (menuToggle) {
                menuToggle.addEventListener('click', function() {
                    document.querySelector('.nav-menu').classList.toggle('active');
                });
            }
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
