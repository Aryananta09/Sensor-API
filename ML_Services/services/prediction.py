import numpy as np
import pandas as pd
from fastapi import HTTPException
from datetime import datetime, timedelta
from ML_Services.db import get_connection
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


def make_prediction(seq_data, models_dict, lokasi: str, room: int, duration: int):
    temp_model, temp_scaler = models_dict["temperature"][room]
    hum_model, hum_scaler = models_dict["humidity"][room]

    X_temp = np.array([d["temperature"] for d in seq_data], dtype=np.float32)
    X_hum = np.array([d["humidity"] for d in seq_data], dtype=np.float32)

    now = datetime.now()
    minute_offset = (5 - (now.minute % 5)) % 5 or 5
    start_time = now.replace(second=0, microsecond=0) + timedelta(minutes=minute_offset)

    predictions = []
    window = 12

    for i in range(duration * 12):
        # Use numpy slicing for last 12 values
        input_temp = X_temp[-window:].reshape(-1, 1)
        input_temp_scaled = temp_scaler.transform(input_temp).reshape(1, window, 1)
        next_temp = temp_model.predict(input_temp_scaled, verbose=0)
        next_temp = temp_scaler.inverse_transform(next_temp)[0][0]

        input_hum = X_hum[-window:].reshape(-1, 1)
        input_hum_scaled = hum_scaler.transform(input_hum).reshape(1, window, 1)
        next_hum = hum_model.predict(input_hum_scaled, verbose=0)
        next_hum = hum_scaler.inverse_transform(next_hum)[0][0]

        pred_time = start_time + timedelta(minutes=5 * i)
        predictions.append({
            "timestamp": pred_time.isoformat(),
            "temperature": round(float(next_temp), 2),
            "humidity": round(float(next_hum), 2)
        })

        # Efficient append
        X_temp = np.append(X_temp, next_temp)
        X_hum = np.append(X_hum, next_hum)

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