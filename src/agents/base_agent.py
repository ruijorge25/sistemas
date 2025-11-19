"""
Base agent class for all transportation system agents - PURE SPADE
"""
import asyncio
import json
from datetime import datetime
from typing import Any, Dict
from collections import deque

from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message

from ..config.settings import MESSAGE_TYPES

# Simple LOCAL message router for simulation without XMPP server
_local_queues = {}

class BaseTransportAgent(Agent):
    """
    Base class for all transportation system agents.
    PURE SPADE with simple local routing for simulation mode.
    """
    
    def __init__(self, jid: str, password: str, agent_type: str, metrics_collector=None):
        super().__init__(jid, password)
        self.agent_type = agent_type
        self.start_time = datetime.now()
        self.metrics = {}
        self.message_history = []
        self.current_tick = 0
        
        # PASSO 5: Metrics collector reference
        self.metrics_collector = metrics_collector
        
        # Register local queue for simulation mode
        if str(jid) not in _local_queues:
            _local_queues[str(jid)] = deque(maxlen=1000)
    
    async def setup(self):
        """Setup the agent with SPADE message receiver behaviour"""
        print(f"🤖 {self.agent_type} agent {self.jid} starting with PURE SPADE...")
        
        # Add universal SPADE message receiver
        self.add_behaviour(self.MessageReceiverBehaviour())
    
    class MessageReceiverBehaviour(CyclicBehaviour):
        """
        Universal message receiver - works with or without XMPP
        """
        async def run(self):
            msg = None
            
            try:
                # FORCE LOCAL MODE - always use _local_queues (no XMPP server)
                jid = str(self.agent.jid)
                if jid in _local_queues and len(_local_queues[jid]) > 0:
                    msg = _local_queues[jid].popleft()
                    # DEBUG
                    msg_type = msg.metadata.get('type') if msg.metadata else None
                    if msg_type == MESSAGE_TYPES.get('BREAKDOWN_ALERT'):
                        print(f"🔍 RECEIVE DEBUG: {jid} popped BREAKDOWN_ALERT from queue, remaining: {len(_local_queues[jid])}")
            except Exception as e:
                print(f"❌ MessageReceiver error for {self.agent.jid}: {e}")
                jid = str(self.agent.jid)
                if jid in _local_queues and len(_local_queues[jid]) > 0:
                    msg = _local_queues[jid].popleft()
            
            if msg:
                await self.agent.handle_message(msg)
            
            await asyncio.sleep(0.1)
    
    async def handle_message(self, msg: Message):
        """
        Handle incoming SPADE messages - MUST BE OVERRIDDEN in subclasses.
        This is the MAIN entry point for all messages.
        """
        self.message_history.append({
            'timestamp': datetime.now(),
            'sender': str(msg.sender),
            'body': msg.body,
            'metadata': dict(msg.metadata) if msg.metadata else {}
        })
    
    async def send_message(self, to: str, content: Dict[Any, Any], message_type: str):
        """
        Send SPADE message with local routing fallback
        
        Args:
            to: Recipient JID
            content: Message content dict (will be JSON serialized)
            message_type: Message type from MESSAGE_TYPES
        """
        msg = Message(to=to)
        msg.set_metadata("type", message_type)
        msg.body = json.dumps(content)
        msg.sender = str(self.jid)
        
        try:
            # FORCE LOCAL MODE - always use _local_queues
            if to not in _local_queues:
                _local_queues[to] = deque(maxlen=1000)
            _local_queues[to].append(msg)
            # DEBUG
            if message_type == MESSAGE_TYPES.get('BREAKDOWN_ALERT'):
                print(f"🔍 SEND DEBUG: Added BREAKDOWN_ALERT to queue for {to}, queue size now: {len(_local_queues[to])}")
        except Exception as e:
            print(f"❌ Error sending message: {e}")
            if to not in _local_queues:
                _local_queues[to] = deque(maxlen=1000)
            _local_queues[to].append(msg)
    
    def log_metric(self, metric_name: str, value: float):
        """Log a performance metric"""
        if metric_name not in self.metrics:
            self.metrics[metric_name] = []
        self.metrics[metric_name].append({
            'timestamp': datetime.now(),
            'value': value
        })
    
    async def update_status(self):
        """Update agent status - to be implemented by subclasses"""
        pass