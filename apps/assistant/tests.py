from django.test import SimpleTestCase, override_settings

from .graph import providers


class ProviderOrderTests(SimpleTestCase):
    @override_settings(ANTHROPIC_API_KEY="a", GEMINI_API_KEY="g", ASSISTANT_PROVIDER="anthropic", ASSISTANT_FALLBACK=True)
    def test_preferred_first_then_the_other(self):
        self.assertEqual(providers(), ["anthropic", "gemini"])

    @override_settings(ANTHROPIC_API_KEY="a", GEMINI_API_KEY="g", ASSISTANT_PROVIDER="gemini", ASSISTANT_FALLBACK=True)
    def test_gemini_can_be_the_preferred_one(self):
        self.assertEqual(providers(), ["gemini", "anthropic"])

    @override_settings(ANTHROPIC_API_KEY="a", GEMINI_API_KEY="g", ASSISTANT_PROVIDER="gemini", ASSISTANT_FALLBACK=False)
    def test_no_fallback_means_one_model(self):
        self.assertEqual(providers(), ["gemini"])

    @override_settings(ANTHROPIC_API_KEY="a", GEMINI_API_KEY="", ASSISTANT_PROVIDER="gemini", ASSISTANT_FALLBACK=True)
    def test_a_model_without_a_key_is_skipped(self):
        self.assertEqual(providers(), ["anthropic"])

    @override_settings(ANTHROPIC_API_KEY="", GEMINI_API_KEY="", ASSISTANT_PROVIDER="anthropic")
    def test_no_keys_means_none(self):
        self.assertEqual(providers(), [])


from langchain_core.messages import AIMessage  # noqa: E402

from . import graph, prompt  # noqa: E402


class PromptTests(SimpleTestCase):
    def test_compact_schema_is_short_and_keeps_every_column(self):
        text = prompt.compact_schema({"reviews": ["rating (integer)", "reviewed_at (timestamp with time zone)"], "alerts": ["title (text)"]})
        self.assertEqual(text, "reviews(rating int, reviewed_at ts)\nalerts(title text)")

    def test_fixed_part_has_no_per_request_text_so_it_can_be_cached(self):
        fixed, dynamic = prompt.parts("A user of client X", "ON PAGE Y", "Monday 17 November 2026, 12:00", 200, "reviews(rating int)")
        self.assertIn("SCHEMA", fixed)
        self.assertIn("reviews(rating int)", fixed)
        self.assertNotIn("client X", fixed)
        self.assertNotIn("17 November", fixed)
        self.assertIn("client X", dynamic)
        self.assertIn("17 November", dynamic)
        self.assertIn("ON PAGE Y", dynamic)

    def test_claude_gets_a_cache_marker_on_the_fixed_part_only(self):
        class ChatAnthropic:
            pass
        msg = graph._system_message(ChatAnthropic(), "fixed", "dynamic")
        self.assertEqual(msg.content[0]["cache_control"], {"type": "ephemeral"})
        self.assertNotIn("cache_control", msg.content[1])

    def test_other_models_get_plain_text_fixed_part_first(self):
        class Other:
            pass
        self.assertEqual(graph._system_message(Other(), "fixed", "dynamic").content, "fixed\ndynamic")


class FakeModel:
    """Answers without calling any service, so a whole turn can run in a test."""
    def bind_tools(self, tools):
        return self

    def invoke(self, messages):
        self.system = messages[0]
        return AIMessage(content="Done.")


class TurnTests(SimpleTestCase):
    @override_settings(ANTHROPIC_API_KEY="a")
    def test_a_turn_runs_and_the_system_prompt_has_the_pieces(self):
        fake = FakeModel()
        answer, trace = graph.ask("hi", "t-1", None, "SocialSpork staff", "", llm=fake)
        self.assertEqual(answer, "Done.")
        self.assertIn("SocialSpork staff", fake.system.content)
