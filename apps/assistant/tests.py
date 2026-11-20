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


class EmptyAnswerFake(FakeModel):
    def invoke(self, messages):
        return AIMessage(content=[{"type": "thinking", "thinking": "..."}])  # no text block: what a model that ran out of tokens returns


class EmptyAnswerTests(SimpleTestCase):
    def test_empty_answer_gives_the_friendly_text(self):
        answer, _ = graph.ask("hi", "t-2", None, "staff", "", llm=EmptyAnswerFake())
        self.assertIn("could not produce an answer", answer)

    def test_strict_raises_so_the_next_model_can_try(self):
        with self.assertRaises(graph.EmptyAnswer):
            graph.ask("hi", "t-3", None, "staff", "", llm=EmptyAnswerFake(), strict=True)


from unittest import mock  # noqa: E402

from django.contrib.auth import get_user_model  # noqa: E402
from django.test import TestCase  # noqa: E402
from rest_framework.test import APIClient  # noqa: E402

from apps.outlets.models import Client, ClientUser  # noqa: E402


@override_settings(ANTHROPIC_API_KEY="a", ASSISTANT_DATABASE_URL="postgresql://x/y", ASSISTANT_SCOPE_SECRET="s")
class QueriesVisibilityTests(TestCase):
    """The SQL behind an answer is shown to SocialSpork staff only, never to a customer."""

    def _chat(self, user):
        api = APIClient()
        api.force_authenticate(user)
        with mock.patch("apps.assistant.graph.ask", return_value=("The answer.", [{"sql": "SELECT 1"}])), \
                mock.patch("apps.assistant.graph.make_llm", return_value=object()):
            return api.post("/api/assistant/chat", {"message": "hi"}, format="json")

    def test_customer_gets_the_answer_without_queries(self):
        user = get_user_model().objects.create_user("cust", password="x")
        ClientUser.objects.create(user=user, client=Client.objects.create(name="Acme"), role="admin")
        res = self._chat(user)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["answer"], "The answer.")
        self.assertEqual(res.data["queries"], [])

    def test_staff_still_sees_the_queries(self):
        res = self._chat(get_user_model().objects.create_user("boss", password="x", is_staff=True))
        self.assertEqual(res.data["queries"], [{"sql": "SELECT 1"}])
