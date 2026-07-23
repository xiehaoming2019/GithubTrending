from __future__ import annotations

import unittest

from github_trending_daily.summarize import _parse_json_response, _response_text


class SummarizeTests(unittest.TestCase):
    def test_extracts_responses_api_text(self) -> None:
        response = {
            "output": [
                {
                    "type": "message",
                    "content": [
                        {
                            "type": "output_text",
                            "text": '{"summary":"示例"}',
                        }
                    ],
                }
            ]
        }
        self.assertEqual('{"summary":"示例"}', _response_text(response))

    def test_accepts_fenced_json_defensively(self) -> None:
        data = _parse_json_response('```json\n{"summary":"示例"}\n```')
        self.assertEqual("示例", data["summary"])


if __name__ == "__main__":
    unittest.main()

