import joblib
from tensorflow.keras.models import load_model
from tensorflow.keras.losses import MeanSquaredError

# ------------------------------
# Path model & scaler per lokasi
# ------------------------------
MODEL_KEBALEN = {
    "temperature": {
        1: "model/lstm_temperature_room1_kebalen_callback.h5",
        2: "model/lstm_temperature_room2_kebalen_callback.h5",
    },
    "humidity": {
        1: "model/lstm_humidity_room1_kebalen_callback.h5",
        2: "model/lstm_humidity_room2_kebalen_callback.h5",
    },
}

SCALER_KEBALEN = {
    "temperature": {
        1: "model/scaler_temperature_room1_kebalen.pkl",
        2: "model/scaler_temperature_room2_kebalen.pkl",
    },
    "humidity": {
        1: "model/scaler_humidity_room1_kebalen.pkl",
        2: "model/scaler_humidity_room2_kebalen.pkl",
    },
}

MODEL_GAYUNGAN = {
    "temperature": {
        1: "model/lstm_temperature_room1_gayungan_callback.h5",
        2: "model/lstm_temperature_room2_gayungan_callback.h5",
        3: "model/lstm_temperature_room3_gayungan_callback.h5",
        4: "model/lstm_temperature_room4_gayungan_callback.h5",
        5: "model/lstm_temperature_room5_gayungan_callback.h5",
    },
    "humidity": {
        1: "model/lstm_humidity_room1_gayungan_callback.h5",
        2: "model/lstm_humidity_room2_gayungan_callback.h5",
        3: "model/lstm_humidity_room3_gayungan_callback.h5",
        4: "model/lstm_humidity_room4_gayungan_callback.h5",
        5: "model/lstm_humidity_room5_gayungan_callback.h5",
    },
}

SCALER_GAYUNGAN = {
    "temperature": {
        1: "model/scaler_temperature_room1_gayungan.pkl",
        2: "model/scaler_temperature_room2_gayungan.pkl",
        3: "model/scaler_temperature_room3_gayungan.pkl",
        4: "model/scaler_temperature_room4_gayungan.pkl",
        5: "model/scaler_temperature_room5_gayungan.pkl",
    },
    "humidity": {
        1: "model/scaler_humidity_room1_gayungan.pkl",
        2: "model/scaler_humidity_room2_gayungan.pkl",
        3: "model/scaler_humidity_room3_gayungan.pkl",
        4: "model/scaler_humidity_room4_gayungan.pkl",
        5: "model/scaler_humidity_room5_gayungan.pkl",
    },
}

# ------------------------------
# Load semua model & scaler
# ------------------------------
def load_models(model_dict, scaler_dict):
    return {
        sensor: {
            r: (
                load_model(model_dict[sensor][r], custom_objects={"mse": MeanSquaredError()}),
                joblib.load(scaler_dict[sensor][r]),
            )
            for r in model_dict[sensor]
        }
        for sensor in model_dict
    }

MODELS_KEBALEN = load_models(MODEL_KEBALEN, SCALER_KEBALEN)
MODELS_GAYUNGAN = load_models(MODEL_GAYUNGAN, SCALER_GAYUNGAN)