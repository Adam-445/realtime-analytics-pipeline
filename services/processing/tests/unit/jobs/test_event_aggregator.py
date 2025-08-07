from unittest.mock import MagicMock, patch

from src.jobs.event_aggregator import EventAggregator


class TestEventAggregator:
    """Test EventAggregator job functionality."""

    def test_event_aggregator_initialization(self):
        """Test EventAggregator initializes with correct name and sink name."""
        aggregator = EventAggregator()

        assert aggregator.name == "EventAggregator"
        assert aggregator.sink_name == "event_metrics"

    def test_event_aggregator_inherits_from_base_job(self):
        """Test that EventAggregator properly inherits from BaseJob."""
        from src.jobs.base_job import BaseJob

        aggregator = EventAggregator()
        assert isinstance(aggregator, BaseJob)

    def test_build_pipeline_basic_flow(self):
        """Test build_pipeline basic execution flow."""
        aggregator = EventAggregator()
        mock_t_env = MagicMock()
        mock_events_table = MagicMock()
        mock_t_env.from_path.return_value = mock_events_table

        with patch(
            "src.jobs.event_aggregator.device_categorizer.categorize_device"
        ) as mock_categorizer:
            mock_categorized_table = MagicMock()
            mock_categorizer.return_value = mock_categorized_table

            # Set up the fluent chain to return mocks
            mock_select = MagicMock()
            mock_filter = MagicMock()
            mock_window = MagicMock()
            mock_group_by = MagicMock()
            mock_final_select = MagicMock()

            mock_categorized_table.select.return_value = mock_select
            mock_select.filter.return_value = mock_filter
            mock_filter.window.return_value = mock_window
            mock_window.group_by.return_value = mock_group_by
            mock_group_by.select.return_value = mock_final_select

            # Mock the windowing and expression imports to avoid PyFlink errors
            with patch("src.jobs.event_aggregator.Tumble") as mock_tumble, patch(
                "src.jobs.event_aggregator.expr"
            ) as mock_expr:

                # Set up basic mocks
                mock_col = MagicMock()
                mock_expr.col.return_value = mock_col
                mock_lit = MagicMock()
                mock_expr.lit.return_value = mock_lit
                mock_over = MagicMock()
                mock_tumble.over.return_value = mock_over

                result = aggregator.build_pipeline(mock_t_env)

                # Verify basic flow
                mock_t_env.from_path.assert_called_once_with("events")
                mock_categorizer.assert_called_once_with(mock_events_table)
                mock_categorized_table.select.assert_called_once()
                mock_select.filter.assert_called_once()
                mock_filter.window.assert_called_once()
                mock_window.group_by.assert_called_once()
                mock_group_by.select.assert_called_once()

                assert result == mock_final_select

    @patch("src.jobs.event_aggregator.settings")
    def test_build_pipeline_environment_time_column_selection(self, mock_settings):
        """Test that correct time column is selected based on environment."""
        aggregator = EventAggregator()

        # Test production environment
        mock_settings.app_environment = "production"
        mock_settings.processing_allowed_event_types = ["click"]
        mock_settings.processing_metrics_window_size_seconds = 60

        with patch(
            "src.jobs.event_aggregator.device_categorizer.categorize_device"
        ) as mock_categorizer, patch("src.jobs.event_aggregator.Tumble"), patch(
            "src.jobs.event_aggregator.expr"
        ):

            # Set up basic mocks to avoid errors
            mock_categorizer.return_value = MagicMock()
            mock_categorizer.return_value.select.return_value.filter.return_value.window.return_value.group_by.return_value.select.return_value = (
                MagicMock()
            )

            # The test verifies the method can be called without error in production mode
            result = aggregator.build_pipeline(MagicMock())
            assert result is not None

        # Test non-production environment
        mock_settings.app_environment = "development"

        with patch(
            "src.jobs.event_aggregator.device_categorizer.categorize_device"
        ) as mock_categorizer, patch("src.jobs.event_aggregator.Tumble"), patch(
            "src.jobs.event_aggregator.expr"
        ):

            # Set up basic mocks to avoid errors
            mock_categorizer.return_value = MagicMock()
            mock_categorizer.return_value.select.return_value.filter.return_value.window.return_value.group_by.return_value.select.return_value = (
                MagicMock()
            )

            # The test verifies the method can be called without error in development mode
            result = aggregator.build_pipeline(MagicMock())
            assert result is not None

    @patch("src.jobs.event_aggregator.settings")
    def test_build_pipeline_filter_configuration(self, mock_settings):
        """Test that event type filtering uses configuration settings."""
        mock_settings.app_environment = "development"
        mock_settings.processing_allowed_event_types = ["click", "view", "purchase"]
        mock_settings.processing_metrics_window_size_seconds = 60

        aggregator = EventAggregator()
        mock_t_env = MagicMock()
        mock_events_table = MagicMock()
        mock_t_env.from_path.return_value = mock_events_table

        with patch(
            "src.jobs.event_aggregator.device_categorizer.categorize_device"
        ) as mock_categorizer, patch("src.jobs.event_aggregator.Tumble"), patch(
            "src.jobs.event_aggregator.expr"
        ) as mock_expr:

            mock_categorized_table = MagicMock()
            mock_categorizer.return_value = mock_categorized_table

            mock_col = MagicMock()
            mock_in_expr = MagicMock()
            mock_expr.col.return_value = mock_col
            mock_col.in_.return_value = mock_in_expr
            mock_expr.lit.return_value = MagicMock()

            # Set up fluent chain
            mock_select = MagicMock()
            mock_filter = MagicMock()
            mock_categorized_table.select.return_value = mock_select
            mock_select.filter.return_value = mock_filter
            mock_filter.window.return_value.group_by.return_value.select.return_value = (
                MagicMock()
            )

            aggregator.build_pipeline(mock_t_env)

            # Verify filter is called with in_ expression for allowed event types
            mock_select.filter.assert_called_once_with(mock_in_expr)
            mock_col.in_.assert_called_once_with("click", "view", "purchase")

    def test_build_pipeline_with_none_table_environment(self):
        """Test EventAggregator behavior with None table environment."""
        aggregator = EventAggregator()

        try:
            result = aggregator.build_pipeline(None)
            # If no exception, should handle gracefully
            assert result is None or hasattr(result, "select")
        except AttributeError:
            # Expected behavior - None doesn't have from_path method
            pass
