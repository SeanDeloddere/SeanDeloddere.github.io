document.addEventListener("DOMContentLoaded", function() {
    var toggles = document.getElementsByClassName("toggle-text");

    for (var i = 0; i < toggles.length; i++) {
        toggles[i].addEventListener("click", function() {
            var content = this.closest('section').querySelector('.content');
            if (content.style.display === "block") {
                content.style.display = "none";
                this.textContent = "(expand)";
            } else {
                content.style.display = "block";
                this.textContent = "(collapse)";
            }
        });
    }
});
