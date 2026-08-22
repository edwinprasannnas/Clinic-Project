const API_BASE = "https://willow-clinic-api.onrender.com";
const week = [
    {d:'Mon', open:8, close:20},
    {d:'Tue', open:8, close:20},
    {d:'Wed', open:8, close:20},
    {d:'Thu', open:8, close:20},
    {d:'Fri', open:8, close:20},
    {d:'Sat', open:9, close:17},
    {d:'Sun', open:null, close:null},
];
  const rangeStart = 8, rangeEnd = 20, span = rangeEnd - rangeStart;
  const rowsEl = document.getElementById('rhythmRows');
  week.forEach(day => {
    const row = document.createElement('div');
    row.className = 'rhythm-row';
    let barHtml = '';
    if(day.open !== null){
      const left = ((day.open - rangeStart)/span)*100;
      const width = ((day.close - day.open)/span)*100;
      barHtml = `<div class="rhythm-bar" style="left:${left}%;width:${width}%;"></div>`;
    }
    row.innerHTML = `<span class="day">${day.d}</span><div class="rhythm-track">${barHtml}</div>`;
    rowsEl.appendChild(row);
  });

  const overlay = document.getElementById('modalOverlay');
  const formView = document.getElementById('formView');
  const confirmView = document.getElementById('confirmView');

  function openModal(doctorName){
    formView.style.display = 'block';
    confirmView.style.display = 'none';
    document.getElementById('bookingForm').reset();
    if(doctorName){
      document.getElementById('doctor').value = doctorName;
    }
    overlay.classList.add('open');
    document.body.style.overflow = 'hidden';
    document.getElementById('name').focus();
  }
  function closeModal(){
    overlay.classList.remove('open');
    document.body.style.overflow = '';
  }
  async function submitForm(e){
  e.preventDefault();
  const payload = {
    name: document.getElementById('name').value,
    phone: document.getElementById('phone').value,
    date: document.getElementById('date').value,
    service: document.getElementById('service').value,
    doctor: document.getElementById('doctor').value || null,
  };

  const btn = e.target.querySelector('button[type="submit"]');
  btn.disabled = true; btn.textContent = 'Sending…';

  try {
    const res = await fetch(`${API_BASE}/api/bookings`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail?.[0]?.msg || 'Could not book this slot');
    }
    document.getElementById('confirmText').textContent =
      `Thanks, ${payload.name}. Your request for ${payload.service} has been noted — we'll call to confirm your slot.`;
    formView.style.display = 'none';
    confirmView.style.display = 'block';
  } catch (err) {
    alert(err.message);
  } finally {
    btn.disabled = false; btn.textContent = 'Request Appointment';
  }
}
  document.addEventListener('keydown', (e) => {
    if(e.key === 'Escape') closeModal();
  });