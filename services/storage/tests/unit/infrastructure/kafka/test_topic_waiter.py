from unittest.mock import MagicMock, patch

from src.infrastructure.kafka.topic_waiter import ensure_topics_available


@patch("src.infrastructure.kafka.topic_waiter.AdminClient")
def test_topics_available_success(mock_admin_cls):
    mock_admin = MagicMock()
    mock_admin_cls.return_value = mock_admin
    metadata = MagicMock()
    metadata.topics.keys.return_value = {"a", "b", "c"}
    mock_admin.list_topics.return_value = metadata

    ensure_topics_available(["a", "b"])  # should return quickly
    mock_admin.list_topics.assert_called()


@patch("time.sleep", return_value=None)
@patch("src.infrastructure.kafka.topic_waiter.AdminClient")
def test_topics_available_retries_then_fails(mock_admin_cls, _sleep):
    mock_admin = MagicMock()
    mock_admin_cls.return_value = mock_admin
    metadata = MagicMock()
    # Always missing
    metadata.topics.keys.return_value = {"x"}
    mock_admin.list_topics.return_value = metadata

    try:
        ensure_topics_available(["a", "b"], max_retries=2, initial_delay=0)
        assert False, "Expected failure when topics not found"
    except RuntimeError as e:
        assert "Topics not available" in str(e)
