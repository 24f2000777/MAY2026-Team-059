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

# Fixed set, one per ComplaintCategory grouping (see
# app/services/routing_service.py). The department-routing LLM prompt
# (app/chatbot/prompts.py) is constrained to only ever return one of
# these exact names.
DEPARTMENT_NAMES = [
    "Roads Department",
    "Water Supply Department",
    "Drainage & Sewerage Department",
    "Solid Waste Management Department",
    "Street Lighting & Electrical Department",
    "General Administration Department",
]