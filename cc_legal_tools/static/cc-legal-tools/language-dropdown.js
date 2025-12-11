const select = document.getElementById("languages-dropdown");

select.addEventListener("input", function () {
  const language_code = select.value;
  const option = document.getElementById("option-" + language_code);
  window.location.href = option.dataset.link;
});
