import numpy as np
import pandas as pd
from fastapi import HTTPException
from datetime import datetime, timedelta
from api.db import supabase
from collections import defaultdict


def predict_future(model, scaler, seq_scaled, steps):
    preds_scaled = []
    current_seq = seq_scaled.copy()

    for _ in range(steps):
        pred = model.predict(current_seq.reshape(1, len(current_seq), current_seq.shape[1]), verbose=0)
        preds_scaled.append(pred[0])
        current_seq = np.vstack([current_seq[1:], pred])

    return scaler.inverse_transform(np.array(preds_scaled)).tolist()

def make_prediction(request, models_dict, lokasi: str):
    room = request.room
    duration = request.duration_hours
    seq = request.sequence

    # Ambil model & scaler untuk temperature dan humidity
    temp_model, temp_scaler = models_dict["temperature"][room]
    hum_model, hum_scaler = models_dict["humidity"][room]

    # Ambil data input (temperature & humidity) pakai dot notation
    X_temp = [d.temperature for d in seq]
    X_hum = [d.humidity for d in seq]

    predictions = []

    for i in range(duration * 12):  # tiap 5 menit
        # ---- Temperature ----
        input_temp = np.array(X_temp[-12:]).reshape(-1, 1)
        input_temp_scaled = temp_scaler.transform(input_temp)
        input_temp_scaled = input_temp_scaled.reshape(1, input_temp_scaled.shape[0], 1)

        next_temp_scaled = temp_model.predict(input_temp_scaled, verbose=0)
        next_temp = temp_scaler.inverse_transform(next_temp_scaled)[0][0]

        # ---- Humidity ----
        input_hum = np.array(X_hum[-12:]).reshape(-1, 1)
        input_hum_scaled = hum_scaler.transform(input_hum)
        input_hum_scaled = input_hum_scaled.reshape(1, input_hum_scaled.shape[0], 1)

        next_hum_scaled = hum_model.predict(input_hum_scaled, verbose=0)
        next_hum = hum_scaler.inverse_transform(next_hum_scaled)[0][0]

        predictions.append({
            "step": i + 1,
            "temperature": round(float(next_temp), 2),
            "humidity": round(float(next_hum), 2)
        })

        X_temp.append(next_temp)
        X_hum.append(next_hum)

    return {
        "room": room,
        "predictions": predictions
    }



def save_predictions(lokasi, room, predictions):
    for p in predictions:
        step = p["step"]
        temp = p["temperature"]
        hum = p["humidity"]

        # sementara print dulu
        print(f"[{lokasi}] Room {room} - Step {step}: Temp={temp}, Hum={hum}")

        # TODO: kalau mau simpan ke database atau file, tambahin query insert di sini



# ROOM_MAP = {
#     1: "ROOM1",
#     2: "ROOM2",
#     3: "ROOM3",
#     4: "ROOM4",
#     5: "ROOM5"
# }

# def fetch_data(location: str, room: int, hours: int):
#     table_name = location
#     room_str = ROOM_MAP.get(room)
#     if not room_str:
#         raise ValueError(f"Invalid room: {room}")

#     records_needed = hours * 12  # 12 record per jam (5 menit sekali)

#     # Ambil semua data dalam room (urut berdasarkan waktu terbaru → lama)
#     response = (
#         supabase.table(table_name)
#         .select("*")
#         .eq("room_id", room_str)
#         .order("time_id", desc=True)  # pakai timestamp asli
#         .execute()
#     )

#     all_data = response.data

#     # Group by sensor_id
#     grouped = defaultdict(list)
#     for row in all_data:
#         grouped[row["sensor_id"]].append(row)

#     # Ambil N terakhir dari tiap sensor, urutkan lama → baru
#     merged = []
#     for rows in grouped.values():
#         latest = list(reversed(rows[:records_needed]))
#         merged.extend(latest)

#     return merged


# def process_avg_per_5min(data: list):
#     """Proses data mentah → rata-rata per 5 menit"""
#     if not data:
#         return []

#     df = pd.DataFrame(data)

#     # Pastikan kolom timestamp benar
#     df["timestamp"] = pd.to_datetime(df["time_id"])

#     # Bulatkan ke 5 menit
#     df["timestamp_5min"] = df["timestamp"].dt.floor("5min")

#     # Rata-rata suhu (kalau mau humidity juga bisa ditambah)
#     avg_df = df.groupby("timestamp_5min")["temperature"].mean().reset_index()

#     return avg_df.to_dict(orient="records")