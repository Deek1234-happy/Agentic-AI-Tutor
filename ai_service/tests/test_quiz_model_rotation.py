import unittest

from app.quiz.quiz_config import QuizMetadataConfig
from app.quiz.quiz_metadata import _call_groq_with_rotation


class FakeChoice:
    def __init__(self, content):
        self.message = type("Msg", (), {"content": content})()


class FakeResponse:
    def __init__(self, content):
        self.choices = [FakeChoice(content)]


class FakeCompletions:
    def __init__(self):
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs["model"])
        model = kwargs["model"]
        if model == "llama-3.1-8b-instant":
            raise Exception("404 model_not_found")
        if model == "llama-3.3-70b-versatile":
            return FakeResponse(
                '[{"chunk_id":"quiz_chunk_0","usable":true,"usability_reason":"","bloom_level":"understand","chunk_type":"definition","concepts":["math"],"keywords":["value"]}]'
            )
        raise AssertionError(f"Unexpected model: {model}")


class FakeChat:
    def __init__(self):
        self.completions = FakeCompletions()


class FakeClient:
    def __init__(self):
        self.chat = FakeChat()


class QuizMetadataRotationTests(unittest.TestCase):
    def test_call_groq_rotates_on_model_not_found(self):
        cfg = QuizMetadataConfig(
            models=("llama-3.1-8b-instant", "llama-3.3-70b-versatile"),
            max_retries=2,
            base_backoff=0.1,
        )

        result = _call_groq_with_rotation(
            FakeClient(),
            [{"_temp_id": "quiz_chunk_0", "text": "sample text"}],
            cfg,
            "sys prompt",
        )

        self.assertIsNotNone(result)
        self.assertEqual(result[0]["chunk_id"], "quiz_chunk_0")

    def test_env_override_is_used_for_model_list(self):
        import os
        os.environ["GROQ_QUIZ_MODELS"] = "custom-model-a, custom-model-b"
        try:
            cfg = QuizMetadataConfig()
            self.assertEqual(cfg.models, ("custom-model-a", "custom-model-b"))
        finally:
            os.environ.pop("GROQ_QUIZ_MODELS", None)

    def test_groq_call_does_not_force_json_mode(self):
        cfg = QuizMetadataConfig(models=("openai/gpt-oss-120b",), max_retries=1, base_backoff=0.1)

        captured = {}

        class CapturingCompletions:
            def create(self, **kwargs):
                captured.update(kwargs)
                return FakeResponse(
                    '[{"chunk_id":"quiz_chunk_0","usable":true,"usability_reason":"","bloom_level":"understand","chunk_type":"definition","concepts":["math"],"keywords":["value"]}]'
                )

        class CapturingChat:
            completions = CapturingCompletions()

        class CapturingClient:
            chat = CapturingChat()

        result = _call_groq_with_rotation(
            CapturingClient(),
            [{"_temp_id": "quiz_chunk_0", "text": "sample text"}],
            cfg,
            "sys prompt",
        )

        self.assertIsNotNone(result)
        self.assertNotIn("response_format", captured)

    def test_default_batch_is_small_enough_for_groq(self):
        cfg = QuizMetadataConfig()
        self.assertLessEqual(cfg.batch_size, 2)


if __name__ == "__main__":
    unittest.main()
