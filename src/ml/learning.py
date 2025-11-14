"""
Demand Prediction using historical patterns
Simple neural network approach for demand forecasting
"""
import math
from collections import deque
from typing import List, Tuple
import random


class DemandPredictor:
    """
    Advanced demand prediction using pattern recognition
    Learns from historical data to predict future demand
    """
    
    def __init__(self, learning_rate=0.01, history_size=100):
        self.learning_rate = learning_rate
        self.history = deque(maxlen=history_size)
        self.hourly_patterns = {h: [] for h in range(24)}
        self.weights = {
            'hour_of_day': 0.4,
            'day_of_week': 0.2,
            'recent_trend': 0.3,
            'historical_avg': 0.1
        }
        
    def add_observation(self, demand: int, hour: int, day_of_week: int):
        """Add new observation to history"""
        self.history.append({
            'demand': demand,
            'hour': hour,
            'day': day_of_week,
            'timestamp': len(self.history)
        })
        self.hourly_patterns[hour].append(demand)
    
    def predict(self, hour: int, day_of_week: int) -> float:
        """
        Predict demand for given hour and day
        Uses weighted combination of multiple signals
        """
        if len(self.history) < 10:
            return 10.0  # Default if not enough data
        
        # Signal 1: Hour of day pattern
        hour_avg = sum(self.hourly_patterns[hour][-10:]) / max(len(self.hourly_patterns[hour][-10:]), 1)
        
        # Signal 2: Day of week pattern
        day_pattern = self._get_day_pattern(day_of_week)
        
        # Signal 3: Recent trend (last 5 observations)
        recent_trend = self._get_recent_trend()
        
        # Signal 4: Overall historical average
        historical_avg = sum(obs['demand'] for obs in list(self.history)[-20:]) / min(len(self.history), 20)
        
        # Weighted combination
        prediction = (
            self.weights['hour_of_day'] * hour_avg +
            self.weights['day_of_week'] * day_pattern +
            self.weights['recent_trend'] * recent_trend +
            self.weights['historical_avg'] * historical_avg
        )
        
        return max(0, prediction)
    
    def _get_day_pattern(self, day: int) -> float:
        """Get average demand for this day of week"""
        day_obs = [obs['demand'] for obs in self.history if obs['day'] == day]
        return sum(day_obs) / max(len(day_obs), 1) if day_obs else 10.0
    
    def _get_recent_trend(self) -> float:
        """Calculate recent trend (increasing/decreasing)"""
        recent = list(self.history)[-5:]
        if len(recent) < 2:
            return 10.0
        
        trend = sum(recent[i]['demand'] for i in range(len(recent))) / len(recent)
        return trend
    
    def get_confidence(self) -> float:
        """Get confidence in predictions (0-1)"""
        return min(1.0, len(self.history) / 100.0)


class QLearningRouter:
    """
    Q-Learning for route optimization
    Learns which routes/actions lead to better outcomes
    """
    
    def __init__(self, num_stations: int, learning_rate=0.1, discount=0.9, epsilon=0.2):
        self.lr = learning_rate
        self.discount = discount
        self.epsilon = epsilon  # exploration rate
        self.q_table = {}  # (state, action) -> Q-value
        self.num_stations = num_stations
        self.episode_rewards = []
        
    def get_state(self, position: Tuple[int, int], fuel: float, passengers: int) -> str:
        """Convert current situation to state string"""
        fuel_level = 'high' if fuel > 0.7 else 'medium' if fuel > 0.3 else 'low'
        capacity_level = 'full' if passengers > 40 else 'medium' if passengers > 20 else 'empty'
        return f"{position}_{fuel_level}_{capacity_level}"
    
    def choose_action(self, state: str, available_stations: List[int]) -> int:
        """
        Choose next station to visit
        Uses epsilon-greedy: explore vs exploit
        """
        if random.random() < self.epsilon or not self._has_learned_state(state):
            # Explore: random choice
            return random.choice(available_stations)
        
        # Exploit: choose best known action
        q_values = {station: self._get_q(state, station) for station in available_stations}
        return max(q_values, key=q_values.get)
    
    def update(self, state: str, action: int, reward: float, next_state: str):
        """Update Q-value based on experience"""
        old_q = self._get_q(state, action)
        
        # Get max Q-value for next state
        next_actions = list(range(self.num_stations))
        max_next_q = max([self._get_q(next_state, a) for a in next_actions])
        
        # Q-learning update rule
        new_q = old_q + self.lr * (reward + self.discount * max_next_q - old_q)
        self._set_q(state, action, new_q)
        
        self.episode_rewards.append(reward)
    
    def _get_q(self, state: str, action: int) -> float:
        """Get Q-value for state-action pair"""
        return self.q_table.get(f"{state}_{action}", 0.0)
    
    def _set_q(self, state: str, action: int, value: float):
        """Set Q-value for state-action pair"""
        self.q_table[f"{state}_{action}"] = value
    
    def _has_learned_state(self, state: str) -> bool:
        """Check if we have any Q-values for this state"""
        return any(key.startswith(f"{state}_") for key in self.q_table.keys())
    
    def get_learning_stats(self) -> dict:
        """Get learning statistics"""
        return {
            'states_explored': len(set(k.rsplit('_', 1)[0] for k in self.q_table.keys())),
            'total_updates': len(self.q_table),
            'avg_recent_reward': sum(self.episode_rewards[-100:]) / max(len(self.episode_rewards[-100:]), 1),
            'exploration_rate': self.epsilon
        }
    
    def decay_exploration(self, min_epsilon=0.05):
        """Reduce exploration over time as agent learns"""
        self.epsilon = max(min_epsilon, self.epsilon * 0.995)


class PatternRecognizer:
    """
    Recognizes patterns in time series data
    Useful for detecting rush hours, special events, etc.
    """
    
    def __init__(self):
        self.patterns = []
        self.anomalies = []
        
    def detect_rush_hour(self, demands: List[int]) -> bool:
        """Detect if current period is rush hour"""
        if len(demands) < 5:
            return False
        
        recent_avg = sum(demands[-5:]) / 5
        overall_avg = sum(demands) / len(demands)
        
        return recent_avg > overall_avg * 1.5
    
    def detect_anomaly(self, current_demand: int, historical: List[int]) -> bool:
        """Detect unusual demand (way above/below normal)"""
        if len(historical) < 10:
            return False
        
        mean = sum(historical) / len(historical)
        variance = sum((x - mean) ** 2 for x in historical) / len(historical)
        std_dev = math.sqrt(variance)
        
        # Anomaly if more than 2 standard deviations away
        return abs(current_demand - mean) > 2 * std_dev
    
    def find_peak_hours(self, hourly_data: dict) -> List[int]:
        """Find which hours typically have high demand"""
        if not hourly_data:
            return []
        
        avg_by_hour = {h: sum(vals) / len(vals) for h, vals in hourly_data.items() if vals}
        if not avg_by_hour:
            return []
        
        overall_avg = sum(avg_by_hour.values()) / len(avg_by_hour)
        peak_hours = [h for h, avg in avg_by_hour.items() if avg > overall_avg * 1.3]
        
        return sorted(peak_hours)


class ReinforcementLearner:
    """
    Generic reinforcement learning for agent behavior
    Learns optimal actions through trial and error
    """
    
    def __init__(self, learning_rate=0.1):
        self.lr = learning_rate
        self.action_values = {}  # action -> average reward
        self.action_counts = {}  # action -> number of tries
        
    def select_action(self, actions: List[str], epsilon=0.1) -> str:
        """
        Select action using epsilon-greedy
        """
        if random.random() < epsilon or not self.action_values:
            return random.choice(actions)
        
        # Choose action with highest average reward
        action_scores = {a: self.action_values.get(a, 0) for a in actions}
        return max(action_scores, key=action_scores.get)
    
    def update_value(self, action: str, reward: float):
        """Update action value based on received reward"""
        if action not in self.action_values:
            self.action_values[action] = reward
            self.action_counts[action] = 1
        else:
            count = self.action_counts[action]
            old_avg = self.action_values[action]
            
            # Incremental average update
            new_avg = old_avg + (reward - old_avg) / (count + 1)
            
            self.action_values[action] = new_avg
            self.action_counts[action] += 1
    
    def get_best_action(self, actions: List[str]) -> str:
        """Get best known action (no exploration)"""
        if not self.action_values:
            return random.choice(actions)
        
        action_scores = {a: self.action_values.get(a, 0) for a in actions}
        return max(action_scores, key=action_scores.get)
