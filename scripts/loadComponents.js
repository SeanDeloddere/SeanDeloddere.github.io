document.addEventListener("DOMContentLoaded", function() {
    console.log('script loaded')
    function getBaseURL() {
        const currentPath = window.location.pathname;
        const folderList = ['blog_posts'];
        const pathArray = currentPath.split('/');

        console.log('Current Path:', currentPath);
        console.log('Path Array:', pathArray);

        const isInFolderList = pathArray.some(folder => folderList.includes(folder));
        console.log('Is in Folder List:', isInFolderList);

        if (isInFolderList) {
            pathArray.pop(); // Remove the last element (file name)
            pathArray.pop(); // Go one folder up
        } else {
            pathArray.pop(); // Remove the last element (file name)
        }

        console.log('Modified Path Array:', pathArray);

        return window.location.origin + pathArray.join('/') + '/';
    }

    const baseURL = getBaseURL();
    console.log('Base URL:', baseURL);

    fetch(baseURL + 'components/nav.html')
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

            // Adjust links in the navigation bar
            const links = nav.querySelectorAll('a[data-path]');
            links.forEach(link => {
                const relativePath = link.getAttribute('data-path');
                link.href = baseURL + relativePath;
            });

            // Adjust images in the navigation bar
            const images = nav.querySelectorAll('img[data-path]');
            images.forEach(img => {
                const relativePath = img.getAttribute('data-path');
                img.src = baseURL + relativePath;
            });
        })
        .catch(error => console.error('Error loading navigation:', error));

    fetch(baseURL + 'components/footer.html')
        .then(response => {
            if (!response.ok) {
                throw new Error(`Network response was not ok: ${response.statusText}`);
            }
            return response.text();
        })
        .then(data => {
            document.getElementById('footer-placeholder').innerHTML = data;

            const footer = document.querySelector('footer');

            // Adjust links in the footer
            const footerLinks = footer.querySelectorAll('a[data-path]');
            footerLinks.forEach(link => {
                const relativePath = link.getAttribute('data-path');
                link.href = baseURL + relativePath;
            });

            // Adjust images in the footer
            const footerImages = footer.querySelectorAll('img[data-path]');
            footerImages.forEach(img => {
                const relativePath = img.getAttribute('data-path');
                img.src = baseURL + relativePath;
            });
        })
        .catch(error => console.error('Error loading footer:', error));
});
