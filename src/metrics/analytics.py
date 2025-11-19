"""
Minimal analytics stubs
"""

class AdvancedAnalytics:
    """Analytics stub"""
    def __init__(self):
        self.events = []
    
    def record_event(self, event_type, data):
        """Record event"""
        self.events.append({'type': event_type, 'data': data})
    
    def get_metrics(self):
        """Get metrics"""
        return {}
