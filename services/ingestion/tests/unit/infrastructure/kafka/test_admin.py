from unittest.mock import MagicMock, patch

from src.infrastructure.kafka.admin import create_topics


class TestKafkaAdmin:
    """Test Kafka admin functionality."""

    @patch("src.infrastructure.kafka.admin.settings")
    @patch("src.infrastructure.kafka.admin.AdminClient")
    @patch("src.infrastructure.kafka.admin.NewTopic")
    def test_create_topics_success(
        self, mock_new_topic, mock_admin_client, mock_settings
    ):
        """Test successful topic creation."""
        # Setup settings
        mock_settings.kafka_topic_events = "analytics_events"
        mock_settings.kafka_consumer_topics = ["processed_events", "metrics"]
        mock_settings.kafka_bootstrap_servers = "localhost:9092"

        # Setup mocks
        mock_admin = MagicMock()
        mock_admin_client.return_value = mock_admin

        mock_topics = [MagicMock(), MagicMock(), MagicMock()]
        mock_new_topic.side_effect = mock_topics

        # Setup successful futures
        mock_futures = {}
        for i, topic_name in enumerate(
            ["analytics_events", "processed_events", "metrics"]
        ):
            future = MagicMock()
            future.result.return_value = None  # Success
            mock_futures[topic_name] = future

        mock_admin.create_topics.return_value = mock_futures

        with patch("src.infrastructure.kafka.admin.logger") as mock_logger:
            create_topics()

            # Verify admin client created with correct config
            mock_admin_client.assert_called_once_with(
                {"bootstrap.servers": "localhost:9092"}
            )

            # Verify topics were created correctly
            assert mock_new_topic.call_count == 3
            topic_calls = mock_new_topic.call_args_list

            # Check each topic creation call
            expected_topics = ["analytics_events", "processed_events", "metrics"]
            for i, call in enumerate(topic_calls):
                assert call[0][0] == expected_topics[i]
                assert call[1]["num_partitions"] == 3
                assert call[1]["replication_factor"] == 1

            # Verify create_topics was called
            mock_admin.create_topics.assert_called_once_with(
                mock_topics, validate_only=False
            )

            # Verify success logging
            assert mock_logger.info.call_count == 4  # 1 initial + 3 success logs

            # Check initial log
            initial_call = mock_logger.info.call_args_list[0]
            assert initial_call[0][0] == "Creating Kafka topics"
            assert initial_call[1]["extra"]["topics"] == ["processed_events", "metrics"]

            # Check success logs
            success_calls = mock_logger.info.call_args_list[1:]
            for i, call in enumerate(success_calls):
                assert call[0][0] == "Topic created"
                assert call[1]["extra"]["topic"] == expected_topics[i]

    @patch("src.infrastructure.kafka.admin.settings")
    @patch("src.infrastructure.kafka.admin.AdminClient")
    @patch("src.infrastructure.kafka.admin.NewTopic")
    def test_create_topics_already_exists(
        self, mock_new_topic, mock_admin_client, mock_settings
    ):
        """Test topic creation when topics already exist."""
        # Setup settings
        mock_settings.kafka_topic_events = "analytics_events"
        mock_settings.kafka_consumer_topics = ["processed_events"]
        mock_settings.kafka_bootstrap_servers = "localhost:9092"

        # Setup mocks
        mock_admin = MagicMock()
        mock_admin_client.return_value = mock_admin

        mock_topics = [MagicMock(), MagicMock()]
        mock_new_topic.side_effect = mock_topics

        # Setup futures with TopicExistsError (code 36)
        mock_futures = {}
        for topic_name in ["analytics_events", "processed_events"]:
            future = MagicMock()
            exc = Exception()
            exc.args = [MagicMock()]
            exc.args[0].code.return_value = 36  # TopicExistsError
            future.result.side_effect = exc
            mock_futures[topic_name] = future

        mock_admin.create_topics.return_value = mock_futures

        with patch("src.infrastructure.kafka.admin.logger") as mock_logger:
            # Should not raise exception
            create_topics()

            # Verify error logging was not called for TopicExistsError
            mock_logger.error.assert_not_called()

    @patch("src.infrastructure.kafka.admin.settings")
    @patch("src.infrastructure.kafka.admin.AdminClient")
    @patch("src.infrastructure.kafka.admin.NewTopic")
    def test_create_topics_other_error(
        self, mock_new_topic, mock_admin_client, mock_settings
    ):
        """Test topic creation with other types of errors."""
        # Setup settings
        mock_settings.kafka_topic_events = "analytics_events"
        mock_settings.kafka_consumer_topics = ["processed_events"]
        mock_settings.kafka_bootstrap_servers = "localhost:9092"

        # Setup mocks
        mock_admin = MagicMock()
        mock_admin_client.return_value = mock_admin

        mock_topics = [MagicMock(), MagicMock()]
        mock_new_topic.side_effect = mock_topics

        # Setup futures with different error
        mock_futures = {}

        # First topic succeeds
        future1 = MagicMock()
        future1.result.return_value = None
        mock_futures["analytics_events"] = future1

        # Second topic fails with different error
        future2 = MagicMock()
        exc = Exception("Connection error")
        exc.args = [MagicMock()]
        exc.args[0].code.return_value = 10  # Some other error code
        future2.result.side_effect = exc
        mock_futures["processed_events"] = future2

        mock_admin.create_topics.return_value = mock_futures

        with patch("src.infrastructure.kafka.admin.logger") as mock_logger:
            create_topics()

            # Verify error was logged for the failed topic
            mock_logger.error.assert_called_once_with(
                "Failed to create topic",
                extra={"topic": "processed_events", "error": exc},
            )

            # Verify success was still logged for the successful topic
            success_calls = [
                call
                for call in mock_logger.info.call_args_list
                if len(call[0]) > 0 and call[0][0] == "Topic created"
            ]
            assert len(success_calls) == 1
            assert success_calls[0][1]["extra"]["topic"] == "analytics_events"

    @patch("src.infrastructure.kafka.admin.settings")
    @patch("src.infrastructure.kafka.admin.AdminClient")
    @patch("src.infrastructure.kafka.admin.NewTopic")
    def test_create_topics_empty_consumer_topics(
        self, mock_new_topic, mock_admin_client, mock_settings
    ):
        """Test topic creation with empty consumer topics list."""
        # Setup settings
        mock_settings.kafka_topic_events = "analytics_events"
        mock_settings.kafka_consumer_topics = []
        mock_settings.kafka_bootstrap_servers = "localhost:9092"

        # Setup mocks
        mock_admin = MagicMock()
        mock_admin_client.return_value = mock_admin

        mock_topic = MagicMock()
        mock_new_topic.return_value = mock_topic

        # Setup successful future
        future = MagicMock()
        future.result.return_value = None
        mock_futures = {"analytics_events": future}
        mock_admin.create_topics.return_value = mock_futures

        with patch("src.infrastructure.kafka.admin.logger") as mock_logger:
            create_topics()

            # Verify only one topic was created
            mock_new_topic.assert_called_once_with(
                "analytics_events", num_partitions=3, replication_factor=1
            )

            # Verify logging
            initial_call = mock_logger.info.call_args_list[0]
            assert initial_call[1]["extra"]["topics"] == []
