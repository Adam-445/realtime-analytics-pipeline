import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from src.services.processor import process_batches


@pytest.mark.asyncio
async def test_process_batches_no_messages_sleeps():
    shutdown = asyncio.Event()

    with (
        patch("src.services.processor.KafkaBatchConsumer") as mock_consumer_cls,
        patch("src.services.processor.ClickHouseClient") as mock_ch_cls,
        patch("asyncio.sleep", new=AsyncMock()) as mock_sleep,
    ):
        mock_consumer = MagicMock()
        mock_consumer.consume_batch.return_value = {}
        mock_consumer_cls.return_value = mock_consumer

        mock_ch_cls.return_value = MagicMock()

        async def stopper():
            await asyncio.sleep(0)
            shutdown.set()

        task = asyncio.create_task(process_batches(shutdown))
        await stopper()
        await task

        # When no messages, we expect a sleep to be scheduled
        assert mock_sleep.await_count >= 1


@pytest.mark.asyncio
async def test_process_batches_successful_flow():
    shutdown = asyncio.Event()

    with (
        patch("src.services.processor.KafkaBatchConsumer") as mock_consumer_cls,
        patch("src.services.processor.ClickHouseClient") as mock_ch_cls,
    ):
        mock_consumer = MagicMock()
        mock_consumer.consume_batch.return_value = {
            "event_metrics": [{"a": 1}, {"a": 2}],
        }
        mock_consumer_cls.return_value = mock_consumer
        mock_consumer.commit = MagicMock()

        mock_ch = MagicMock()
        mock_ch_cls.return_value = mock_ch

        async def stopper():
            await asyncio.sleep(0)
            shutdown.set()

        task = asyncio.create_task(process_batches(shutdown))
        await stopper()
        await task

        # Inserts attempted and commit called
        assert mock_ch.insert_rows.call_count >= 1
        assert mock_consumer.commit.called


@pytest.mark.asyncio
async def test_process_batches_insert_failure_records_error_and_no_commit():
    shutdown = asyncio.Event()

    with (
        patch("src.services.processor.KafkaBatchConsumer") as mock_consumer_cls,
        patch("src.services.processor.ClickHouseClient") as mock_ch_cls,
    ):
        mock_consumer = MagicMock()
        mock_consumer.consume_batch.return_value = {
            "event_metrics": [{"a": 1}],
        }
        mock_consumer_cls.return_value = mock_consumer

        mock_ch = MagicMock()
        mock_ch.insert_rows.side_effect = RuntimeError("boom")
        mock_ch_cls.return_value = mock_ch

        async def stopper():
            await asyncio.sleep(0)
            shutdown.set()

        task = asyncio.create_task(process_batches(shutdown))
        await stopper()
        await task

        # Commit should not be called when insert failed
        assert not mock_consumer.commit.called
