const select = document.getElementById("languages-dropdown")

if (select) {
    select.addEventListener("change", function () {
        const language_code = select.value
        const option = document.getElementById("option-" + language_code)
        if (option && option.dataset.link) {
            window.location.href = option.dataset.link
        }
    })
}
