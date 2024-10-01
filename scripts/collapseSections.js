document.addEventListener("DOMContentLoaded", function() {
    var coll = document.getElementsByClassName("collapsible");
    var toggles = document.getElementsByClassName("toggle-text");

    for (var i = 0; i < coll.length; i++) {
        toggles[i].addEventListener("click", function() {
            var content = this.nextElementSibling;
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
