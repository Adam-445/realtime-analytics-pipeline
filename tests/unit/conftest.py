from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_kafka_producer():
    """Mock Kafka producer for unit tests"""
    producer = MagicMock()
    producer.send_event = MagicMock()
    producer.flush = MagicMock()
    return producer


@pytest.fixture
def mock_click_house_client():
    """Mock Clickhouse client for unit tests"""
    client = MagicMock()
    client.execute = MagicMock(return_value=[])
    client.insert_batch = MagicMock()
    return client
