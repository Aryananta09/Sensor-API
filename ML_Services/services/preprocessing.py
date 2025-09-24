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
