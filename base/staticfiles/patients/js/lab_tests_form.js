document.addEventListener('DOMContentLoaded', function () {
    const resultTypeSelect = document.getElementById('id_result_type');
    const resultFieldsContainer = document.getElementById('result-fields');

    resultTypeSelect.addEventListener('change', function () {
        const resultTypeId = this.value;
        if (resultTypeId) {
            fetch(`/lab_tests/result-types/${resultTypeId}/schema/`)
                .then(response => response.json())
                .then(schema => {
                    resultFieldsContainer.innerHTML = '';
                    for (const [field, config] of Object.entries(schema)) {
                        const div = document.createElement('div');
                        div.classList.add('mb-3');
                        div.innerHTML = `
                            <label class="form-label">${config.label} (${config.unit})</label>
                            <input type="text" class="form-control" name="${field}">
                        `;
                        resultFieldsContainer.appendChild(div);
                    }
                });
        }
    });
});