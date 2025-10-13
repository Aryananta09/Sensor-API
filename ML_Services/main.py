# from fastapi import FastAPI
# from fastapi.middleware.cors import CORSMiddleware
# from ML_Services.schemas import PredictionRequest
# from ML_Services.models_config import MODELS_KEBALEN, MODELS_GAYUNGAN
# from ML_Services.services.prediction import  make_prediction, save_predictions
# from ML_Services.services.preprocessing import get_sensor_data, average_by_interval

# app = FastAPI()

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# @app.get("/")
# def root():
#     return {"message": "server is running"}

# @app.post("/predict-kebalen")
# def predict_kebalen(request: PredictionRequest):
#     raw_data = get_sensor_data("kebalen", request.room, request.duration_hours)
#     if len(raw_data) == 0:
#         return {"error": "No data found for this room"}

#     averaged_data = average_by_interval(raw_data)
#     seq_data = averaged_data.to_dict(orient="records")
#     result = make_prediction(seq_data, MODELS_KEBALEN, "kebalen", request.room, request.duration_hours)
#     save_predictions("kebalen", result["room"], result["predictions"])

#     return {
#         "prediction_result": result
#     } 


# @app.post("/predict-gayungan")
# def predict_gayungan(request: PredictionRequest):
#     raw_data = get_sensor_data("gayungan", request.room, request.duration_hours)
#     if len(raw_data) == 0:
#         return {"error": "No data found for this room"}

#     averaged_data = average_by_interval(raw_data)
#     seq_data = averaged_data.to_dict(orient="records")
#     result = make_prediction(seq_data, MODELS_GAYUNGAN, "gayungan", request.room, request.duration_hours)
#     save_predictions("gayungan", result["room"], result["predictions"])

#     return {
#         "prediction_result": result
#     }

# ML_Services/main.py
import time
import traceback
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from ML_Services.schemas import PredictionRequest
from ML_Services.models_config import MODELS_KEBALEN, MODELS_GAYUNGAN
from ML_Services.services.prediction import make_prediction, save_predictions
from ML_Services.services.preprocessing import get_sensor_data, average_by_interval

# logging
logger = logging.getLogger("uvicorn.error")

app = FastAPI(title="ML Services - Prediction")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Thread pool for CPU-bound blocking work (inference, DB access, preprocessing)
# Choose max_workers according to CPU cores and memory. Start small (2-4).
EXECUTOR = ThreadPoolExecutor(max_workers=3)


@app.get("/")
async def root():
    return {"message": "ml service is running"}


def _do_predict_pipeline(
    location: str,
    room: str,
    duration_hours: int,
    models_dict: dict
) -> Dict[str, Any]:
    """
    Blocking function to run the full prediction pipeline:
    1. get_sensor_data
    2. average_by_interval
    3. make_prediction
    4. save_predictions

    Returns dict: { "prediction_result": ..., "profiling": {...} }
    """
    profiling = {}
    start_total = time.time()

    try:
        # 1) fetch raw data
        t0 = time.time()
        raw_data = get_sensor_data(location, room, duration_hours)
        profiling['data_fetch'] = time.time() - t0
        logger.info(f"[{location}/{room}] data fetch: {profiling['data_fetch']:.3f}s (rows={len(raw_data) if hasattr(raw_data, '__len__') else 'N/A'})")

        if len(raw_data) == 0:
            # return early with profiling info
            total = time.time() - start_total
            profiling['total'] = total
            return {"error": "No data found for this room", "profiling": profiling}

        # 2) averaging / preprocessing
        t1 = time.time()
        averaged_df = average_by_interval(raw_data)
        profiling['averaging'] = time.time() - t1
        logger.info(f"[{location}/{room}] averaging: {profiling['averaging']:.3f}s (records={len(averaged_df) if hasattr(averaged_df, '__len__') else 'N/A'})")

        # Convert to list-of-dicts (sequence) expected by make_prediction
        t2 = time.time()
        seq_data = averaged_df.to_dict(orient="records") if hasattr(averaged_df, "to_dict") else list(averaged_df)
        profiling['prep_format'] = time.time() - t2
        logger.info(f"[{location}/{room}] format prep: {profiling['prep_format']:.3f}s")

        # 3) inference / prediction
        t3 = time.time()
        result = make_prediction(seq_data, models_dict, location, room, duration_hours)
        profiling['inference'] = time.time() - t3
        logger.info(f"[{location}/{room}] inference: {profiling['inference']:.3f}s")

        # 4) save predictions (non-critical, but measure)
        t4 = time.time()
        try:
            save_predictions(location, result.get("room", room), result.get("predictions", []))
            saved = True
        except Exception as e:
            # Log but don't fail entire request if saving fails
            saved = False
            logger.error(f"[{location}/{room}] save_predictions failed: {e}")
            logger.debug(traceback.format_exc())
        profiling['save'] = time.time() - t4
        logger.info(f"[{location}/{room}] save: {profiling['save']:.3f}s (saved={saved})")

        total = time.time() - start_total
        profiling['total'] = total
        logger.info(f"[{location}/{room}] total pipeline time: {total:.3f}s")

        return {"prediction_result": result, "profiling": profiling}

    except Exception as e:
        tb = traceback.format_exc()
        logger.error("Exception in prediction pipeline: %s\n%s", str(e), tb)
        # include profiling so far
        profiling['error'] = str(e)
        profiling['total_so_far'] = time.time() - start_total
        # raise to outer layer to convert to HTTPException if needed
        raise RuntimeError({"error": str(e), "profiling": profiling})


async def _run_in_executor(fn, *args, **kwargs):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(EXECUTOR, lambda: fn(*args, **kwargs))


@app.post("/predict-kebalen")
async def predict_kebalen(request: PredictionRequest):
    """
    Async endpoint that runs blocking prediction pipeline in ThreadPoolExecutor.
    Returns: { prediction_result: ..., profiling: { ... } } or error object.
    """
    try:
        # Run full blocking pipeline in executor (preprocessing + inference + save)
        res = await _run_in_executor(
            _do_predict_pipeline,
            "kebalen",
            request.room,
            request.duration_hours,
            MODELS_KEBALEN
        )

        # If _do_predict_pipeline returned an "error" dict, convert to HTTP 400
        if isinstance(res, dict) and res.get("error"):
            return res

        return res

    except RuntimeError as re:
        # _do_predict_pipeline raised RuntimeError with a dict inside
        payload = re.args[0] if re.args else {"error": "unknown", "profiling": {}}
        logger.error("RuntimeError in /predict-kebalen: %s", payload)
        raise HTTPException(status_code=500, detail=payload)
    except Exception as e:
        logger.error("Unhandled error in /predict-kebalen: %s\n%s", str(e), traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/predict-gayungan")
async def predict_gayungan(request: PredictionRequest):
    try:
        res = await _run_in_executor(
            _do_predict_pipeline,
            "gayungan",
            request.room,
            request.duration_hours,
            MODELS_GAYUNGAN
        )

        if isinstance(res, dict) and res.get("error"):
            return res

        return res

    except RuntimeError as re:
        payload = re.args[0] if re.args else {"error": "unknown", "profiling": {}}
        logger.error("RuntimeError in /predict-gayungan: %s", payload)
        raise HTTPException(status_code=500, detail=payload)
    except Exception as e:
        logger.error("Unhandled error in /predict-gayungan: %s\n%s", str(e), traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))



