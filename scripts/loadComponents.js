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

            // Add mobile menu functionality
            const menuToggle = document.querySelector('.menu-toggle');
            const navMenu = document.querySelector('.nav-menu');
            
            if (menuToggle) {
                menuToggle.addEventListener('click', function() {
                    navMenu.classList.toggle('active');
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

// Add this JavaScript function
function openCertificateModal(event) {
    event.preventDefault();
    const modal = document.getElementById('certificateModal');
    const closeBtn = modal.querySelector('.close-modal');
    
    modal.style.display = "block";
    
    closeBtn.onclick = function() {
        modal.style.display = "none";
    }
    
    window.onclick = function(event) {
        if (event.target == modal) {
            modal.style.display = "none";
        }
    }
}
