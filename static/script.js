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

// Ações dos cards (categoria, status, bom exemplo, excluir) são enviadas
// sem recarregar a página inteira, pra não perder a posição de rolagem.
document.addEventListener("submit", (event) => {
  const form = event.target;
  if (!form.classList.contains("ajax-form")) return;
  event.preventDefault();

  const card = form.closest(".product-card");
  const action = form.dataset.action;

  fetch(form.action, {
    method: "POST",
    headers: { "X-Requested-With": "XMLHttpRequest" },
    body: new FormData(form),
  })
    .then((response) => {
      if (!response.ok) throw new Error("resposta inesperada do servidor");
      return response.json();
    })
    .then((data) => {
      if (action === "delete") {
        card.remove();
        return;
      }

      if (action === "liked") {
        const btn = form.querySelector("button");
        if (data.liked) {
          btn.textContent = "⭐ Bom exemplo";
          btn.classList.add("btn-liked");
        } else {
          btn.textContent = "☆ Marcar como bom exemplo";
          btn.classList.remove("btn-liked");
        }
        return;
      }

      if (action === "status") {
        card.classList.remove("status-pendente", "status-enviado");
        card.classList.add("status-" + data.status);
        const hidden = form.querySelector("input[name='status']");
        const btn = form.querySelector("button");
        card.querySelector(".badge-status").textContent = data.status;
        if (data.status === "pendente") {
          hidden.value = "enviado";
          btn.textContent = "Marcar como enviado";
          btn.classList.add("btn-primary");
        } else {
          hidden.value = "pendente";
          btn.textContent = "Marcar como pendente";
          btn.classList.remove("btn-primary");
        }
        return;
      }

      if (action === "category") {
        card.querySelector(".badge-category").textContent = data.category;
        card.querySelector(".generated-text").value = data.generated_text;
        return;
      }
    })
    .catch(() => {
      alert("Não foi possível salvar essa alteração. Tente novamente.");
    });
});
