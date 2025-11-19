"""Web search skill behaviour tests."""
from __future__ import annotations

import types
import unittest
from typing import Any
from unittest.mock import Mock, patch

from skills import web_search


class DummyText:
    def __init__(self, value: str):
        self.value = value


class WebSearchTests(unittest.TestCase):
    def setUp(self) -> None:
        web_search._WEB_TOOL_TYPE = None  # reset cache

    @patch("skills.web_search.get_type_hints")
    def test_detect_web_tool_type_fallback_on_error(self, mock_hints: Any) -> None:
        mock_hints.side_effect = ValueError("boom")

        tool_type = web_search._detect_web_tool_type()

        self.assertEqual(tool_type, "web_search")

    def test_extract_text_handles_text_objects(self) -> None:
        message = types.SimpleNamespace(
            output=[
                {
                    "content": [
                        types.SimpleNamespace(text=DummyText("Result one")),
                        {"content": []},
                    ]
                }
            ]
        )

        text = web_search._extract_text(message)

        self.assertEqual(text, "Result one")

    def test_run_web_search_uses_latest_tool(self) -> None:
        mock_client = Mock()
        response = Mock()
        response.output_text = "Latest headlines delivered."
        mock_client.responses.create.return_value = response

        with patch.object(web_search, "_get_client", return_value=mock_client), patch.object(
            web_search, "_detect_web_tool_type", return_value="web_search_2025_08_26"
        ):
            result = web_search.run_web_search("news today")

        self.assertEqual(result, "Latest headlines delivered.")
        mock_client.responses.create.assert_called_once()
        tools = mock_client.responses.create.call_args.kwargs.get("tools")
        self.assertEqual(len(tools), 1)
        self.assertEqual(tools[0]["type"], "web_search_2025_08_26")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()

