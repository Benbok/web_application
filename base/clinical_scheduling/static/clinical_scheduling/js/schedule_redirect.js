/**
 * JavaScript для перенаправления на форму настройки расписания
 * после создания назначения в treatment_management и examination_management
 */

(function() {
    'use strict';
    
    /**
     * Перенаправляет на форму настройки расписания
     * @param {string} assignmentType - тип назначения (medication, lab_test, procedure)
     * @param {number} assignmentId - ID назначения
     * @param {number} contentTypeId - ID типа контента
     */
    function redirectToScheduleSettings(assignmentType, assignmentId, contentTypeId) {
        const baseUrl = '/scheduling/schedule-settings/';
        const params = new URLSearchParams({
            assignment_type: assignmentType,
            assignment_id: assignmentId,
            content_type_id: contentTypeId
        });
        
        const url = baseUrl + '?' + params.toString();
        window.location.href = url;
    }
    
    /**
     * Обрабатывает успешное создание назначения
     * @param {Object} data - данные ответа от сервера
     */
    function handleAssignmentCreated(data) {
        if (data && data.success && data.assignment_id) {
            // Определяем тип назначения по URL или другим признакам
            let assignmentType = 'medication'; // по умолчанию
            
            if (window.location.pathname.includes('lab-tests')) {
                assignmentType = 'lab_test';
            } else if (window.location.pathname.includes('instrumental')) {
                assignmentType = 'procedure';
            }
            
            // Получаем ID типа контента для модели
            let contentTypeId;
            switch (assignmentType) {
                case 'medication':
                    contentTypeId = 1; // ID для TreatmentMedication
                    break;
                case 'lab_test':
                    contentTypeId = 2; // ID для ExaminationLabTest
                    break;
                case 'procedure':
                    contentTypeId = 3; // ID для ExaminationInstrumental
                    break;
                default:
                    contentTypeId = 1;
            }
            
            // Перенаправляем на форму настройки расписания
            redirectToScheduleSettings(assignmentType, data.assignment_id, contentTypeId);
        }
    }
    
    /**
     * Инициализирует обработчики событий
     */
    function init() {
        // Находим все формы создания назначений
        const forms = document.querySelectorAll('form[data-schedule-redirect="true"]');
        
        forms.forEach(form => {
            form.addEventListener('submit', function(e) {
                // Добавляем обработчик для AJAX ответа
                const originalSubmit = form.submit;
                
                // Если форма использует AJAX, перехватываем ответ
                if (window.fetch) {
                    e.preventDefault();
                    
                    const formData = new FormData(form);
                    const url = form.action || window.location.href;
                    
                    fetch(url, {
                        method: 'POST',
                        body: formData,
                        headers: {
                            'X-Requested-With': 'XMLHttpRequest'
                        }
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            handleAssignmentCreated(data);
                        } else {
                            // Если AJAX не удался, отправляем форму обычным способом
                            form.submit();
                        }
                    })
                    .catch(() => {
                        // В случае ошибки отправляем форму обычным способом
                        form.submit();
                    });
                }
            });
        });
        
        // Обработчик для успешного создания через Django messages
        const successMessages = document.querySelectorAll('.alert-success');
        successMessages.forEach(message => {
            if (message.textContent.includes('создан') || message.textContent.includes('создано')) {
                // Ищем ID назначения в сообщении или на странице
                const assignmentIdMatch = message.textContent.match(/ID[:\s]*(\d+)/i);
                if (assignmentIdMatch) {
                    const assignmentId = assignmentIdMatch[1];
                    
                    // Определяем тип назначения
                    let assignmentType = 'medication';
                    if (window.location.pathname.includes('lab-tests')) {
                        assignmentType = 'lab_test';
                    } else if (window.location.pathname.includes('instrumental')) {
                        assignmentType = 'procedure';
                    }
                    
                    // Получаем ID типа контента
                    let contentTypeId = 1;
                    if (assignmentType === 'lab_test') contentTypeId = 2;
                    else if (assignmentType === 'procedure') contentTypeId = 3;
                    
                    // Добавляем кнопку для перехода к настройке расписания
                    const redirectButton = document.createElement('button');
                    redirectButton.type = 'button';
                    redirectButton.className = 'btn btn-primary btn-sm ms-2';
                    redirectButton.innerHTML = '<i class="fas fa-calendar-plus me-1"></i>Настроить расписание';
                    redirectButton.onclick = function() {
                        redirectToScheduleSettings(assignmentType, assignmentId, contentTypeId);
                    };
                    
                    message.appendChild(redirectButton);
                }
            }
        });
    }
    
    // Инициализируем при загрузке страницы
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
    
    // Экспортируем функции для использования в других скриптах
    window.ScheduleRedirect = {
        redirectToScheduleSettings: redirectToScheduleSettings,
        handleAssignmentCreated: handleAssignmentCreated
    };
    
})(); 