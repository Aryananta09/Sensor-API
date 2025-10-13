// Room map
const ROOM_MAP = {
  gayungan: {
    ROOM1: ["DHT1","DHT2","DHT3","DHT4"],
    ROOM2: ["DHT5"],
    ROOM3: ["DHT6"],
    ROOM4: ["DHT7","DHT8","DHT9"],
    ROOM5: ["DHT10","DHT11","DHT12"]
  },
  kebalen: {
    ROOM1: ["DHT1","DHT2","DHT3","DHT4"],
    ROOM2: ["DHT5","DHT6"]
  }
};

// Sidebar nav toggle
document.querySelectorAll(".sidebar nav ul li").forEach(li => {
  li.addEventListener("click", () => {
    document.querySelectorAll(".sidebar nav ul li").forEach(x => x.classList.remove("active"));
    li.classList.add("active");
    document.querySelectorAll(".section").forEach(sec => sec.classList.remove("active"));
    document.getElementById(li.dataset.target).classList.add("active");
  });
});

/* ---------------- Dashboard Existing ---------------- */
const serverSelect = document.getElementById("serverSelect");
const roomSelect = document.getElementById("roomSelect");
const sensorSelect = document.getElementById("sensorSelect");
const tempNowEl = document.getElementById("tempNow");
const humNowEl = document.getElementById("humNow");
const classNowEl = document.getElementById("classNow");

function populateRoomsAndSensors() {
  const loc = serverSelect.value;
  roomSelect.innerHTML = `<option value="" selected disabled>Pilih Room</option>`;
  sensorSelect.innerHTML = `<option value="" selected disabled>Pilih Sensor</option>`;
  if (!loc) return;
  const rooms = Object.keys(ROOM_MAP[loc]);
  rooms.forEach(r => {
    const o = document.createElement("option");
    o.value = r;
    o.textContent = r;
    roomSelect.appendChild(o);
  });
}

function updateSensors() {
  const loc = serverSelect.value;
  const room = roomSelect.value;
  sensorSelect.innerHTML = `<option value="" selected disabled>Pilih Sensor</option>`;
  if (!loc || !room) return;

  const allOpt = document.createElement("option");
  allOpt.value = "ALL";
  allOpt.textContent = "All Sensor";
  sensorSelect.appendChild(allOpt);

  ROOM_MAP[loc][room].forEach(s => {
    const o = document.createElement("option");
    o.value = s;
    o.textContent = s;
    sensorSelect.appendChild(o);
  });

  sensorSelect.value = "ALL";
}

const tempCtx = document.getElementById("tempChart").getContext("2d");
const humCtx = document.getElementById("humChart").getContext("2d");

const tempChart = new Chart(tempCtx, {
  type: 'line',
  data: { labels: [], datasets: [{ label: 'Temp (°C)', data: [], borderColor: 'lime', backgroundColor: 'rgba(0,255,0,0.06)', fill: true }] },
  options: { responsive: true, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: false } } }
});
const humChart = new Chart(humCtx, {
  type: 'line',
  data: { labels: [], datasets: [{ label: 'Humidity (%)', data: [], borderColor: 'salmon', backgroundColor: 'rgba(255,100,100,0.06)', fill: true }] },
  options: { responsive: true, plugins: { legend: { display: false } } }
});

async function fetchDashboard() {
  const location = serverSelect.value;
  const room = roomSelect.value;
  const sensor = sensorSelect.value;
  if (!location || !room || !sensor) return;

  const endpoint = `http://127.0.0.1:8000/dashboard-data?location=${location}&room=${room}&sensor=${sensor}&points=12`;
  try {
    const res = await fetch(endpoint);
    if (!res.ok) return;
    const json = await res.json();
    if (!json.latest) return;

    tempNowEl.textContent = `${Number(json.latest.temperature).toFixed(1)} °C`;
    humNowEl.textContent = `${Number(json.latest.humidity).toFixed(1)} %`;
    classNowEl.textContent = json.latest.class || "Normal";

    const cls = json.latest.class;
    const colorMap = { Anomali:"#666", Normal:"#2a9d2a", Minor:"#ff9f00", Major:"#ff6b00", Critical:"#e53935" };
    classNowEl.style.color = colorMap[cls] || "#222";

    const labels = json.history.map(h => new Date(h.timestamp).toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'}));
    const temps = json.history.map(h => h.temperature);
    const hums = json.history.map(h => h.humidity);

    tempChart.data.labels = labels;
    tempChart.data.datasets[0].data = temps;
    tempChart.update();

    humChart.data.labels = labels;
    humChart.data.datasets[0].data = hums;
    humChart.update();

  } catch (err) {
    console.error("fetchDashboard error", err);
  }
}
serverSelect.addEventListener("change", () => {
  populateRoomsAndSensors();
  tempNowEl.textContent = "-- °C";
  humNowEl.textContent = "-- %";
  classNowEl.textContent = "--";
});
roomSelect.addEventListener("change", () => {
  updateSensors();
  
  setTimeout(() => {
    fetchDashboard();
  }, 100); 
});
sensorSelect.addEventListener("change", fetchDashboard);
setInterval(fetchDashboard, 10000);

/* ---------------- Future Prediction ---------------- */
const fpServerSelect = document.getElementById("fpServerSelect");
const fpRoomSelect = document.getElementById("fpRoomSelect");
const fpDurationSelect = document.getElementById("fpDurationSelect");
const fpPredictBtn = document.getElementById("fpPredictBtn");
const fpResult = document.getElementById("fpResult");

function populateFpRooms() {
  const loc = fpServerSelect.value;
  fpRoomSelect.innerHTML = `<option value="" selected disabled>Pilih Room</option>`;
  if (!loc) return;
  Object.keys(ROOM_MAP[loc]).forEach(r => {
    const o = document.createElement("option");
    o.value = r;
    o.textContent = r;
    fpRoomSelect.appendChild(o);
  });
}
fpServerSelect.addEventListener("change", populateFpRooms);

const fpTempCtx = document.getElementById("fpTempChart").getContext("2d");
const fpHumCtx = document.getElementById("fpHumChart").getContext("2d");

const fpTempChart = new Chart(fpTempCtx, {
  type: 'line',
  data: { labels: [], datasets: [{ label: 'Pred Temp (°C)', data: [], borderColor: '#00e676', backgroundColor: 'rgba(0,230,118,0.06)', fill: true }] },
  options: { responsive: true, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: false } } }
});
const fpHumChart = new Chart(fpHumCtx, {
  type: 'line',
  data: { labels: [], datasets: [{ label: 'Pred Humidity (%)', data: [], borderColor: '#ff4081', backgroundColor: 'rgba(255,64,129,0.06)', fill: true }] },
  options: { responsive: true, plugins: { legend: { display: false } } }
});

fpPredictBtn.addEventListener("click", async () => {
  const loc = fpServerSelect.value;
  const room = fpRoomSelect.value;
  const duration = parseInt(fpDurationSelect.value);
  if (!loc || !room || !duration) {
    alert("Lengkapi pilihan dulu!");
    return;
  }

  const endpoint = loc === "kebalen" ? "http://127.0.0.1:8001/predict-kebalen" : "http://127.0.0.1:8001/predict-gayungan";
  const body = { room: parseInt(room.replace("ROOM", "")), duration_hours: duration };

  try {
    const res = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    });
    if (!res.ok) throw new Error("Request gagal");
    const json = await res.json();

    const preds = json.prediction_result.predictions;
    const labels = preds.map(p => new Date(p.timestamp).toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'}));
    const temps = preds.map(p => p.temperature);
    const hums = preds.map(p => p.humidity);

    fpTempChart.data.labels = labels;
    fpTempChart.data.datasets[0].data = temps;
    fpTempChart.update();

    fpHumChart.data.labels = labels;
    fpHumChart.data.datasets[0].data = hums;
    fpHumChart.update();

    // --- Tambahan tabel prediksi ---
    const tableContainer = document.getElementById("fpTable");
    tableContainer.innerHTML = `
      <table border="1" cellspacing="0" cellpadding="4" style="margin-top:10px;width:100%;text-align:center;">
        <thead>
          <tr style="background:#f4f4f4;">
            <th>Waktu</th>
            <th>Suhu (°C)</th>
            <th>Kelembapan (%)</th>
          </tr>
        </thead>
        <tbody>
          ${preds.map(p => `
            <tr>
              <td>${new Date(p.timestamp).toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'})}</td>
              <td>${Number(p.temperature).toFixed(1)}</td>
              <td>${Number(p.humidity).toFixed(1)}</td>
            </tr>
          `).join("")}
        </tbody>
      </table>
    `;
    // --- END tabel ---

    fpResult.classList.remove("hidden");
    fpPredictBtn.textContent = "Hide Prediction";

    fpPredictBtn.onclick = () => {
      fpResult.classList.add("hidden");
      fpPredictBtn.textContent = "Predict";
      fpPredictBtn.onclick = null;
      fpPredictBtn.addEventListener("click", arguments.callee);
    };

  } catch (err) {
    console.error("Prediction error", err);
    alert("Gagal memuat prediksi");
  }
});
