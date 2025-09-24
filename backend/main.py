from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from backend.db import get_connection
from datetime import datetime

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TABLE_MAP = {
    "kebalen": "server_kebalen",
    "gayungan": "server_gayungan"
}

ROOM_MAP = {
    "gayungan": {
        "ROOM1": ["DHT1", "DHT2", "DHT3", "DHT4"],
        "ROOM2": ["DHT5"],
        "ROOM3": ["DHT6"],
        "ROOM4": ["DHT7", "DHT8", "DHT9"],
        "ROOM5": ["DHT10", "DHT11", "DHT12"]
    },
    "kebalen": {
        "ROOM1": ["DHT1", "DHT2", "DHT3", "DHT4"],
        "ROOM2": ["DHT5", "DHT6"]
    }
}

@app.get("/")
def root():
    return {"message": "backend is running"}

@app.get("/dashboard-data")
def get_dashboard_data(
    location: str = Query(..., description="kebalen or gayungan"),
    room: str = Query(..., description="room id e.g. ROOM1"),
    sensor: str = Query(..., description="sensor id e.g. DHT1"),
    points: int = Query(12, description="max number of history points (default 12)")
):
    # pastikan location valid
    if location not in TABLE_MAP:
        raise HTTPException(status_code=400, detail="Invalid location")

    table = TABLE_MAP[location]  # <-- ambil nama tabel sesuai mapping

    # validasi room
    if room not in ROOM_MAP[location]:
        raise HTTPException(status_code=400, detail="Invalid room for this location")

    # validasi sensor
    if sensor not in ROOM_MAP[location][room]:
        raise HTTPException(status_code=400, detail="Invalid sensor for this room")

    conn = get_connection()
    if conn is None:
        raise HTTPException(status_code=500, detail="DB connection failed")

    try:
        cursor = conn.cursor(dictionary=True)

        query = f"""
            SELECT time_id, temperature, humidity
            FROM `{table}`
            WHERE sensor_id = %s
            ORDER BY time_id DESC
            LIMIT %s
        """
        cursor.execute(query, (sensor, points))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        if not rows:
            return {"latest": None, "history": []}

        # reverse ASC
        rows = list(reversed(rows))
        latest_row = rows[-1]
        temp = latest_row["temperature"]

        # klasifikasi
        if temp <= 10:
            temp_class = "Anomali"
        elif 11 <= temp <= 25:
            temp_class = "Normal"
        elif 26 <= temp <= 27:
            temp_class = "Minor"
        elif 28 <= temp <= 29:
            temp_class = "Major"
        else:
            temp_class = "Critical"

        history = [
            {
                "timestamp": (r["time_id"].isoformat() if isinstance(r["time_id"], datetime) else str(r["time_id"])),
                "temperature": r["temperature"],
                "humidity": r["humidity"]
            }
            for r in rows
        ]

        return {
            "latest": {
                "temperature": latest_row["temperature"],
                "humidity": latest_row["humidity"],
                "class": temp_class,
                "timestamp": history[-1]["timestamp"]
            },
            "history": history
        }

    except Exception as e:
        try:
            cursor.close()
            conn.close()
        except:
            pass
        raise HTTPException(status_code=500, detail=str(e))