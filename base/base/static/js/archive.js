/**
 * JavaScript для системы архивирования
 */

class ArchiveManager {
    constructor() {
        this.init();
    }

    init() {
        this.bindEvents();
        this.updateArchiveButtons();
    }

    bindEvents() {
        // Обработчики для кнопок архивирования
        document.addEventListener('click', (e) => {
            if (e.target.matches('.btn-archive')) {
                e.preventDefault();
                this.handleArchiveClick(e.target);
            }
            
            if (e.target.matches('.btn-restore')) {
                e.preventDefault();
                this.handleRestoreClick(e.target);
            }
            
            if (e.target.matches('.btn-bulk-archive')) {
                e.preventDefault();
                this.handleBulkArchiveClick(e.target);
            }
        });

        // Обработчики для чекбоксов массового выбора
        document.addEventListener('change', (e) => {
            if (e.target.matches('.record-checkbox')) {
                this.updateBulkActions();
            }
        });
    }

    handleArchiveClick(button) {
        const url = button.getAttribute('href');
        const recordName = button.getAttribute('data-record-name');
        
        if (confirm(`Вы уверены, что хотите архивировать "${recordName}"?`)) {
            this.showArchiveModal(url, recordName);
        }
    }

    handleRestoreClick(button) {
        const url = button.getAttribute('href');
        const recordName = button.getAttribute('data-record-name');
        
        if (confirm(`Вы уверены, что хотите восстановить "${recordName}" из архива?`)) {
            this.showRestoreModal(url, recordName);
        }
    }

    handleBulkArchiveClick(button) {
        const selectedRecords = this.getSelectedRecords();
        
        if (selectedRecords.length === 0) {
            alert('Выберите записи для архивирования');
            return;
        }
        
        this.showBulkArchiveModal(selectedRecords);
    }

    showArchiveModal(url, recordName) {
        const modal = this.createModal(
            'Архивирование записи',
            `Вы собираетесь архивировать "${recordName}". Укажите причину архивирования:`,
            'archive'
        );

        modal.querySelector('.modal-body').innerHTML = `
            <form id="archiveForm">
                <div class="mb-3">
                    <label for="archiveReason" class="form-label">Причина архивирования</label>
                    <textarea class="form-control" id="archiveReason" rows="3" 
                              placeholder="Укажите причину архивирования..." required></textarea>
                </div>
                <div class="form-check mb-3">
                    <input class="form-check-input" type="checkbox" id="cascadeArchive" checked>
                    <label class="form-check-label" for="cascadeArchive">
                        Каскадное архивирование (архивировать связанные записи)
                    </label>
                </div>
            </form>
        `;

        modal.querySelector('.btn-primary').onclick = () => {
            const reason = modal.querySelector('#archiveReason').value;
            const cascade = modal.querySelector('#cascadeArchive').checked;
            
            if (!reason.trim()) {
                alert('Необходимо указать причину архивирования');
                return;
            }
            
            this.performArchive(url, reason, cascade);
            this.closeModal(modal);
        };

        this.showModal(modal);
    }

    showRestoreModal(url, recordName) {
        const modal = this.createModal(
            'Восстановление записи',
            `Вы собираетесь восстановить "${recordName}" из архива.`,
            'restore'
        );

        modal.querySelector('.modal-body').innerHTML = `
            <form id="restoreForm">
                <div class="form-check mb-3">
                    <input class="form-check-input" type="checkbox" id="cascadeRestore" checked>
                    <label class="form-check-label" for="cascadeRestore">
                        Каскадное восстановление (восстановить связанные записи)
                    </label>
                </div>
            </form>
        `;

        modal.querySelector('.btn-primary').onclick = () => {
            const cascade = modal.querySelector('#cascadeRestore').checked;
            this.performRestore(url, cascade);
            this.closeModal(modal);
        };

        this.showModal(modal);
    }

    showBulkArchiveModal(selectedRecords) {
        const modal = this.createModal(
            'Массовое архивирование',
            `Вы собираетесь архивировать ${selectedRecords.length} записей. Укажите причину архивирования:`,
            'bulk-archive'
        );

        modal.querySelector('.modal-body').innerHTML = `
            <form id="bulkArchiveForm">
                <div class="mb-3">
                    <label for="bulkArchiveReason" class="form-label">Причина архивирования</label>
                    <textarea class="form-control" id="bulkArchiveReason" rows="3" 
                              placeholder="Укажите причину архивирования..." required></textarea>
                </div>
                <div class="form-check mb-3">
                    <input class="form-check-input" type="checkbox" id="bulkCascadeArchive" checked>
                    <label class="form-check-label" for="bulkCascadeArchive">
                        Каскадное архивирование (архивировать связанные записи)
                    </label>
                </div>
                <div class="alert alert-info">
                    <strong>Выбранные записи:</strong>
                    <ul class="mb-0 mt-2">
                        ${selectedRecords.map(record => `<li>${record.name}</li>`).join('')}
                    </ul>
                </div>
            </form>
        `;

        modal.querySelector('.btn-primary').onclick = () => {
            const reason = modal.querySelector('#bulkArchiveReason').value;
            const cascade = modal.querySelector('#bulkCascadeArchive').checked;
            
            if (!reason.trim()) {
                alert('Необходимо указать причину архивирования');
                return;
            }
            
            this.performBulkArchive(selectedRecords, reason, cascade);
            this.closeModal(modal);
        };

        this.showModal(modal);
    }

    createModal(title, message, type) {
        const modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.innerHTML = `
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">
                            <i class="fas fa-${type === 'archive' ? 'archive' : 'undo'} text-${type === 'archive' ? 'warning' : 'success'}"></i>
                            ${title}
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <p>${message}</p>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Отмена</button>
                        <button type="button" class="btn btn-${type === 'archive' ? 'warning' : 'success'}">
                            <i class="fas fa-${type === 'archive' ? 'archive' : 'undo'}"></i>
                            ${type === 'archive' ? 'Архивировать' : 'Восстановить'}
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        return modal;
    }

    showModal(modal) {
        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();
    }

    closeModal(modal) {
        const bsModal = bootstrap.Modal.getInstance(modal);
        if (bsModal) {
            bsModal.hide();
        }
        modal.remove();
    }

    async performArchive(url, reason, cascade) {
        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken(),
                },
                body: JSON.stringify({
                    reason: reason,
                    cascade: cascade
                })
            });

            const result = await response.json();
            
            if (result.success) {
                this.showSuccessMessage(result.message);
                this.updateArchiveStatus(url, true);
            } else {
                this.showErrorMessage(result.error);
            }
        } catch (error) {
            this.showErrorMessage('Ошибка при архивировании: ' + error.message);
        }
    }

    async performRestore(url, cascade) {
        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken(),
                },
                body: JSON.stringify({
                    cascade: cascade
                })
            });

            const result = await response.json();
            
            if (result.success) {
                this.showSuccessMessage(result.message);
                this.updateArchiveStatus(url, false);
            } else {
                this.showErrorMessage(result.error);
            }
        } catch (error) {
            this.showErrorMessage('Ошибка при восстановлении: ' + error.message);
        }
    }

    async performBulkArchive(selectedRecords, reason, cascade) {
        try {
            const response = await fetch('/base/bulk-archive/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken(),
                },
                body: JSON.stringify({
                    record_ids: selectedRecords.map(r => r.id),
                    reason: reason,
                    cascade: cascade
                })
            });

            const result = await response.json();
            
            if (result.success) {
                this.showSuccessMessage(result.message);
                this.refreshPage();
            } else {
                this.showErrorMessage(result.error);
            }
        } catch (error) {
            this.showErrorMessage('Ошибка при массовом архивировании: ' + error.message);
        }
    }

    updateArchiveStatus(url, isArchived) {
        const button = document.querySelector(`[href="${url}"]`);
        if (button) {
            if (isArchived) {
                button.classList.remove('btn-warning', 'btn-archive');
                button.classList.add('btn-success', 'btn-restore');
                button.innerHTML = '<i class="fas fa-undo"></i> Восстановить';
                button.setAttribute('data-record-name', button.getAttribute('data-record-name'));
            } else {
                button.classList.remove('btn-success', 'btn-restore');
                button.classList.add('btn-warning', 'btn-archive');
                button.innerHTML = '<i class="fas fa-archive"></i> Архивировать';
                button.setAttribute('data-record-name', button.getAttribute('data-record-name'));
            }
        }
    }

    getSelectedRecords() {
        const checkboxes = document.querySelectorAll('.record-checkbox:checked');
        return Array.from(checkboxes).map(cb => ({
            id: cb.value,
            name: cb.getAttribute('data-record-name')
        }));
    }

    updateBulkActions() {
        const selectedRecords = this.getSelectedRecords();
        const bulkButtons = document.querySelectorAll('.btn-bulk-archive');
        
        bulkButtons.forEach(button => {
            button.disabled = selectedRecords.length === 0;
        });
    }

    updateArchiveButtons() {
        // Обновляем стили кнопок в зависимости от статуса архивирования
        document.querySelectorAll('.btn-archive, .btn-restore').forEach(button => {
            const row = button.closest('tr');
            if (row) {
                const isArchived = row.classList.contains('archived') || 
                                 row.querySelector('.archive-status')?.textContent.includes('Архивировано');
                
                if (isArchived) {
                    button.classList.remove('btn-warning', 'btn-archive');
                    button.classList.add('btn-success', 'btn-restore');
                    button.innerHTML = '<i class="fas fa-undo"></i> Восстановить';
                } else {
                    button.classList.remove('btn-success', 'btn-restore');
                    button.classList.add('btn-warning', 'btn-archive');
                    button.innerHTML = '<i class="fas fa-archive"></i> Архивировать';
                }
            }
        });
    }

    getCSRFToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value ||
               document.cookie.split('; ').find(row => row.startsWith('csrftoken='))?.split('=')[1];
    }

    showSuccessMessage(message) {
        this.showMessage(message, 'success');
    }

    showErrorMessage(message) {
        this.showMessage(message, 'danger');
    }

    showMessage(message, type) {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        const container = document.querySelector('.container') || document.body;
        container.insertBefore(alertDiv, container.firstChild);
        
        // Автоматически скрываем через 5 секунд
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.remove();
            }
        }, 5000);
    }

    refreshPage() {
        window.location.reload();
    }
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    window.archiveManager = new ArchiveManager();
});

// Экспорт для использования в других модулях
window.ArchiveManager = ArchiveManager;
