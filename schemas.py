from pydantic import BaseModel
from typing import List

class SequenceData(BaseModel):
    temperature: float
    humidity: float

class PredictionRequest(BaseModel):
    room: int
    duration_hours: int
    sequence: List[SequenceData]
