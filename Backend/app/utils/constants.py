"""
Application constants.

Avoid hardcoding strings across the project.
"""

# =====================================================
# User Roles
# =====================================================

ROLE_CITIZEN = "citizen"
ROLE_STAFF = "staff"
ROLE_ADMIN = "admin"

# =====================================================
# OTP Purposes
# =====================================================

OTP_VERIFY_EMAIL = "verify_email"
OTP_RESET_PASSWORD = "reset_password"

# =====================================================
# Token Types
# =====================================================

ACCESS_TOKEN = "access"
REFRESH_TOKEN = "refresh"

# =====================================================
# Departments
# =====================================================

# Fixed set, one per ComplaintCategory grouping (see CATEGORY_TO_DEPARTMENT
# below).
DEPARTMENT_NAMES = [
    "Roads Department",
    "Water Supply Department",
    "Drainage & Sewerage Department",
    "Solid Waste Management Department",
    "Street Lighting & Electrical Department",
    "General Administration Department",
]

# Deterministic category -> department routing (app/services/routing_service.py's
# route_complaint), a straight lookup rather than an LLM call: both sides
# are already fixed, controlled sets, category is never free text by the
# time a complaint reaches routing, so there's no actual ambiguity for a
# model to resolve, and asking one anyway is just an unnecessary source of
# misrouting (confirmed in practice: a real drainage complaint got routed
# to General Administration). Every app.schemas.complaint.ComplaintCategory
# value must have an entry here, enforced by
# Testing/test_routing_service.py's test_every_category_has_a_department_mapping.
CATEGORY_TO_DEPARTMENT = {
    "road": "Roads Department",
    "pothole": "Roads Department",
    "traffic": "Roads Department",
    "water_supply": "Water Supply Department",
    "drainage": "Drainage & Sewerage Department",
    "sewage": "Drainage & Sewerage Department",
    "garbage": "Solid Waste Management Department",
    "streetlight": "Street Lighting & Electrical Department",
    "electricity": "Street Lighting & Electrical Department",
    "other": "General Administration Department",
}