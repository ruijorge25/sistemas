"""
Unit tests for message subscription system in BaseTransportAgent
Ensures messages route correctly to subscribers without race conditions
"""
import asyncio
import pytest
from collections import defaultdict

from src.agents.base_agent import BaseTransportAgent
from src.protocols.message_bus import LocalMessage
from src.config.settings import MESSAGE_TYPES


class TestAgent(BaseTransportAgent):
    """Minimal test agent"""
    def __init__(self, jid: str):
        super().__init__(jid, "password", "test_agent")


@pytest.fixture
def agent():
    """Create test agent instance"""
    return TestAgent("test@local")


@pytest.mark.asyncio
async def test_subscribe_to_single_message_type(agent):
    """Test subscribing to single message type"""
    subscription = agent.subscribe_to_messages([MESSAGE_TYPES['PASSENGER_REQUEST']])
    
    # Simulate incoming message
    msg = LocalMessage(
        sender="sender@local",
        to="test@local",
        body="test body",
        metadata={"type": MESSAGE_TYPES['PASSENGER_REQUEST']}
    )
    
    await agent._handle_incoming_message(msg)
    
    # Subscriber should receive message
    received = await asyncio.wait_for(subscription.get(), timeout=1.0)
    assert received == msg
    assert received.get_metadata("type") == MESSAGE_TYPES['PASSENGER_REQUEST']


@pytest.mark.asyncio
async def test_subscribe_to_multiple_message_types(agent):
    """Test subscribing to multiple message types"""
    subscription = agent.subscribe_to_messages([
        MESSAGE_TYPES['VEHICLE_CAPACITY'],
        MESSAGE_TYPES['STATION_DEMAND']
    ])
    
    # Send first message type
    msg1 = LocalMessage(
        sender="sender1@local",
        to="test@local",
        body="capacity update",
        metadata={"type": MESSAGE_TYPES['VEHICLE_CAPACITY']}
    )
    await agent._handle_incoming_message(msg1)
    
    # Send second message type
    msg2 = LocalMessage(
        sender="sender2@local",
        to="test@local",
        body="demand update",
        metadata={"type": MESSAGE_TYPES['STATION_DEMAND']}
    )
    await agent._handle_incoming_message(msg2)
    
    # Both should arrive at subscription
    received1 = await asyncio.wait_for(subscription.get(), timeout=1.0)
    received2 = await asyncio.wait_for(subscription.get(), timeout=1.0)
    
    received_types = {received1.get_metadata("type"), received2.get_metadata("type")}
    assert MESSAGE_TYPES['VEHICLE_CAPACITY'] in received_types
    assert MESSAGE_TYPES['STATION_DEMAND'] in received_types


@pytest.mark.asyncio
async def test_multiple_subscribers_receive_copies(agent):
    """Test multiple subscribers get independent copies"""
    sub1 = agent.subscribe_to_messages([MESSAGE_TYPES['BREAKDOWN_ALERT']])
    sub2 = agent.subscribe_to_messages([MESSAGE_TYPES['BREAKDOWN_ALERT']])
    sub3 = agent.subscribe_to_messages([MESSAGE_TYPES['BREAKDOWN_ALERT']])
    
    msg = LocalMessage(
        sender="vehicle@local",
        to="test@local",
        body="breakdown",
        metadata={"type": MESSAGE_TYPES['BREAKDOWN_ALERT']}
    )
    
    await agent._handle_incoming_message(msg)
    
    # All three subscribers should receive the message
    received1 = await asyncio.wait_for(sub1.get(), timeout=1.0)
    received2 = await asyncio.wait_for(sub2.get(), timeout=1.0)
    received3 = await asyncio.wait_for(sub3.get(), timeout=1.0)
    
    assert received1 == msg
    assert received2 == msg
    assert received3 == msg


@pytest.mark.asyncio
async def test_message_type_filtering(agent):
    """Test messages only go to correct subscribers"""
    passenger_sub = agent.subscribe_to_messages([MESSAGE_TYPES['PASSENGER_REQUEST']])
    vehicle_sub = agent.subscribe_to_messages([MESSAGE_TYPES['VEHICLE_CAPACITY']])
    
    # Send PASSENGER_REQUEST
    msg1 = LocalMessage(
        sender="passenger@local",
        to="test@local",
        body="request",
        metadata={"type": MESSAGE_TYPES['PASSENGER_REQUEST']}
    )
    await agent._handle_incoming_message(msg1)
    
    # Send VEHICLE_CAPACITY
    msg2 = LocalMessage(
        sender="vehicle@local",
        to="test@local",
        body="capacity",
        metadata={"type": MESSAGE_TYPES['VEHICLE_CAPACITY']}
    )
    await agent._handle_incoming_message(msg2)
    
    # passenger_sub should only get PASSENGER_REQUEST
    received_passenger = await asyncio.wait_for(passenger_sub.get(), timeout=1.0)
    assert received_passenger.get_metadata("type") == MESSAGE_TYPES['PASSENGER_REQUEST']
    
    # vehicle_sub should only get VEHICLE_CAPACITY
    received_vehicle = await asyncio.wait_for(vehicle_sub.get(), timeout=1.0)
    assert received_vehicle.get_metadata("type") == MESSAGE_TYPES['VEHICLE_CAPACITY']
    
    # Neither queue should have more messages
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(passenger_sub.get(), timeout=0.1)
    
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(vehicle_sub.get(), timeout=0.1)


@pytest.mark.asyncio
async def test_log_queue_receives_all_messages(agent):
    """Test log queue gets all messages regardless of subscribers"""
    # Create subscription for only one message type
    subscription = agent.subscribe_to_messages([MESSAGE_TYPES['PASSENGER_REQUEST']])
    
    # Send message that subscriber wants
    msg1 = LocalMessage(
        sender="sender1@local",
        to="test@local",
        body="subscribed",
        metadata={"type": MESSAGE_TYPES['PASSENGER_REQUEST']}
    )
    await agent._handle_incoming_message(msg1)
    
    # Send message that subscriber doesn't want
    msg2 = LocalMessage(
        sender="sender2@local",
        to="test@local",
        body="not subscribed",
        metadata={"type": MESSAGE_TYPES['BREAKDOWN_ALERT']}
    )
    await agent._handle_incoming_message(msg2)
    
    # Log queue should have both messages
    logged1 = await asyncio.wait_for(agent._log_queue.get(), timeout=1.0)
    logged2 = await asyncio.wait_for(agent._log_queue.get(), timeout=1.0)
    
    logged_types = {logged1.get_metadata("type"), logged2.get_metadata("type")}
    assert MESSAGE_TYPES['PASSENGER_REQUEST'] in logged_types
    assert MESSAGE_TYPES['BREAKDOWN_ALERT'] in logged_types
    
    # Subscription queue should only have one
    received = await asyncio.wait_for(subscription.get(), timeout=1.0)
    assert received.get_metadata("type") == MESSAGE_TYPES['PASSENGER_REQUEST']
    
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(subscription.get(), timeout=0.1)


@pytest.mark.asyncio
async def test_no_race_conditions_concurrent_messages(agent):
    """Test no messages lost under concurrent load"""
    subscription = agent.subscribe_to_messages([MESSAGE_TYPES['VEHICLE_CAPACITY']])
    
    num_messages = 50
    tasks = []
    
    # Send many messages concurrently
    for i in range(num_messages):
        msg = LocalMessage(
            sender=f"sender{i}@local",
            to="test@local",
            body=f"message {i}",
            metadata={"type": MESSAGE_TYPES['VEHICLE_CAPACITY']}
        )
        tasks.append(agent._handle_incoming_message(msg))
    
    await asyncio.gather(*tasks)
    
    # All messages should be received
    received_count = 0
    while not subscription.empty():
        await subscription.get()
        received_count += 1
    
    assert received_count == num_messages


@pytest.mark.asyncio
async def test_unsubscribed_types_ignored(agent):
    """Test unsubscribed message types don't fill queues"""
    subscription = agent.subscribe_to_messages([MESSAGE_TYPES['PASSENGER_REQUEST']])
    
    # Send many unsubscribed messages
    for i in range(10):
        msg = LocalMessage(
            sender=f"sender{i}@local",
            to="test@local",
            body=f"ignored {i}",
            metadata={"type": MESSAGE_TYPES['BREAKDOWN_ALERT']}
        )
        await agent._handle_incoming_message(msg)
    
    # Subscription queue should be empty
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(subscription.get(), timeout=0.1)
    
    # But log queue should have all 10
    for i in range(10):
        msg = await asyncio.wait_for(agent._log_queue.get(), timeout=1.0)
        assert msg.get_metadata("type") == MESSAGE_TYPES['BREAKDOWN_ALERT']
