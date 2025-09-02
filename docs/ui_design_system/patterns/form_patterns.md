# Паттерны форм - МедКарт

## Обзор

Данный документ описывает стандартные паттерны форм для медицинской информационной системы МедКарт. Все паттерны основаны на анализе существующих шаблонов и адаптированы под специфику медицинских рабочих процессов.

## 1. Паттерн "Quick Create" (Быстрое создание)

### Описание
Модальная форма для быстрого создания записей без перехода на отдельную страницу.

### HTML структура

```html
<!-- Модальное окно -->
<div class="modal fade" id="quickCreateModal" tabindex="-1" aria-labelledby="quickCreateModalLabel" aria-hidden="true">
  <div class="modal-dialog modal-lg">
    <div class="modal-content">
      <div class="modal-header">
        <h5 class="modal-title" id="quickCreateModalLabel">
          <i class="fas fa-plus-circle me-2"></i>Быстрое создание
        </h5>
        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
      </div>
      <div class="modal-body">
        <form method="post" class="quick-create-form">
          {% csrf_token %}
          
          <!-- Основные поля -->
          <div class="row">
            <div class="col-md-6">
              <div class="form-group">
                <label for="{{ form.field1.id_for_label }}" class="form-label">
                  <strong>{{ form.field1.label }}</strong>
                </label>
                {{ form.field1|add_class:"form-control" }}
                {% if form.field1.errors %}
                  <div class="invalid-feedback d-block">
                    {% for error in form.field1.errors %}
                      {{ error }}
                    {% endfor %}
                  </div>
                {% endif %}
              </div>
            </div>
            <div class="col-md-6">
              <div class="form-group">
                <label for="{{ form.field2.id_for_label }}" class="form-label">
                  <strong>{{ form.field2.label }}</strong>
                </label>
                {{ form.field2|add_class:"form-control" }}
                {% if form.field2.errors %}
                  <div class="invalid-feedback d-block">
                    {% for error in form.field2.errors %}
                      {{ error }}
                    {% endfor %}
                  </div>
                {% endif %}
              </div>
            </div>
          </div>
        </form>
      </div>
      <div class="modal-footer">
        <button type="button" class="btn btn-outline-secondary" data-bs-dismiss="modal">
          <i class="fas fa-times me-1"></i>Отмена
        </button>
        <button type="submit" form="quickCreateForm" class="btn btn-primary">
          <i class="fas fa-save me-1"></i>Создать
        </button>
      </div>
    </div>
  </div>
</div>
```

### CSS стили

```css
/* Модальное окно */
.modal-content {
  border: none;
  border-radius: var(--border-radius);
  box-shadow: var(--shadow-lg);
}

.modal-header {
  background-color: var(--bg-primary);
  border-bottom: 1px solid var(--border-light);
  border-radius: var(--border-radius) var(--border-radius) 0 0;
}

.modal-title {
  font-family: 'Montserrat', sans-serif;
  font-weight: 600;
  color: var(--text-primary);
  display: flex;
  align-items: center;
}

.modal-title i {
  color: var(--primary-color);
}

.modal-body {
  padding: var(--spacing-lg);
}

.modal-footer {
  background-color: var(--bg-primary);
  border-top: 1px solid var(--border-light);
  border-radius: 0 0 var(--border-radius) var(--border-radius);
  padding: var(--spacing-md) var(--spacing-lg);
}

/* Форма в модальном окне */
.quick-create-form {
  margin: 0;
}

.quick-create-form .form-group {
  margin-bottom: var(--spacing-md);
}

.quick-create-form .form-label {
  font-size: 0.9rem;
  font-weight: 600;
  margin-bottom: var(--spacing-sm);
}

.quick-create-form .form-control {
  font-size: 0.9rem;
  padding: var(--spacing-sm) var(--spacing-md);
}
```

### JavaScript функциональность

```javascript
// Инициализация модального окна
document.addEventListener('DOMContentLoaded', function() {
  const quickCreateModal = document.getElementById('quickCreateModal');
  if (quickCreateModal) {
    const modal = new bootstrap.Modal(quickCreateModal);
    
    // Обработка отправки формы
    const form = quickCreateModal.querySelector('form');
    form.addEventListener('submit', function(e) {
      e.preventDefault();
      
      const submitButton = quickCreateModal.querySelector('button[type="submit"]');
      submitButton.disabled = true;
      submitButton.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Создание...';
      
      // Отправка формы через AJAX
      fetch(form.action, {
        method: 'POST',
        body: new FormData(form),
        headers: {
          'X-CSRFToken': form.querySelector('[name=csrfmiddlewaretoken]').value
        }
      })
      .then(response => response.json())
      .then(data => {
        if (data.success) {
          modal.hide();
          toastr.success('Запись успешно создана');
          // Обновление списка или страницы
          location.reload();
        } else {
          toastr.error('Ошибка при создании записи');
        }
      })
      .catch(error => {
        toastr.error('Ошибка сети');
      })
      .finally(() => {
        submitButton.disabled = false;
        submitButton.innerHTML = '<i class="fas fa-save me-1"></i>Создать';
      });
    });
  }
});
```

## 2. Паттерн "Multi-step Form" (Многошаговая форма)

### Описание
Форма с несколькими шагами для сложных процессов, таких как создание медицинских документов или планов лечения.

### HTML структура

```html
<div class="multi-step-form">
  <div class="card mt-4" style="z-index: 2;">
    <div class="card-body position-relative">
      <h4 class="card-title mb-4">{{ title }}</h4>
      
      <!-- Индикатор прогресса -->
      <div class="progress-indicator mb-4">
        <div class="progress-steps">
          <div class="step active" data-step="1">
            <div class="step-number">1</div>
            <div class="step-label">Основная информация</div>
          </div>
          <div class="step" data-step="2">
            <div class="step-number">2</div>
            <div class="step-label">Детали</div>
          </div>
          <div class="step" data-step="3">
            <div class="step-number">3</div>
            <div class="step-label">Проверка</div>
          </div>
        </div>
      </div>
      
      <!-- Форма -->
      <form method="post" class="multi-step-form" id="multiStepForm">
        {% csrf_token %}
        
        <!-- Шаг 1: Основная информация -->
        <div class="form-step active" data-step="1">
          <div class="form-section">
            <h5 class="section-title">
              <i class="fas fa-info-circle me-2"></i>Основная информация
            </h5>
            <div class="row">
              <div class="col-md-6">
                <div class="form-group">
                  <label for="{{ form.field1.id_for_label }}" class="form-label">
                    <strong>{{ form.field1.label }}</strong>
                  </label>
                  {{ form.field1|add_class:"form-control" }}
                </div>
              </div>
              <div class="col-md-6">
                <div class="form-group">
                  <label for="{{ form.field2.id_for_label }}" class="form-label">
                    <strong>{{ form.field2.label }}</strong>
                  </label>
                  {{ form.field2|add_class:"form-control" }}
                </div>
              </div>
            </div>
          </div>
        </div>
        
        <!-- Шаг 2: Детали -->
        <div class="form-step" data-step="2">
          <div class="form-section">
            <h5 class="section-title">
              <i class="fas fa-list me-2"></i>Детали
            </h5>
            <div class="form-group">
              <label for="{{ form.field3.id_for_label }}" class="form-label">
                <strong>{{ form.field3.label }}</strong>
              </label>
              {{ form.field3|add_class:"form-control" }}
            </div>
          </div>
        </div>
        
        <!-- Шаг 3: Проверка -->
        <div class="form-step" data-step="3">
          <div class="form-section">
            <h5 class="section-title">
              <i class="fas fa-check-circle me-2"></i>Проверка данных
            </h5>
            <div class="preview-data">
              <!-- Предварительный просмотр данных -->
            </div>
          </div>
        </div>
        
        <!-- Навигация -->
        <div class="form-navigation">
          <div class="d-flex justify-content-between align-items-center mt-3">
            <button type="button" class="btn btn-outline-secondary" id="prevStep" style="display: none;">
              <i class="fas fa-arrow-left me-1"></i>Назад
            </button>
            <div class="ms-auto">
              <button type="button" class="btn btn-primary" id="nextStep">
                Далее<i class="fas fa-arrow-right ms-1"></i>
              </button>
              <button type="submit" class="btn btn-success" id="submitForm" style="display: none;">
                <i class="fas fa-save me-1"></i>Сохранить
              </button>
            </div>
          </div>
        </div>
      </form>
    </div>
  </div>
</div>
```

### CSS стили

```css
/* Индикатор прогресса */
.progress-indicator {
  margin-bottom: var(--spacing-lg);
}

.progress-steps {
  display: flex;
  justify-content: space-between;
  align-items: center;
  position: relative;
}

.progress-steps::before {
  content: '';
  position: absolute;
  top: 50%;
  left: 0;
  right: 0;
  height: 2px;
  background-color: var(--border-color);
  z-index: 1;
}

.step {
  display: flex;
  flex-direction: column;
  align-items: center;
  position: relative;
  z-index: 2;
  background-color: var(--bg-secondary);
  padding: var(--spacing-sm);
}

.step-number {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background-color: var(--border-color);
  color: var(--text-muted);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  margin-bottom: var(--spacing-xs);
  transition: all var(--transition-speed) ease;
}

.step.active .step-number {
  background-color: var(--primary-color);
  color: white;
}

.step.completed .step-number {
  background-color: var(--success-color);
  color: white;
}

.step-label {
  font-size: 0.8rem;
  color: var(--text-muted);
  text-align: center;
  font-weight: 500;
}

.step.active .step-label {
  color: var(--text-primary);
}

/* Шаги формы */
.form-step {
  display: none;
  animation: fadeIn 0.3s ease;
}

.form-step.active {
  display: block;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Навигация */
.form-navigation {
  border-top: 1px solid var(--border-light);
  padding-top: var(--spacing-lg);
  margin-top: var(--spacing-lg);
}

/* Адаптивность */
@media (max-width: 768px) {
  .progress-steps {
    flex-direction: column;
    gap: var(--spacing-md);
  }
  
  .progress-steps::before {
    display: none;
  }
  
  .step {
    flex-direction: row;
    gap: var(--spacing-sm);
  }
  
  .step-number {
    margin-bottom: 0;
  }
}
```

### JavaScript функциональность

```javascript
class MultiStepForm {
  constructor(formElement) {
    this.form = formElement;
    this.currentStep = 1;
    this.totalSteps = 3;
    this.init();
  }
  
  init() {
    this.bindEvents();
    this.updateNavigation();
  }
  
  bindEvents() {
    const nextBtn = this.form.querySelector('#nextStep');
    const prevBtn = this.form.querySelector('#prevStep');
    const submitBtn = this.form.querySelector('#submitForm');
    
    nextBtn.addEventListener('click', () => this.nextStep());
    prevBtn.addEventListener('click', () => this.prevStep());
    submitBtn.addEventListener('click', () => this.submitForm());
  }
  
  nextStep() {
    if (this.validateCurrentStep()) {
      this.currentStep++;
      this.updateSteps();
      this.updateNavigation();
    }
  }
  
  prevStep() {
    if (this.currentStep > 1) {
      this.currentStep--;
      this.updateSteps();
      this.updateNavigation();
    }
  }
  
  updateSteps() {
    // Обновляем отображение шагов
    const steps = this.form.querySelectorAll('.form-step');
    const progressSteps = this.form.querySelectorAll('.step');
    
    steps.forEach((step, index) => {
      if (index + 1 === this.currentStep) {
        step.classList.add('active');
      } else {
        step.classList.remove('active');
      }
    });
    
    progressSteps.forEach((step, index) => {
      const stepNumber = index + 1;
      step.classList.remove('active', 'completed');
      
      if (stepNumber < this.currentStep) {
        step.classList.add('completed');
      } else if (stepNumber === this.currentStep) {
        step.classList.add('active');
      }
    });
  }
  
  updateNavigation() {
    const nextBtn = this.form.querySelector('#nextStep');
    const prevBtn = this.form.querySelector('#prevStep');
    const submitBtn = this.form.querySelector('#submitForm');
    
    // Показываем/скрываем кнопки
    prevBtn.style.display = this.currentStep > 1 ? 'block' : 'none';
    nextBtn.style.display = this.currentStep < this.totalSteps ? 'block' : 'none';
    submitBtn.style.display = this.currentStep === this.totalSteps ? 'block' : 'none';
    
    // Обновляем текст кнопки "Далее"
    if (this.currentStep === this.totalSteps - 1) {
      nextBtn.innerHTML = 'Проверить<i class="fas fa-check ms-1"></i>';
    } else {
      nextBtn.innerHTML = 'Далее<i class="fas fa-arrow-right ms-1"></i>';
    }
  }
  
  validateCurrentStep() {
    const currentStepElement = this.form.querySelector(`[data-step="${this.currentStep}"]`);
    const requiredFields = currentStepElement.querySelectorAll('[required]');
    let isValid = true;
    
    requiredFields.forEach(field => {
      if (!field.value.trim()) {
        field.classList.add('is-invalid');
        isValid = false;
      } else {
        field.classList.remove('is-invalid');
      }
    });
    
    if (!isValid) {
      toastr.error('Пожалуйста, заполните все обязательные поля');
    }
    
    return isValid;
  }
  
  submitForm() {
    if (this.validateCurrentStep()) {
      this.form.submit();
    }
  }
}

// Инициализация
document.addEventListener('DOMContentLoaded', function() {
  const multiStepForm = document.querySelector('.multi-step-form');
  if (multiStepForm) {
    new MultiStepForm(multiStepForm);
  }
});
```

## 3. Паттерн "Form with Preview" (Форма с предварительным просмотром)

### Описание
Форма с предварительным просмотром результата, особенно полезная для медицинских документов и отчетов.

### HTML структура

```html
<div class="form-with-preview">
  <div class="row">
    <!-- Форма -->
    <div class="col-md-6">
      <div class="card mt-4" style="z-index: 2;">
        <div class="card-body position-relative">
          <h4 class="card-title mb-4">
            <i class="fas fa-edit me-2"></i>Редактирование
          </h4>
          
          <form method="post" class="preview-form">
            {% csrf_token %}
            
            <div class="form-section">
              <h5 class="section-title">
                <i class="fas fa-info-circle me-2"></i>Основная информация
              </h5>
              <div class="form-group">
                <label for="{{ form.title.id_for_label }}" class="form-label">
                  <strong>{{ form.title.label }}</strong>
                </label>
                {{ form.title|add_class:"form-control" }}
              </div>
              <div class="form-group">
                <label for="{{ form.content.id_for_label }}" class="form-label">
                  <strong>{{ form.content.label }}</strong>
                </label>
                {{ form.content|add_class:"form-control" }}
              </div>
            </div>
            
            <div class="form-actions">
              <button type="submit" class="btn btn-primary">
                <i class="fas fa-save me-1"></i>Сохранить
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
    
    <!-- Предварительный просмотр -->
    <div class="col-md-6">
      <div class="card mt-4" style="z-index: 2;">
        <div class="card-body position-relative">
          <h4 class="card-title mb-4">
            <i class="fas fa-eye me-2"></i>Предварительный просмотр
          </h4>
          
          <div class="preview-content">
            <div class="preview-header">
              <h3 id="previewTitle">Заголовок документа</h3>
              <p class="text-muted">Дата: <span id="previewDate">{{ current_date|date:"d.m.Y" }}</span></p>
            </div>
            
            <div class="preview-body">
              <div id="previewContent">
                Содержимое документа будет отображаться здесь...
              </div>
            </div>
            
            <div class="preview-footer">
              <div class="document-meta">
                <small class="text-muted">
                  <i class="fas fa-user-md me-1"></i>
                  Врач: {{ request.user.get_full_name }}
                </small>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>
```

### CSS стили

```css
/* Контейнер формы с предварительным просмотром */
.form-with-preview {
  margin-bottom: var(--spacing-lg);
}

/* Предварительный просмотр */
.preview-content {
  background-color: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  padding: var(--spacing-lg);
  min-height: 400px;
}

.preview-header {
  border-bottom: 2px solid var(--primary-color);
  padding-bottom: var(--spacing-md);
  margin-bottom: var(--spacing-lg);
}

.preview-header h3 {
  color: var(--text-primary);
  font-weight: 600;
  margin-bottom: var(--spacing-sm);
}

.preview-body {
  margin-bottom: var(--spacing-lg);
}

.preview-body p {
  line-height: 1.6;
  color: var(--text-primary);
  margin-bottom: var(--spacing-md);
}

.preview-footer {
  border-top: 1px solid var(--border-light);
  padding-top: var(--spacing-md);
  margin-top: var(--spacing-lg);
}

.document-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

/* Адаптивность */
@media (max-width: 992px) {
  .form-with-preview .row {
    flex-direction: column;
  }
  
  .form-with-preview .col-md-6 {
    width: 100%;
    margin-bottom: var(--spacing-lg);
  }
}
```

### JavaScript функциональность

```javascript
class FormWithPreview {
  constructor() {
    this.form = document.querySelector('.preview-form');
    this.previewTitle = document.getElementById('previewTitle');
    this.previewContent = document.getElementById('previewContent');
    this.init();
  }
  
  init() {
    this.bindEvents();
    this.updatePreview();
  }
  
  bindEvents() {
    const titleField = this.form.querySelector('[name="title"]');
    const contentField = this.form.querySelector('[name="content"]');
    
    titleField.addEventListener('input', () => this.updatePreview());
    contentField.addEventListener('input', () => this.updatePreview());
  }
  
  updatePreview() {
    const titleField = this.form.querySelector('[name="title"]');
    const contentField = this.form.querySelector('[name="content"]');
    
    // Обновляем заголовок
    this.previewTitle.textContent = titleField.value || 'Заголовок документа';
    
    // Обновляем содержимое
    const content = contentField.value || 'Содержимое документа будет отображаться здесь...';
    this.previewContent.innerHTML = this.formatContent(content);
  }
  
  formatContent(content) {
    // Простое форматирование текста
    return content
      .replace(/\n/g, '<br>')
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>');
  }
}

// Инициализация
document.addEventListener('DOMContentLoaded', function() {
  const formWithPreview = document.querySelector('.form-with-preview');
  if (formWithPreview) {
    new FormWithPreview();
  }
});
```

## 4. Паттерн "Dynamic Fields" (Динамические поля)

### Описание
Форма с динамически добавляемыми/удаляемыми полями, полезная для списков лекарств, диагнозов и других повторяющихся данных.

### HTML структура

```html
<div class="dynamic-form">
  <div class="card mt-4" style="z-index: 2;">
    <div class="card-body position-relative">
      <h4 class="card-title mb-4">
        <i class="fas fa-list me-2"></i>Список элементов
      </h4>
      
      <form method="post" class="dynamic-form">
        {% csrf_token %}
        
        <div class="form-section">
          <div class="d-flex justify-content-between align-items-center mb-3">
            <h5 class="section-title mb-0">
              <i class="fas fa-plus-circle me-2"></i>Элементы
            </h5>
            <button type="button" class="btn btn-success btn-sm" id="addField">
              <i class="fas fa-plus me-1"></i>Добавить элемент
            </button>
          </div>
          
          <div class="dynamic-fields" id="dynamicFields">
            <!-- Динамические поля будут добавляться сюда -->
          </div>
        </div>
        
        <div class="form-actions">
          <button type="submit" class="btn btn-primary">
            <i class="fas fa-save me-1"></i>Сохранить
          </button>
        </div>
      </form>
    </div>
  </div>
</div>
```

### CSS стили

```css
/* Динамические поля */
.dynamic-fields {
  margin-bottom: var(--spacing-lg);
}

.dynamic-field {
  background-color: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  padding: var(--spacing-md);
  margin-bottom: var(--spacing-md);
  position: relative;
  transition: all var(--transition-speed) ease;
}

.dynamic-field:hover {
  border-color: var(--primary-color);
  box-shadow: var(--shadow-sm);
}

.dynamic-field-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-md);
}

.field-number {
  font-weight: 600;
  color: var(--primary-color);
  font-size: 0.9rem;
}

.remove-field {
  background: none;
  border: none;
  color: var(--danger-color);
  cursor: pointer;
  padding: var(--spacing-xs);
  border-radius: var(--border-radius-sm);
  transition: all var(--transition-fast) ease;
}

.remove-field:hover {
  background-color: var(--danger-color);
  color: white;
}

.field-content {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: var(--spacing-md);
}

/* Анимации */
.dynamic-field {
  animation: slideIn 0.3s ease;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.dynamic-field.removing {
  animation: slideOut 0.3s ease forwards;
}

@keyframes slideOut {
  to {
    opacity: 0;
    transform: translateY(-10px);
  }
}
```

### JavaScript функциональность

```javascript
class DynamicForm {
  constructor() {
    this.form = document.querySelector('.dynamic-form');
    this.fieldsContainer = document.getElementById('dynamicFields');
    this.addButton = document.getElementById('addField');
    this.fieldCounter = 0;
    this.init();
  }
  
  init() {
    this.bindEvents();
    this.addField(); // Добавляем первое поле
  }
  
  bindEvents() {
    this.addButton.addEventListener('click', () => this.addField());
  }
  
  addField() {
    this.fieldCounter++;
    const fieldHtml = this.createFieldHtml(this.fieldCounter);
    
    const fieldElement = document.createElement('div');
    fieldElement.className = 'dynamic-field';
    fieldElement.innerHTML = fieldHtml;
    
    this.fieldsContainer.appendChild(fieldElement);
    
    // Привязываем событие удаления
    const removeButton = fieldElement.querySelector('.remove-field');
    removeButton.addEventListener('click', () => this.removeField(fieldElement));
    
    // Анимация появления
    fieldElement.style.opacity = '0';
    fieldElement.style.transform = 'translateY(-10px)';
    
    setTimeout(() => {
      fieldElement.style.transition = 'all 0.3s ease';
      fieldElement.style.opacity = '1';
      fieldElement.style.transform = 'translateY(0)';
    }, 10);
  }
  
  removeField(fieldElement) {
    if (this.fieldsContainer.children.length > 1) {
      fieldElement.classList.add('removing');
      
      setTimeout(() => {
        fieldElement.remove();
        this.updateFieldNumbers();
      }, 300);
    } else {
      toastr.warning('Должен быть хотя бы один элемент');
    }
  }
  
  createFieldHtml(number) {
    return `
      <div class="dynamic-field-header">
        <span class="field-number">Элемент ${number}</span>
        <button type="button" class="remove-field" title="Удалить">
          <i class="fas fa-trash"></i>
        </button>
      </div>
      <div class="field-content">
        <div class="form-group">
          <label class="form-label">
            <strong>Название</strong>
          </label>
          <input type="text" name="items[${number}][name]" class="form-control" required>
        </div>
        <div class="form-group">
          <label class="form-label">
            <strong>Количество</strong>
          </label>
          <input type="number" name="items[${number}][quantity]" class="form-control" min="1" required>
        </div>
        <div class="form-group">
          <label class="form-label">
            <strong>Единица</strong>
          </label>
          <select name="items[${number}][unit]" class="form-select" required>
            <option value="">Выберите единицу</option>
            <option value="шт">Штуки</option>
            <option value="мл">Миллилитры</option>
            <option value="мг">Миллиграммы</option>
            <option value="таб">Таблетки</option>
          </select>
        </div>
      </div>
    `;
  }
  
  updateFieldNumbers() {
    const fields = this.fieldsContainer.querySelectorAll('.dynamic-field');
    fields.forEach((field, index) => {
      const numberElement = field.querySelector('.field-number');
      numberElement.textContent = `Элемент ${index + 1}`;
    });
  }
}

// Инициализация
document.addEventListener('DOMContentLoaded', function() {
  const dynamicForm = document.querySelector('.dynamic-form');
  if (dynamicForm) {
    new DynamicForm();
  }
});
```

## Лучшие практики

### 1. Валидация
- Валидируйте поля в реальном времени
- Показывайте понятные сообщения об ошибках
- Используйте цветовую индикацию для статусов полей

### 2. Доступность
- Используйте семантические HTML элементы
- Добавляйте ARIA-атрибуты для динамического контента
- Обеспечивайте клавиатурную навигацию

### 3. Производительность
- Ограничивайте количество динамических полей
- Используйте debounce для частых обновлений
- Оптимизируйте DOM-операции

### 4. UX
- Предоставляйте понятную обратную связь
- Используйте анимации для плавных переходов
- Сохраняйте состояние формы при навигации

---

**Дата создания**: 28.08.2025  
**Версия**: 2.0  
**Статус**: Активные паттерны  
**Основано на**: encounters/detail.html
