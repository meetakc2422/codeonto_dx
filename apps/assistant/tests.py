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
