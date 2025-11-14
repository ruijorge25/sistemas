"""
Performance metrics collection and analysis
"""
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any
from collections import defaultdict, deque

class MetricsCollector:
    """Collects and analyzes performance metrics from all agents"""
    
    def __init__(self):
        self.metrics_data = defaultdict(list)
        self.time_series_data = defaultdict(lambda: deque(maxlen=1000))
        self.start_time = datetime.now()
        
    def add_metric(self, agent_id: str, metric_name: str, value: float, timestamp: datetime = None):
        """Add a metric data point"""
        if timestamp is None:
            timestamp = datetime.now()
            
        metric_entry = {
            'agent_id': agent_id,
            'metric_name': metric_name,
            'value': value,
            'timestamp': timestamp,
            'simulation_time': (timestamp - self.start_time).total_seconds()
        }
        
        self.metrics_data[metric_name].append(metric_entry)
        self.time_series_data[f"{agent_id}_{metric_name}"].append(metric_entry)
    
    def get_average_metric(self, metric_name: str, time_window_seconds: int = None) -> float:
        """Get average value for a metric"""
        if metric_name not in self.metrics_data:
            return 0.0
        
        data = self.metrics_data[metric_name]
        
        if time_window_seconds:
            cutoff_time = datetime.now() - timedelta(seconds=time_window_seconds)
            data = [entry for entry in data if entry['timestamp'] >= cutoff_time]
        
        if not data:
            return 0.0
        
        return sum(entry['value'] for entry in data) / len(data)
    
    def get_current_performance_summary(self) -> Dict[str, Any]:
        """Get current performance summary"""
        summary = {
            'timestamp': datetime.now().isoformat(),
            'simulation_duration': (datetime.now() - self.start_time).total_seconds(),
            'metrics': {}
        }
        
        # Calculate key performance indicators
        summary['metrics']['average_waiting_time'] = self.get_average_metric('average_waiting_time', 300)  # Last 5 minutes
        summary['metrics']['fleet_utilization'] = self.get_average_metric('fleet_utilization', 60)  # Last minute
        summary['metrics']['on_time_performance'] = self.get_average_metric('on_time_performance', 300)
        summary['metrics']['passenger_satisfaction'] = self.get_average_metric('passenger_satisfaction', 300)
        
        # Calculate system-wide metrics
        total_breakdowns = len([m for m in self.metrics_data.get('breakdown_alert', [])
                               if (datetime.now() - m['timestamp']).total_seconds() <= 3600])  # Last hour
        summary['metrics']['breakdowns_per_hour'] = total_breakdowns
        
        return summary
    
    def export_metrics(self, filename: str = None):
        """Export metrics to JSON file"""
        if filename is None:
            filename = f"metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        export_data = {
            'collection_start': self.start_time.isoformat(),
            'collection_end': datetime.now().isoformat(),
            'metrics': {}
        }
        
        for metric_name, data in self.metrics_data.items():
            export_data['metrics'][metric_name] = [
                {
                    'agent_id': entry['agent_id'],
                    'value': entry['value'],
                    'timestamp': entry['timestamp'].isoformat(),
                    'simulation_time': entry['simulation_time']
                }
                for entry in data
            ]
        
        with open(filename, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        print(f"📊 Metrics exported to {filename}")