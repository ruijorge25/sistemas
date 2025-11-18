"""
Base agent class for all transportation system agents
"""
import asyncio
import json
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, Iterable, List

import spade
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour, OneShotBehaviour
from spade.message import Message
from spade.template import Template

class BaseTransportAgent(Agent):
    """Base class for all transportation system agents"""
    
    def __init__(self, jid: str, password: str, agent_type: str):
        super().__init__(jid, password)
        self.agent_type = agent_type
        self.start_time = datetime.now()
        self.metrics = {}
        self.message_history = []

        # Subscription queues for behaviors
        self._log_queue: asyncio.Queue = asyncio.Queue()
        self._message_subscribers = defaultdict(list)
        
    async def setup(self):
        """Setup the agent with basic behaviours"""
        print(f"🤖 {self.agent_type} agent {self.jid} starting...")
        
        # Add message receiving behaviour
        self.add_behaviour(self.MessageReceiver())

        # Add periodic status update behaviour
        self.add_behaviour(self.StatusUpdater())

    async def _handle_incoming_message(self, msg: Message):
        """Push incoming messages to local queues and notify subscribers."""
        # Queue message for logging/metrics collection
        await self._log_queue.put(msg)

        # Deliver copies to subscribers by message type
        msg_type = msg.get_metadata("type")
        if msg_type and msg_type in self._message_subscribers:
            for queue in list(self._message_subscribers[msg_type]):
                await queue.put(msg)

    def subscribe_to_messages(self, message_types: Iterable[str]):
        """Create a subscription queue for specific message types."""
        if isinstance(message_types, str):
            message_types = [message_types]

        queue: asyncio.Queue = asyncio.Queue()
        for msg_type in message_types:
            self._message_subscribers[msg_type].append(queue)
        return queue

    async def _get_logged_message(self, timeout: float = 1.0):
        """Retrieve the next message for logging/handle_message."""
        try:
            return await asyncio.wait_for(self._log_queue.get(), timeout)
        except asyncio.TimeoutError:
            return None
    
    class MessageReceiver(CyclicBehaviour):
        """Handle incoming XMPP messages and route to subscribers"""

        async def run(self):
            # Receive XMPP message with timeout
            msg = await self.receive(timeout=1)
            if msg:
                # Route to subscribers via callback
                await self.agent._handle_incoming_message(msg)
                # Also handle in main handler for logging
                await self.agent.handle_message(msg)
    
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
        """Send a message to another agent via XMPP"""
        # Create SPADE message
        msg = Message(to=to)
        msg.set_metadata("type", message_type)
        msg.body = json.dumps(content)
        
        # Send via SPADE/XMPP
        await self.send(msg)
        
        print(f"📤 {self.agent_type} {self.jid} sent {message_type} to {to}")
    
    def log_metric(self, metric_name: str, value: float):
        """Log a performance metric"""
        if metric_name not in self.metrics:
            self.metrics[metric_name] = []
        self.metrics[metric_name].append({
            'timestamp': datetime.now(),
            'value': value
        })