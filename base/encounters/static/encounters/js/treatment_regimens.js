/**
 * JavaScript для работы со схемами лечения в encounters
 */

class TreatmentRegimensManager {
    constructor(encounterId = null) {
        this.encounterId = encounterId;
        this.init();
    }

    init() {
        this.bindEvents();
        this.setupDiagnosisSelect();
        
        // Дополнительная инициализация для Select2
        this.initSelect2();
    }

    bindEvents() {
        // Обработчик изменения диагноза - используем делегирование событий для Select2
        document.addEventListener('change', (e) => {
            if (e.target.id === 'diagnosis-select') {
                console.log('Диагноз изменен:', e.target.value);
                this.onDiagnosisChange(e.target.value);
            }
        });

        // Обработчик клика по кнопке "Показать рекомендации"
        document.addEventListener('click', (e) => {
            if (e.target.id === 'show-recommendations-btn') {
                this.showPatientRecommendations();
            }
        });
    }

    setupDiagnosisSelect() {
        const diagnosisSelect = document.getElementById('diagnosis-select');
        if (diagnosisSelect) {
            // Добавляем опцию для поиска
            const searchOption = document.createElement('option');
            searchOption.value = '';
            searchOption.textContent = 'Выберите диагноз';
            diagnosisSelect.insertBefore(searchOption, diagnosisSelect.firstChild);
        }
    }

    initSelect2() {
        // Ждем инициализации Select2
        const checkSelect2 = () => {
            const diagnosisSelect = document.getElementById('diagnosis-select');
            if (diagnosisSelect && diagnosisSelect.classList.contains('django-select2')) {
                console.log('Select2 инициализирован');
                
                // Добавляем обработчик для Select2
                $(diagnosisSelect).on('select2:select', (e) => {
                    console.log('Select2 выбрано:', e.params.data);
                    this.onDiagnosisChange(e.params.data.id);
                });
                
                $(diagnosisSelect).on('select2:clear', () => {
                    console.log('Select2 очищено');
                    this.clearRegimensDisplay();
                });
            } else {
                setTimeout(checkSelect2, 100);
            }
        };
        
        checkSelect2();
    }

    async onDiagnosisChange(diagnosisId) {
        if (!diagnosisId) {
            this.clearRegimensDisplay();
            return;
        }

        try {
            this.showLoading();
            const response = await this.fetchTreatmentRegimens(diagnosisId);
            this.displayRegimens(response);
        } catch (error) {
            console.error('Ошибка при загрузке схем лечения:', error);
            this.showError('Ошибка при загрузке схем лечения');
        }
    }

    async fetchTreatmentRegimens(diagnosisId) {
        const url = new URL('/encounters/api/treatment-regimens/', window.location.origin);
        url.searchParams.append('diagnosis_id', diagnosisId);
        if (this.encounterId) {
            url.searchParams.append('encounter_id', this.encounterId);
        }

        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    }

    async showPatientRecommendations() {
        if (!this.encounterId) {
            this.showError('ID обращения не найден');
            return;
        }

        const diagnosisSelect = document.getElementById('diagnosis-select');
        const diagnosisId = diagnosisSelect ? diagnosisSelect.value : null;

        try {
            this.showLoading();
            const response = await this.fetchPatientRecommendations(diagnosisId);
            this.displayPersonalizedRecommendations(response);
        } catch (error) {
            console.error('Ошибка при загрузке рекомендаций:', error);
            this.showError('Ошибка при загрузке рекомендаций');
        }
    }

    async fetchPatientRecommendations(diagnosisId) {
        const url = new URL('/encounters/api/patient-recommendations/', window.location.origin);
        url.searchParams.append('encounter_id', this.encounterId);
        if (diagnosisId) {
            url.searchParams.append('diagnosis_id', diagnosisId);
        }

        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    }

    displayRegimens(data) {
        const container = document.getElementById('treatment-regimens-container');
        if (!container) return;

        let html = `
            <div class="card">
                <div class="card-header">
                    <h5 class="mb-0">
                        <i class="fas fa-pills"></i> 
                        Схемы лечения для диагноза: ${data.diagnosis.name}
                    </h5>
                </div>
                <div class="card-body">
        `;

        if (data.regimens && data.regimens.length > 0) {
            data.regimens.forEach(regimen => {
                html += this.renderRegimenCard(regimen);
            });
        } else {
            html += '<p class="text-muted">Для данного диагноза схемы лечения не найдены.</p>';
        }

        if (this.encounterId && data.personalized_recommendations) {
            html += `
                <hr>
                <div class="mt-3">
                    <button id="show-recommendations-btn" class="btn btn-primary">
                        <i class="fas fa-user-md"></i> 
                        Показать персонализированные рекомендации
                    </button>
                </div>
            `;
        }

        html += '</div></div>';
        container.innerHTML = html;

        // Перепривязываем события для новых элементов
        this.bindEvents();
    }

    displayPersonalizedRecommendations(data) {
        const container = document.getElementById('treatment-regimens-container');
        if (!container) return;

        let html = `
            <div class="card">
                <div class="card-header">
                    <h5 class="mb-0">
                        <i class="fas fa-user-md"></i> 
                        Персонализированные рекомендации для пациента: ${data.patient.name}
                    </h5>
                    <small class="text-muted">Возраст: ${Math.floor(data.patient.age_days / 365)} лет</small>
                </div>
                <div class="card-body">
        `;

        if (data.recommendations && Object.keys(data.recommendations).length > 0) {
            Object.entries(data.recommendations).forEach(([medicationName, regimens]) => {
                html += this.renderPersonalizedRecommendation(medicationName, regimens);
            });
        } else {
            html += '<p class="text-muted">Персонализированные рекомендации не найдены.</p>';
        }

        html += `
                <hr>
                <div class="mt-3">
                    <button onclick="location.reload()" class="btn btn-secondary">
                        <i class="fas fa-arrow-left"></i> 
                        Назад к схемам лечения
                    </button>
                </div>
            </div>
        </div>
        `;

        container.innerHTML = html;
    }

    renderRegimenCard(regimen) {
        return `
            <div class="card mb-3">
                <div class="card-header">
                    <h6 class="mb-0">${regimen.medication_name} - ${regimen.name}</h6>
                </div>
                <div class="card-body">
                    ${regimen.notes ? `<p class="text-muted">${regimen.notes}</p>` : ''}
                    
                    ${regimen.dosing_instructions.length > 0 ? `
                        <h6>Инструкции по дозированию:</h6>
                        <ul class="list-unstyled">
                            ${regimen.dosing_instructions.map(instruction => `
                                <li class="mb-2">
                                    <strong>${instruction.dose_description}</strong> 
                                    ${instruction.frequency} 
                                    ${instruction.duration ? `в течение ${instruction.duration}` : ''}
                                </li>
                            `).join('')}
                        </ul>
                    ` : ''}
                </div>
            </div>
        `;
    }

    renderPersonalizedRecommendation(medicationName, regimens) {
        return `
            <div class="card mb-3">
                <div class="card-header bg-primary text-white">
                    <h6 class="mb-0">${medicationName}</h6>
                </div>
                <div class="card-body">
                    ${regimens.map(regimen => `
                        <div class="mb-3">
                            <h6>${regimen.regimen_name}</h6>
                            ${regimen.notes ? `<p class="text-muted">${regimen.notes}</p>` : ''}
                            
                            ${regimen.suitable_criteria.length > 0 ? `
                                <p><strong>Подходящие критерии:</strong></p>
                                <ul>
                                    ${regimen.suitable_criteria.map(criteria => `
                                        <li>${criteria.name} (возраст: ${criteria.age_range}, вес: ${criteria.weight_range})</li>
                                    `).join('')}
                                </ul>
                            ` : ''}
                            
                            ${regimen.dosing_instructions.length > 0 ? `
                                <p><strong>Инструкции по дозированию:</strong></p>
                                <ul>
                                    ${regimen.dosing_instructions.map(instruction => `
                                        <li>
                                            <strong>${instruction.dose_type}:</strong> 
                                            ${instruction.dose_description} 
                                            ${instruction.frequency} 
                                            ${instruction.duration ? `в течение ${instruction.duration}` : ''}
                                            ${instruction.route ? `(${instruction.route})` : ''}
                                        </li>
                                    `).join('')}
                                </ul>
                            ` : ''}
                            
                            ${regimen.adjustments.length > 0 ? `
                                <p><strong>Корректировки:</strong></p>
                                <ul>
                                    ${regimen.adjustments.map(adjustment => `
                                        <li><strong>${adjustment.condition}:</strong> ${adjustment.adjustment}</li>
                                    `).join('')}
                                </ul>
                            ` : ''}
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }

    clearRegimensDisplay() {
        const container = document.getElementById('treatment-regimens-container');
        if (container) {
            container.innerHTML = '';
        }
    }

    showLoading() {
        const container = document.getElementById('treatment-regimens-container');
        if (container) {
            container.innerHTML = `
                <div class="text-center">
                    <div class="spinner-border" role="status">
                        <span class="visually-hidden">Загрузка...</span>
                    </div>
                    <p class="mt-2">Загрузка схем лечения...</p>
                </div>
            `;
        }
    }

    showError(message) {
        const container = document.getElementById('treatment-regimens-container');
        if (container) {
            container.innerHTML = `
                <div class="alert alert-danger" role="alert">
                    <i class="fas fa-exclamation-triangle"></i> 
                    ${message}
                </div>
            `;
        }
    }
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    // Получаем ID обращения из URL или data-атрибута
    const encounterId = document.querySelector('[data-encounter-id]')?.dataset.encounterId || 
                       window.location.pathname.match(/\/encounters\/(\d+)\//)?.[1];
    
    window.treatmentRegimensManager = new TreatmentRegimensManager(encounterId);
}); 