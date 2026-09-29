document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll(".copy-canonical-url").forEach(function (button) {
    button.addEventListener("click", function () {
      navigator.clipboard.writeText(button.dataset.url).then(function () {
        var original = button.textContent;
        button.textContent = "Copied!";
        setTimeout(function () {
          button.textContent = original;
        }, 1500);
      });
    });
  });
});