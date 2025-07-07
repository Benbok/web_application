document.addEventListener('DOMContentLoaded', function () {
  const buttons = document.querySelectorAll('.add-assignment-btn');
  buttons.forEach(button => {
    button.addEventListener('click', () => {
      alert('Добавление назначения...');
    });
  });
});
