from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from backend.db import get_connection
from datetime import datetime
import traceback
import logging

logger = logging.getLogger("uvicorn.error")

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
    sensor: str = Query(..., description="sensor id e.g. DHT1 or ALL"),
    points: int = Query(12, description="max number of history points (default 12)")
):
    # validation
    if location not in ROOM_MAP or location not in TABLE_MAP:
        raise HTTPException(status_code=400, detail="Invalid location")

    if room not in ROOM_MAP[location]:
        raise HTTPException(status_code=400, detail="Invalid room for this location")

    sensors_in_room = ROOM_MAP[location][room]
    if not sensors_in_room:
        raise HTTPException(status_code=400, detail="No sensors configured for this room")

    if sensor != "ALL" and sensor not in sensors_in_room:
        raise HTTPException(status_code=400, detail="Invalid sensor for this room")

    conn = get_connection()
    if conn is None:
        raise HTTPException(status_code=500, detail="DB connection failed")

    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)

        # use mapped table name
        table_name = TABLE_MAP[location]

        if sensor == "ALL":
            placeholders = ",".join(["%s"] * len(sensors_in_room))
            query = f"""
                SELECT time_id,
                       AVG(temperature) AS temperature,
                       AVG(humidity)    AS humidity
                FROM `{table_name}`
                WHERE sensor_id IN ({placeholders})
                GROUP BY time_id
                ORDER BY time_id DESC
                LIMIT %s
            """
            params = tuple(sensors_in_room) + (points,)
            cursor.execute(query, params)
        else:
            query = f"""
                SELECT time_id, temperature, humidity
                FROM `{table_name}`
                WHERE sensor_id = %s
                ORDER BY time_id DESC
                LIMIT %s
            """
            cursor.execute(query, (sensor, points))

        rows = cursor.fetchall() or []
        rows = list(reversed(rows))

        if not rows:
            return {"latest": None, "history": []}

        history = []
        for r in rows:
            ts = r.get("time_id")
            try:
                iso = ts.isoformat() if hasattr(ts, "isoformat") else str(ts)
            except Exception:
                iso = str(ts)
            history.append({
                "timestamp": iso,
                "temperature": float(r.get("temperature") or 0.0),
                "humidity": float(r.get("humidity") or 0.0)
            })

        latest_row = history[-1]
        temp = latest_row["temperature"]

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

        return {
            "latest": {
                "temperature": latest_row["temperature"],
                "humidity": latest_row["humidity"],
                "class": temp_class,
                "timestamp": latest_row["timestamp"]
            },
            "history": history
        }

    except Exception as e:
        tb = traceback.format_exc()
        logger.error("Error in /dashboard-data: %s\n%s", str(e), tb)
        raise HTTPException(status_code=500, detail="Internal server error. Check server logs for details.")
    finally:
        try:
            if cursor:
                cursor.close()
            conn.close()
        except Exception:
            pass