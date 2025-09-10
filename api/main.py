from fastapi import FastAPI, HTTPException
from schemas import PredictionRequest
from models_config import MODELS_KEBALEN, MODELS_GAYUNGAN
from services.prediction import make_prediction, save_predictions

app = FastAPI()

@app.get("/")
def root():
    return {"message": "server is running"}

@app.post("/predict-kebalen")
def predict_kebalen(request: PredictionRequest):
    result = make_prediction(request, MODELS_KEBALEN, "kebalen")
    save_predictions("kebalen", result["room"], result["predictions"])
    return {"prediction_result": result}


@app.post("/predict-gayungan")
def predict_gayungan(request: PredictionRequest):
    result = make_prediction(request, MODELS_GAYUNGAN, "gayungan")
    save_predictions("gayungan", result["room"], result["predictions"])
    return {"prediction_result": result}



