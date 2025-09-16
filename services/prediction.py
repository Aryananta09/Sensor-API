import numpy as np
import pandas as pd
from fastapi import HTTPException
from datetime import datetime, timedelta
from api.db import get_connection
from collections import defaultdict

TABLE_MAP = {
    "kebalen": "server_kebalen",
    "gayungan": "server_gayungan"
}

PREDICTION_TABLE_MAP = {
    "kebalen": "predictions_kebalen",
    "gayungan": "predictions_gayungan"
}

ROOM_MAP = {
    1: "ROOM1",
    2: "ROOM2",
    3: "ROOM3",
    4: "ROOM4",
    5: "ROOM5"
}

def get_sensor_data(location: str, room: int, duration_hours: int):

    table = TABLE_MAP.get(location)
    if not table:
        raise ValueError("Unknown location")
    
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    room_name = ROOM_MAP.get(room)
    if not room_name:
        raise ValueError("Invalid room number")

    # total data per sensor = duration_hours * 12 (karena 12 data per jam)
    limit = duration_hours * 12

    sql = f"""
        SELECT sensor_id, time_id, temperature, humidity
        FROM {table}
        WHERE room_id = %s
        ORDER BY time_id DESC
    """
    cursor.execute(sql, (room_name,))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    if not rows:
        return []

    # convert ke DataFrame biar gampang proses
    df = pd.DataFrame(rows)

    # ambil N data terakhir per sensor
    df_sorted = df.sort_values(["sensor_id", "time_id"], ascending=[True, False])
    df_limited = df_sorted.groupby("sensor_id").head(limit)

    return df_limited


def average_by_interval(raw_data):
    df = pd.DataFrame(raw_data, columns=["sensor_id", "time_id", "temperature", "humidity"])
    df["time_id"] = pd.to_datetime(df["time_id"])

    # Buat kolom pembulatan ke 5 menit
    df["timestamp_5min"] = df["time_id"].dt.floor("5min")

    # Groupby lalu ambil rata-rata
    avg_df = (
        df.groupby("timestamp_5min")[["temperature", "humidity"]]
        .mean()
        .reset_index()
        .sort_values("timestamp_5min")
    )

    return avg_df


def make_prediction(seq_data, models_dict, lokasi: str, room: int, duration: int):
    # Ambil model & scaler
    temp_model, temp_scaler = models_dict["temperature"][room]
    hum_model, hum_scaler = models_dict["humidity"][room]

    # Ambil data input
    X_temp = [d["temperature"] for d in seq_data]
    X_hum = [d["humidity"] for d in seq_data]

    # Tentukan start time
    now = datetime.now()
    minute_offset = (5 - (now.minute % 5)) % 5 or 5
    start_time = now.replace(second=0, microsecond=0) + timedelta(minutes=minute_offset)

    predictions = []
    for i in range(duration * 12):  # tiap 5 menit
        # Temperature
        input_temp = np.array(X_temp[-12:]).reshape(-1, 1)
        input_temp_scaled = temp_scaler.transform(input_temp).reshape(1, input_temp.shape[0], 1)
        next_temp = temp_scaler.inverse_transform(temp_model.predict(input_temp_scaled, verbose=0))[0][0]

        # Humidity
        input_hum = np.array(X_hum[-12:]).reshape(-1, 1)
        input_hum_scaled = hum_scaler.transform(input_hum).reshape(1, input_hum.shape[0], 1)
        next_hum = hum_scaler.inverse_transform(hum_model.predict(input_hum_scaled, verbose=0))[0][0]

        pred_time = start_time + timedelta(minutes=5 * i)
        predictions.append({
            "timestamp": pred_time.isoformat(),
            "temperature": round(float(next_temp), 2),
            "humidity": round(float(next_hum), 2)
        })

        X_temp.append(next_temp)
        X_hum.append(next_hum)

    return {"room": room, "predictions": predictions}


def save_predictions(location: str, room: int, predictions: list):
    table = PREDICTION_TABLE_MAP[location]
    room_name = ROOM_MAP.get(room, f"ROOM{room}")  # fallback kalau ga ada

    conn = get_connection()
    cursor = conn.cursor()

    sql = f"""
        INSERT INTO {table} (room, predicted_temp, predicted_humid, predicted_time, created_at)
        VALUES (%s, %s, %s, %s, %s)
    """

    now = datetime.now()
    for pred in predictions:
        cursor.execute(sql, (
            room_name,                 # room string (ex: ROOM1)
            pred["temperature"],       # simpan temperature
            pred["humidity"],          # simpan humidity
            pred["timestamp"],         # simpan timestamp prediksi
            now                        # created_at
        ))

    conn.commit()
    cursor.close()
    conn.close()