"""
Real BMC administrative wards (Mumbai has exactly 24, ward codes A-T with
a few split into /N, /S, /E, /W sub-wards). Extracted from the priority
scorer's own training data (app/ml/priority_scorer/data/bmc_train.csv),
where each ward_code maps to exactly one ward_area/zone/ward_type/
population_density/ward_slum_percentage combination, confirmed by
grouping the 960k-row dataset by ward_code and checking each of those
columns has exactly one distinct value per ward.

Only ward_slum_percentage is actually used by the priority model today
(see priority_scorer/features.py), the rest is kept here for display
purposes (dropdown labels, admin/reporting views) since it's real data
already extracted, not extra guesswork.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Ward:
    code: str
    area: str
    zone: str
    ward_type: str
    population_density: str
    slum_percentage: int


WARDS: dict[str, Ward] = {
    w.code: w
    for w in [
        Ward("A", "Colaba-Fort", "City", "South", "High", 12),
        Ward("B", "Mandvi-Masjid", "City", "South", "Very High", 28),
        Ward("C", "Girgaon-Marine Lines", "City", "South", "High", 15),
        Ward("D", "Worli-Prabhadevi", "City", "South", "High", 22),
        Ward("E", "Byculla-Mazgaon", "City", "South", "Very High", 35),
        Ward("F/N", "Sion-Dharavi", "City", "Central", "Very High", 55),
        Ward("F/S", "Wadala-Antop Hill", "City", "Central", "High", 40),
        Ward("G/N", "Dharavi-Matunga", "City", "Central", "Very High", 60),
        Ward("G/S", "Dadar-Mahim", "City", "Central", "High", 25),
        Ward("H/E", "Bandra East", "Western", "Suburban", "High", 38),
        Ward("H/W", "Bandra West", "Western", "Suburban", "Medium", 10),
        Ward("K/E", "Andheri East", "Western", "Suburban", "High", 30),
        Ward("K/W", "Andheri West-Juhu", "Western", "Suburban", "Medium", 18),
        Ward("L", "Kurla-Vidyavihar", "Eastern", "Suburban", "Very High", 45),
        Ward("M/E", "Govandi-Mankhurd", "Eastern", "Suburban", "High", 65),
        Ward("M/W", "Chembur West", "Eastern", "Suburban", "High", 32),
        Ward("N", "Ghatkopar", "Eastern", "Suburban", "High", 28),
        Ward("P/N", "Malad", "Western", "Suburban", "High", 35),
        Ward("P/S", "Goregaon", "Western", "Suburban", "High", 30),
        Ward("R/C", "Borivali Central", "Western", "Suburban", "Medium", 22),
        Ward("R/N", "Dahisar", "Western", "Suburban", "Medium", 20),
        Ward("R/S", "Kandivali", "Western", "Suburban", "Medium", 18),
        Ward("S", "Bhandup-Mulund", "Eastern", "Suburban", "Medium", 25),
        Ward("T", "Mulund", "Eastern", "Suburban", "Low", 15),
    ]
}

# Used when a complaint has no ward_code (not every submission path collects
# one yet, e.g. complaints filed through the chatbot before it can ask for a
# ward), rather than defaulting to 0, which would understate risk for every
# complaint from a real but unspecified ward. 33 is the real row-weighted
# mean ward_slum_percentage across the 960k-row training set (not just an
# average of the 24 wards above, complaint volume isn't evenly spread
# across them) — a neutral, data-backed middle-of-the-road value.
DEFAULT_SLUM_PERCENTAGE = 33
