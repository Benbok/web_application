// JavaScript для страницы входа МедКарт

document.addEventListener('DOMContentLoaded', function() {
    const form = document.querySelector('form');
    const usernameField = document.getElementById('id_username');
    const passwordField = document.getElementById('id_password');
    const submitBtn = document.querySelector('button[type="submit"]');
    
    // Инициализация анимаций
    initAnimations();
    
    // Автофокус на поле username
    if (usernameField) {
        usernameField.focus();
        addFieldAnimations(usernameField);
    }
    
    // Добавляем анимации для поля пароля
    if (passwordField) {
        addFieldAnimations(passwordField);
    }
    
    // Валидация в реальном времени
    if (usernameField) {
        usernameField.addEventListener('blur', () => validateField(usernameField));
        usernameField.addEventListener('input', () => {
            usernameField.classList.remove('is-invalid');
            hideFieldError(usernameField);
        });
    }
    
    if (passwordField) {
        passwordField.addEventListener('blur', () => validateField(passwordField));
        passwordField.addEventListener('input', () => {
            passwordField.classList.remove('is-invalid');
            hideFieldError(passwordField);
        });
    }
    
    // Обработка отправки формы
    if (form) {
        form.addEventListener('submit', handleFormSubmit);
    }
    
    // Анимация появления формы
    animateFormEntry();
});

// Инициализация анимаций
function initAnimations() {
    // Скрываем прелоадер
    setTimeout(function() {
        const preloader = document.querySelector('.preloader');
        if (preloader) {
            preloader.classList.add('loaded');
        }
    }, 800);
    
    // Анимация плавающих иконок
    animateFloatingIcons();
}

// Анимация появления формы
function animateFormEntry() {
    const loginCard = document.querySelector('.login-card');
    if (loginCard) {
        loginCard.style.opacity = '0';
        loginCard.style.transform = 'translateY(30px)';
        
        setTimeout(() => {
            loginCard.style.transition = 'all 0.8s cubic-bezier(0.4, 0, 0.2, 1)';
            loginCard.style.opacity = '1';
            loginCard.style.transform = 'translateY(0)';
        }, 200);
    }
}

// Анимация плавающих иконок
function animateFloatingIcons() {
    const floatingIcons = document.querySelectorAll('.floating-icon');
    
    floatingIcons.forEach((icon, index) => {
        icon.style.opacity = '0';
        icon.style.transform = 'translateY(50px)';
        
        setTimeout(() => {
            icon.style.transition = 'all 1s cubic-bezier(0.4, 0, 0.2, 1)';
            icon.style.opacity = '1';
            icon.style.transform = 'translateY(0)';
        }, 500 + (index * 200));
    });
}

// Добавление анимаций для полей
function addFieldAnimations(field) {
    field.addEventListener('focus', function() {
        this.parentNode.classList.add('focused');
        animateFieldFocus(this);
    });
    
    field.addEventListener('blur', function() {
        if (!this.value) {
            this.parentNode.classList.remove('focused');
        }
        animateFieldBlur(this);
    });
}

// Анимация фокуса на поле
function animateFieldFocus(field) {
    gsap.to(field, {
        scale: 1.02,
        duration: 0.2,
        ease: 'power2.out'
    });
    
    // Анимация лейбла
    const label = field.parentNode.querySelector('label');
    if (label) {
        gsap.to(label, {
            color: '#667eea',
            duration: 0.3,
            ease: 'power2.out'
        });
    }
}

// Анимация потери фокуса
function animateFieldBlur(field) {
    gsap.to(field, {
        scale: 1,
        duration: 0.2,
        ease: 'power2.out'
    });
    
    // Возвращаем цвет лейбла
    const label = field.parentNode.querySelector('label');
    if (label) {
        gsap.to(label, {
            color: '#2c3e50',
            duration: 0.3,
            ease: 'power2.out'
        });
    }
}

// Валидация поля
function validateField(field) {
    const value = field.value.trim();
    const feedback = field.parentNode.querySelector('.invalid-feedback');
    
    if (!value) {
        field.classList.add('is-invalid');
        if (feedback) {
            showFieldError(field, 'Это поле обязательно для заполнения');
        }
        return false;
    } else {
        field.classList.remove('is-invalid');
        if (feedback) {
            hideFieldError(field);
        }
        return true;
    }
}

// Показать ошибку поля
function showFieldError(field, message) {
    const feedback = field.parentNode.querySelector('.invalid-feedback');
    if (feedback) {
        feedback.textContent = message;
        feedback.style.display = 'block';
        
        // Анимация появления ошибки
        gsap.fromTo(feedback, 
            { opacity: 0, y: -10 },
            { opacity: 1, y: 0, duration: 0.3, ease: 'power2.out' }
        );
    }
}

// Скрыть ошибку поля
function hideFieldError(field) {
    const feedback = field.parentNode.querySelector('.invalid-feedback');
    if (feedback) {
        gsap.to(feedback, {
            opacity: 0,
            y: -10,
            duration: 0.2,
            ease: 'power2.out',
            onComplete: () => {
                feedback.style.display = 'none';
            }
        });
    }
}

// Обработка отправки формы
function handleFormSubmit(e) {
    let isValid = true;
    
    // Валидируем все поля
    const usernameField = document.getElementById('id_username');
    const passwordField = document.getElementById('id_password');
    
    if (usernameField) {
        isValid = validateField(usernameField) && isValid;
    }
    
    if (passwordField) {
        isValid = validateField(passwordField) && isValid;
    }
    
    if (!isValid) {
        e.preventDefault();
        
        // Анимация тряски формы при ошибке
        const loginCard = document.querySelector('.login-card');
        if (loginCard) {
            gsap.to(loginCard, {
                x: -10,
                duration: 0.1,
                repeat: 3,
                yoyo: true,
                ease: 'power2.inOut'
            });
        }
        
        return false;
    }
    
    // Показываем индикатор загрузки
    if (submitBtn) {
        submitBtn.classList.add('loading');
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Вход...';
        submitBtn.disabled = true;
    }
    
    // Анимация успешной отправки
    const loginCard = document.querySelector('.login-card');
    if (loginCard) {
        gsap.to(loginCard, {
            scale: 0.98,
            duration: 0.2,
            ease: 'power2.out'
        });
    }
}

// Анимация при наведении на кнопку
document.addEventListener('DOMContentLoaded', function() {
    const submitBtn = document.querySelector('.btn-primary');
    
    if (submitBtn) {
        submitBtn.addEventListener('mouseenter', function() {
            gsap.to(this, {
                scale: 1.05,
                duration: 0.2,
                ease: 'power2.out'
            });
        });
        
        submitBtn.addEventListener('mouseleave', function() {
            gsap.to(this, {
                scale: 1,
                duration: 0.2,
                ease: 'power2.out'
            });
        });
    }
});

// Анимация при наведении на поля
document.addEventListener('DOMContentLoaded', function() {
    const formControls = document.querySelectorAll('.form-control');
    
    formControls.forEach(control => {
        control.addEventListener('mouseenter', function() {
            if (!this.classList.contains('focused')) {
                gsap.to(this, {
                    y: -2,
                    duration: 0.2,
                    ease: 'power2.out'
                });
            }
        });
        
        control.addEventListener('mouseleave', function() {
            if (!this.classList.contains('focused')) {
                gsap.to(this, {
                    y: 0,
                    duration: 0.2,
                    ease: 'power2.out'
                });
            }
        });
    });
});

// Анимация чекбокса
document.addEventListener('DOMContentLoaded', function() {
    const checkbox = document.getElementById('id_remember_me');
    
    if (checkbox) {
        checkbox.addEventListener('change', function() {
            if (this.checked) {
                gsap.to(this, {
                    scale: 1.2,
                    duration: 0.1,
                    yoyo: true,
                    repeat: 1,
                    ease: 'power2.out'
                });
            }
        });
    }
});

// Параллакс эффект для фона
document.addEventListener('DOMContentLoaded', function() {
    const backgroundElements = document.querySelector('.background-elements');
    
    if (backgroundElements) {
        document.addEventListener('mousemove', function(e) {
            const mouseX = e.clientX / window.innerWidth;
            const mouseY = e.clientY / window.innerHeight;
            
            const floatingIcons = document.querySelectorAll('.floating-icon');
            
            floatingIcons.forEach((icon, index) => {
                const speed = (index + 1) * 0.5;
                const x = (mouseX - 0.5) * speed * 20;
                const y = (mouseY - 0.5) * speed * 20;
                
                gsap.to(icon, {
                    x: x,
                    y: y,
                    duration: 1,
                    ease: 'power2.out'
                });
            });
        });
    }
});

// Анимация появления уведомлений
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} notification-toast`;
    notification.innerHTML = `
        <i class="fas fa-${type === 'success' ? 'check-circle' : 'info-circle'} me-2"></i>
        ${message}
    `;
    
    document.body.appendChild(notification);
    
    // Анимация появления
    gsap.fromTo(notification, 
        { opacity: 0, y: -50, scale: 0.8 },
        { opacity: 1, y: 0, scale: 1, duration: 0.5, ease: 'back.out(1.7)' }
    );
    
    // Автоматическое скрытие
    setTimeout(() => {
        gsap.to(notification, {
            opacity: 0,
            y: -50,
            scale: 0.8,
            duration: 0.3,
            ease: 'power2.in',
            onComplete: () => {
                document.body.removeChild(notification);
            }
        });
    }, 3000);
}

// Добавляем стили для уведомлений
const notificationStyles = document.createElement('style');
notificationStyles.textContent = `
    .notification-toast {
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 9999;
        min-width: 300px;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
        border-radius: 12px;
        border: none;
    }
    
    .focused .form-control {
        border-color: #667eea;
        box-shadow: 0 0 0 4px rgba(102, 126, 234, 0.1);
    }
`;
document.head.appendChild(notificationStyles);

