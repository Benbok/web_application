document.addEventListener("DOMContentLoaded", function () {
  const statusSelect = document.getElementById("id_status");
  const reasonContainer = document.getElementById("cancellation_reason_container");

  function toggleReasonField() {
    if (!statusSelect || !reasonContainer) return;
    reasonContainer.style.display = statusSelect.value === "canceled" ? "block" : "none";
  }

  if (statusSelect) {
    toggleReasonField();
    statusSelect.addEventListener("change", toggleReasonField);
  }

  if (document.body.dataset.assignmentType === "medication") {
    const medicationSelect = document.getElementById("id_medication");
    const dosingRuleSelect = document.getElementById("id_dosing_rule");

    function updateDosingRules() {
      const medicationId = medicationSelect.value;
      dosingRuleSelect.innerHTML = '<option value="">Загрузка правил...</option>';
      dosingRuleSelect.disabled = true;

      if (medicationId) {
        fetch(`${dosingRuleSelect.dataset.url}?medication_id=${medicationId}`)
          .then((response) => response.json())
          .then((data) => {
            dosingRuleSelect.innerHTML = '<option value="">Выберите правило</option>';
            data.forEach((rule) => {
              const option = new Option(rule.name, rule.id);
              dosingRuleSelect.add(option);
            });
            dosingRuleSelect.disabled = false;
          })
          .catch((error) => {
            console.error("Ошибка при загрузке правил дозирования:", error);
            dosingRuleSelect.innerHTML = '<option value="">Ошибка загрузки</option>';
          });
      } else {
        dosingRuleSelect.innerHTML = '<option value="">Сначала выберите препарат</option>';
      }
    }

    if (medicationSelect) {
      medicationSelect.addEventListener("change", updateDosingRules);
      if (!medicationSelect.value) {
        dosingRuleSelect.disabled = true;
        dosingRuleSelect.innerHTML = '<option value="">Сначала выберите препарат</option>';
      }
    }
  }
});
