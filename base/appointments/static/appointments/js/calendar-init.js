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
        initialView: 'timeGridWeek',
        headerToolbar: {
            left: 'prev,next today',
            center: 'title',
            right: 'dayGridMonth,timeGridWeek'
        },
        locale: 'ru',
        selectable: true,
        slotMinTime: "08:00:00",
        slotMaxTime: "20:00:00",
        allDaySlot: false,
        firstDay: 1,
        eventSources: [ bookedAppointmentsSource ],

        eventClick(info) {
            if (info.event.backgroundColor === '#28a745') {
                const startTime = info.event.start.toISOString();
                const scheduleId = info.event.extendedProps.schedule_id;
                const createUrl = `${window.createAppointmentUrl}?start=${startTime}&schedule_id=${scheduleId}`;
                window.location.href = createUrl;
            }
        }
    });

    calendar.render();

    function loadScheduleForDoctor(doctorId) {
        const oldSource = calendar.getEventSourceById('available');
        if (oldSource) {
            oldSource.remove();
        }
        if (doctorId) {
            availableSlotsSource.url = `${window.availableSlotsBaseUrl}?doctor_id=${doctorId}`;
            calendar.addEventSource(availableSlotsSource);
        }
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

    document.getElementById('createAppointmentBtn').addEventListener('click', function(e){
        e.preventDefault();
        const doctorId = doctorSelector.value;
        if (!doctorId) {
            alert("Пожалуйста, сначала выберите врача, чтобы увидеть его расписание.");
        } else {
            alert("Выберите свободный зеленый слот в календаре, чтобы записаться.");
        }
    });
});
