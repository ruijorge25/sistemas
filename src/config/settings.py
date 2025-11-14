# Configuration for the Multi-Agent Transportation System

SIMULATION_CONFIG = {
    'city': {
        'name': 'SimCity Transport',
        'grid_size': (20, 20),  # 20x20 grid
        'num_stations': 15,
        'num_vehicles': 10,
        'num_passengers': 50,
        'num_maintenance_crews': 3
    },
    'vehicle': {
        'capacity': 40,  # passengers per vehicle
        'fuel_capacity': 100,
        'fuel_consumption_rate': 2,  # fuel per time unit
        'speed': 1,  # grid units per time unit
        'breakdown_probability': 0.001  # per time unit
    },
    'station': {
        'max_queue_size': 100,
        'demand_forecast_window': 10,  # time units
        'overcrowding_threshold': 20  # passengers
    },
    'passenger': {
        'patience_time': 15,  # max waiting time
        'arrival_rate': 0.3,  # passengers per time unit per station
        'rush_hour_multiplier': 3.0
    },
    'maintenance': {
        'repair_time': 5,  # time units to repair
        'max_concurrent_repairs': 2,
        'response_time': 2  # time to reach broken vehicle
    },
    'simulation': {
        'time_step': 1.0,  # seconds per simulation step
        'max_duration': 3600,  # maximum simulation time
        'rush_hours': [(7, 9), (17, 19)],  # (start, end) hours
        'log_level': 'INFO'
    }
}

# XMPP Configuration for SPADE agents
XMPP_CONFIG = {
    'server': 'localhost',
    'domain': 'localhost',
    'password': 'password'
}

# Message types for agent communication
MESSAGE_TYPES = {
    'PASSENGER_REQUEST': 'passenger_request',
    'VEHICLE_CAPACITY': 'vehicle_capacity',
    'STATION_DEMAND': 'station_demand',
    'BREAKDOWN_ALERT': 'breakdown_alert',
    'MAINTENANCE_REQUEST': 'maintenance_request',
    'ROUTE_UPDATE': 'route_update',
    'CONTRACT_NET_CFP': 'cfp',  # Call for Proposals
    'CONTRACT_NET_PROPOSE': 'propose',
    'CONTRACT_NET_ACCEPT': 'accept',
    'CONTRACT_NET_REJECT': 'reject',
    'CONTRACT_NET_INFORM': 'inform'  # Inform about contract execution
}

# Performance metrics to track
METRICS = [
    'average_waiting_time',
    'fleet_utilization',
    'on_time_performance',
    'passenger_satisfaction',
    'collaboration_effectiveness',
    'fuel_efficiency',
    'breakdown_response_time'
]