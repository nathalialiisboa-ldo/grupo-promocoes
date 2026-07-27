document.addEventListener("click", (event) => {
  const button = event.target.closest(".copy-btn");
  if (!button) return;

  const targetId = button.getAttribute("data-copy-target");
  const textarea = document.getElementById(targetId);
  if (!textarea) return;

  navigator.clipboard.writeText(textarea.value).then(() => {
    const original = button.textContent;
    button.textContent = "✅ Copiado!";
    setTimeout(() => {
      button.textContent = original;
    }, 1500);
  });
});
