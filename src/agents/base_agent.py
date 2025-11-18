"""
Base agent class for all transportation system agents
"""
import spade
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour, OneShotBehaviour
from spade.message import Message
from spade.template import Template
import json
import asyncio
from datetime import datetime
from typing import Dict, Any, List
from src.protocols.message_bus import message_bus, LocalMessage

class BaseTransportAgent(Agent):
    """Base class for all transportation system agents"""
    
    def __init__(self, jid: str, password: str, agent_type: str):
        super().__init__(jid, password)
        self.agent_type = agent_type
        self.start_time = datetime.now()
        self.metrics = {}
        self.message_history = []
        
        # Register with local message bus
        message_bus.register_agent(str(jid))
        
    async def setup(self):
        """Setup the agent with basic behaviours"""
        print(f"🤖 {self.agent_type} agent {self.jid} starting...")
        
        # Add message receiving behaviour
        self.add_behaviour(self.MessageReceiver())
        
        # Add periodic status update behaviour
        self.add_behaviour(self.StatusUpdater())
    
    class MessageReceiver(CyclicBehaviour):
        """Handle incoming messages"""
        
        async def run(self):
            while True:
                # Use local message bus instead of SPADE
                msg = await message_bus.receive_message(str(self.agent.jid), timeout=1)
                if msg:
                    await self.agent.handle_message(msg)
                await asyncio.sleep(0.1)
    
    class StatusUpdater(CyclicBehaviour):
        """Periodic status updates and maintenance"""
        
        async def run(self):
            while True:
                await asyncio.sleep(5)  # Update every 5 seconds
                await self.agent.update_status()
    
    async def handle_message(self, msg: Message):
        """Handle incoming messages - to be implemented by subclasses"""
        self.message_history.append({
            'timestamp': datetime.now(),
            'sender': str(msg.sender),
            'body': msg.body,
            'metadata': msg.metadata
        })
        print(f"📨 {self.agent_type} {self.jid} received message from {msg.sender}")
    
    async def update_status(self):
        """Update agent status - to be implemented by subclasses"""
        pass
    
    async def send_message(self, to: str, content: Dict[Any, Any], message_type: str):
        """Send a message to another agent via local message bus"""
        # Create metadata
        metadata = {"type": message_type}
        
        # Serialize content
        body = json.dumps(content)
        
        # Send via local message bus instead of SPADE
        await message_bus.send_message(
            sender_jid=str(self.jid),
            to_jid=to,
            body=body,
            metadata=metadata
        )
        
        print(f"📤 {self.agent_type} {self.jid} sent {message_type} to {to}")
    
    def log_metric(self, metric_name: str, value: float):
        """Log a performance metric"""
        if metric_name not in self.metrics:
            self.metrics[metric_name] = []
        self.metrics[metric_name].append({
            'timestamp': datetime.now(),
            'value': value
        })