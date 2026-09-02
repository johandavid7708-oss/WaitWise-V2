"""
WaitWise Machine Learning Intelligence Layer.

This package contains the systems responsible for:

- Crowd prediction
- Self-learning from historical data
- Pattern discovery
- Anomaly detection
"""

from .predictor import CrowdPredictor
from .learner import CrowdLearner
from .anomaly import CrowdAnomalyDetector


__all__ = [

    "CrowdPredictor",

    "CrowdLearner",

    "CrowdAnomalyDetector"

]
