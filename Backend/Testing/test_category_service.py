"""
Pytest suite for app/services/category_service.py: mapping the LLM's
BMC 13-category taxonomy down to our own 10-value ComplaintCategory
enum, and falling back to "other" when extraction fails or the LLM
decides the text isn't a genuine complaint.

test_predict_category hits the real LLM (Groq), same reasoning as
the other unmocked chatbot/extraction-dependent suites in this
project (test_chat_service.py) — this is genuinely what needs
proving, a mock would just assert the mock's own canned response.
"""

from app.services.category_service import BMC_TO_OUR_CATEGORY, predict_category


class TestBmcToOurCategoryMapping:
    def test_every_mapped_value_is_a_real_category(self):
        # Mirrors ComplaintCategory's actual values (app/schemas/complaint.py)
        # without importing it, so this test fails loudly if the enum and
        # this mapping table ever drift apart independently.
        valid_categories = {
            "road", "pothole", "streetlight", "drainage", "garbage",
            "water_supply", "sewage", "traffic", "electricity", "other",
        }

        assert set(BMC_TO_OUR_CATEGORY.values()) <= valid_categories

    def test_known_mappings(self):
        assert BMC_TO_OUR_CATEGORY["Pothole / Road Damage"] == "pothole"
        assert BMC_TO_OUR_CATEGORY["Water Supply Disruption"] == "water_supply"
        assert BMC_TO_OUR_CATEGORY["Water Leakage / Pipe Burst"] == "water_supply"
        assert BMC_TO_OUR_CATEGORY["Solid Waste / Garbage"] == "garbage"
        assert BMC_TO_OUR_CATEGORY["Street Light Failure"] == "streetlight"

    def test_categories_with_no_direct_match_fall_back_to_other(self):
        assert BMC_TO_OUR_CATEGORY["Illegal Construction"] == "other"
        assert BMC_TO_OUR_CATEGORY["Stray Animal Menace"] == "other"


class TestPredictCategory:
    async def test_maps_a_clear_pothole_complaint(self):
        category = await predict_category(
            "There is a massive pothole on the main road outside my house, "
            "cars keep hitting it and it's getting worse every day."
        )

        assert category == "pothole"

    async def test_maps_a_clear_garbage_complaint(self):
        category = await predict_category(
            "Garbage has not been collected from our street in over two weeks, "
            "it is piling up and starting to smell."
        )

        assert category == "garbage"

    async def test_returns_a_valid_category_for_unrelated_text(self):
        # Not a real civic complaint at all — extract_complaint_info should
        # come back with complaint_category=None, predict_category should
        # still return a usable value rather than propagate that None.
        category = await predict_category("What's the weather like today?")

        assert category in set(BMC_TO_OUR_CATEGORY.values()) | {"other"}
