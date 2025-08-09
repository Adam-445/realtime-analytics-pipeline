import unittest.mock
from unittest.mock import MagicMock

from src.transformations.device_categorizer import categorize_device


class TestDeviceCategorizer:
    """Test device categorization functionality."""

    def test_categorize_device_returns_table_with_new_column(self):
        """Test that categorize_device adds device_category column to table."""
        # Create mock table and expressions
        mock_table = MagicMock()
        mock_table_with_column = MagicMock()
        mock_table.add_columns.return_value = mock_table_with_column

        result = categorize_device(mock_table)

        # Verify add_columns was called
        mock_table.add_columns.assert_called_once()

        # Verify the result is the modified table
        assert result == mock_table_with_column

    def test_categorize_device_calls_add_columns_with_expression(self):
        """Test that categorize_device calls add_columns with proper expression."""
        mock_table = MagicMock()

        categorize_device(mock_table)

        # Verify add_columns was called once
        assert mock_table.add_columns.call_count == 1

        # Get the argument passed to add_columns
        call_args = mock_table.add_columns.call_args[0]
        assert len(call_args) == 1

        # The argument should have an alias
        expression = call_args[0]
        assert hasattr(expression, "alias")

    def test_categorize_device_with_none_table(self):
        """Test categorize_device behavior with None table."""
        try:
            result = categorize_device(None)
            # If no exception, the function should return None or handle gracefully
            assert result is None or hasattr(result, "add_columns")
        except AttributeError:
            # Expected behavior - None doesn't have add_columns method
            pass

    def test_categorize_device_preserves_original_table_reference(self):
        """Test that original table object is used correctly."""
        mock_table = MagicMock()
        mock_result = MagicMock()
        mock_table.add_columns.return_value = mock_result

        result = categorize_device(mock_table)

        # Verify the original table's add_columns method was used
        mock_table.add_columns.assert_called_once()
        assert result == mock_result

    def test_categorize_device_expression_structure(self):
        """Test that the device categorization expression is properly structured."""
        mock_table = MagicMock()

        # Mock the expression chain to capture the logic
        mock_col = MagicMock()
        mock_user_agent = MagicMock()

        with unittest.mock.patch(
            "src.transformations.device_categorizer.expr"
        ) as mock_expr:
            mock_expr.col.return_value = mock_col
            mock_col.get.return_value = mock_user_agent

            categorize_device(mock_table)

            # Verify the basic expression setup
            mock_expr.col.assert_called_once_with("device")
            mock_col.get.assert_called_once_with("user_agent")

            # Verify that like() was called with all expected patterns
            # The order doesn't matter as much as ensuring all patterns are used
            like_calls = mock_user_agent.like.call_args_list
            like_patterns = [call[0][0] for call in like_calls]

            assert "%Mobile%" in like_patterns, "Missing Mobile pattern"
            assert "%Tablet%" in like_patterns, "Missing Tablet pattern"
            assert "%Bot%" in like_patterns, "Missing Bot pattern"

            # Verify add_columns was called on the table
            mock_table.add_columns.assert_called_once()
