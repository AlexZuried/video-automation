import numpy as np
from typing import List, Dict
from loguru import logger

class TrendPredictor:
    def __init__(self):
        self.history = {}

    def record_hashtag_performance(self, hashtag: str, views: int):
        if hashtag not in self.history:
            self.history[hashtag] = []
        self.history[hashtag].append(views)

    def predict_trend(self, hashtag: str) -> str:
        if hashtag not in self.history or len(self.history[hashtag]) < 2:
            return "UNKNOWN"
        
        data = self.history[hashtag]
        # Simple linear regression logic using numpy
        x = np.array(range(len(data)))
        y = np.array(data)
        
        if len(x) < 2: return "STABLE"
        
        slope = np.polyfit(x, y, 1)[0]
        
        if slope > 100000:
            return "RISING 🚀"
        elif slope < -50000:
            return "FALLING 📉"
        else:
            return "STABLE ➡️"
