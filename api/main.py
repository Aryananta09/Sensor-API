from fastapi import FastAPI
from schemas import PredictionRequest
from models_config import MODELS_KEBALEN, MODELS_GAYUNGAN
from services.prediction import get_sensor_data, average_by_interval, make_prediction, save_predictions

app = FastAPI()

@app.get("/")
def root():
    return {"message": "server is running"}

@app.post("/predict-kebalen")
def predict_kebalen(request: PredictionRequest):
    raw_data = get_sensor_data("kebalen", request.room, request.duration_hours)
    if len(raw_data) == 0:
        return {"error": "No data found for this room"}

    averaged_data = average_by_interval(raw_data)
    seq_data = averaged_data.to_dict(orient="records")
    result = make_prediction(seq_data, MODELS_KEBALEN, "kebalen", request.room, request.duration_hours)
    save_predictions("kebalen", result["room"], result["predictions"])

    return {
        "prediction_result": result
    } 


@app.post("/predict-gayungan")
def predict_gayungan(request: PredictionRequest):
    raw_data = get_sensor_data("gayungan", request.room, request.duration_hours)
    if len(raw_data) == 0:
        return {"error": "No data found for this room"}

    averaged_data = average_by_interval(raw_data)
    seq_data = averaged_data.to_dict(orient="records")
    result = make_prediction(seq_data, MODELS_GAYUNGAN, "gayungan", request.room, request.duration_hours)
    save_predictions("gayungan", result["room"], result["predictions"])

    return {
        "averaged_input": averaged_data,
        "prediction_result": result
    }



