document.addEventListener('DOMContentLoaded', function() {
    const calendarEl = document.getElementById('calendar');
    const doctorSelector = document.getElementById('doctorSelector');

    const bookedAppointmentsSource = {
        id: 'booked',
        url: window.bookedAppointmentsUrl,
        color: '#dc3545',
        textColor: 'white'
    };
    const availableSlotsSource = {
        id: 'available',
        url: ''
    };

    const calendar = new FullCalendar.Calendar(calendarEl, {
        initialView: 'timeGridDay',
        headerToolbar: {
            left: 'prev,next today',
            center: 'title',
            right: 'dayGridMonth,timeGridWeek,timeGridDay'
        },
        timeZone: 'local',
        locale: 'ru',
        selectable: true,
        slotMinTime: "08:00:00",
        slotMaxTime: "20:00:00",
        allDaySlot: false,
        firstDay: 1,
        height: 900,
        slotDuration: '00:30:00',
        scrollTime: '08:00:00',
        expandRows: true,
        eventSources: [ bookedAppointmentsSource ],

        eventDidMount: function(info) {
                const status = info.event.extendedProps.status;

                if (status === 'completed') {
                    info.el.style.backgroundColor = '#6c757d';
                    info.el.style.textDecoration = 'line-through';
                } else if (status === 'canceled') {
                    info.el.style.backgroundColor = '#28a745';
                    info.el.style.textDecoration = 'none';
                } else if (status === 'scheduled') {
                    info.el.style.backgroundColor = '#dc3545';
                    info.el.style.textDecoration = 'none';
                } else {
                    console.warn('Неизвестный статус:', status);
                }
            },

        eventClick(info) {
            if (info.event.backgroundColor === '#28a745') {
                // Свободный слот → открыть создание записи
                const startTime = info.event.start.toISOString();
                const scheduleId = info.event.extendedProps.schedule_id;
                const createUrl = `${window.createAppointmentUrl}?start=${startTime}&schedule_id=${scheduleId}`;
                window.location.href = createUrl;
            } else {
                // Занятая запись → открыть детальную информацию
                const detailUrl = window.detailAppointmentUrl.replace('__ID__', info.event.id);
                window.location.href = detailUrl;
            }
        }
    });

    calendar.render();

    function loadScheduleForDoctor(doctorId) {
    // Удаляем ВСЕ события
    calendar.getEventSources().forEach(source => source.remove());

    if (doctorId && doctorId !== "__all_free__") {
        // Для конкретного врача — и занятые, и свободные
        calendar.addEventSource({
            id: 'booked',
            url: `${window.bookedAppointmentsUrl}?doctor=${doctorId}`,
            color: '#dc3545',
            textColor: 'white'
        });
        calendar.addEventSource({
            id: 'available',
            url: `${window.availableSlotsBaseUrl}?doctor_id=${doctorId}`
        });
    } else if (doctorId === "__all_free__") {
        // Только свободные слоты для всех врачей
        calendar.addEventSource({
            id: 'available',
            url: window.availableSlotsBaseUrl
        });
    } else {
        // Только занятые слоты для всех врачей
        calendar.addEventSource({
            id: 'booked',
            url: window.bookedAppointmentsUrl,
            color: '#dc3545',
            textColor: 'white'
        });
    }
    calendar.refetchEvents();
}


    doctorSelector.addEventListener('change', function() {
        const doctorId = this.value;
        localStorage.setItem('selectedDoctorId', doctorId);
        loadScheduleForDoctor(doctorId);
    });

    const savedDoctorId = localStorage.getItem('selectedDoctorId');
    if (savedDoctorId) {
        doctorSelector.value = savedDoctorId;
        loadScheduleForDoctor(savedDoctorId);
    }

    const createBtn = document.getElementById('createAppointmentBtn');
    if (createBtn) {
        createBtn.addEventListener('click', function(e){
            e.preventDefault();
            const doctorId = doctorSelector.value;
            if (!doctorId) {
                alert("Пожалуйста, сначала выберите врача, чтобы увидеть его расписание.");
            } else {
                alert("Выберите свободный зеленый слот в календаре, чтобы записаться.");
            }
        });
    }
});
