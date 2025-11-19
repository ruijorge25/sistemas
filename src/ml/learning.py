"""
Minimal ML stubs for demand prediction
"""

class DemandPredictor:
    """Simple demand predictor (stub)"""
    def __init__(self, learning_rate=0.01, history_size=200):
        self.history = []
    
    def predict_next(self, history):
        """Predict next demand based on history"""
        if len(history) < 2:
            return history[-1] if history else 0
        return sum(history[-3:]) / min(3, len(history))
    
    def add_observation(self, demand, hour, day):
        """Add observation"""
        self.history.append(demand)
    
    def predict(self, hour, day):
        """Predict demand"""
        if not self.history:
            return 0
        return sum(self.history[-5:]) / min(5, len(self.history))


class PatternRecognizer:
    """Simple pattern recognizer (stub)"""
    def get_demand_boost(self, hour, x, y):
        """Get demand boost multiplier"""
        # Rush hours: 7-9, 17-19
        if 7 <= hour <= 9 or 17 <= hour <= 19:
            return 1.5
        return 1.0
    
    def detect_rush_hour(self, history):
        """Detect if in rush hour"""
        if not history or len(history) < 3:
            return False
        avg = sum(history[-3:]) / 3
        return avg > 10
    
    def detect_anomaly(self, current, history):
        """Detect anomaly"""
        if not history or len(history) < 5:
            return False
        avg = sum(history[-5:]) / 5
        return current > avg * 2


class QLearningRouter:
    """Q-learning router stub"""
    def __init__(self, num_stations, learning_rate=0.1, discount=0.9, epsilon=0.2):
        pass
    
    def choose_action(self, state):
        """Choose action"""
        return 0
    
    def update(self, state, action, reward, next_state):
        """Update Q-values"""
        pass


class ReinforcementLearner:
    """Reinforcement learner stub"""
    def __init__(self, learning_rate=0.1):
        pass
    
    def learn(self, state, reward):
        """Learn from experience"""
        pass
