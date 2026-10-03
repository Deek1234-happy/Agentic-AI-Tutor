import os
import unittest
from unittest.mock import patch

from app.llm import get_gemini_api_key


class GeminiApiKeyRoutingTests(unittest.TestCase):
    def test_feature_keys_are_independent_and_override_legacy_key(self):
        environment = {
            "GOOGLE_API_KEY": "legacy-key",
            "GEMINI_CHAT_API_KEY": "chat-key",
            "GEMINI_KG_API_KEY": "kg-key",
            "GEMINI_QUIZ_API_KEY": "quiz-key",
            "GEMINI_TTS_API_KEY": "tts-key",
        }

        with patch.dict(os.environ, environment, clear=True):
            self.assertEqual(get_gemini_api_key("GEMINI_CHAT_API_KEY"), "chat-key")
            self.assertEqual(get_gemini_api_key("GEMINI_KG_API_KEY"), "kg-key")
            self.assertEqual(get_gemini_api_key("GEMINI_QUIZ_API_KEY"), "quiz-key")
            self.assertEqual(get_gemini_api_key("GEMINI_TTS_API_KEY"), "tts-key")

    def test_legacy_key_is_used_when_feature_key_is_missing(self):
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "legacy-key"}, clear=True):
            self.assertEqual(get_gemini_api_key("GEMINI_CHAT_API_KEY"), "legacy-key")


if __name__ == "__main__":
    unittest.main()