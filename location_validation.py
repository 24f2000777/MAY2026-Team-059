"""
Location Field Validation Module for NAGRIK AI Complaint System

This module validates complaint submissions to ensure they include valid
location data either as GPS coordinates (latitude/longitude) or as a
non-empty text address.

Error Codes:
- VAL_001: Neither valid coordinates nor a valid address was provided.
- VAL_002: Only one of latitude/longitude was provided (they must be given together).
"""

from typing import Optional
from pydantic import BaseModel, Field, model_validator, ConfigDict

# Centralized error code catalog
VAL_001 = "VAL_001"
VAL_002 = "VAL_002"

ERROR_MESSAGES = {
    VAL_001: "Either latitude and longitude or address must be provided.",
    VAL_002: "Latitude and longitude must be provided together.",
}


class LocationValidationError(ValueError):
    """Custom exception for location validation failures.

    Subclasses ValueError so pydantic's model_validator (which only
    auto-wraps ValueError/TypeError/AssertionError into its own
    ValidationError) correctly catches and wraps this exception instead
    of letting it propagate as an unhandled custom exception type.
    """

    def __init__(self, error_code: str, message: str, field: str = "location"):
        self.error_code = error_code
        self.message = message
        self.field = field
        super().__init__(f"{error_code}: {message}")


class ComplaintLocation(BaseModel):
    """
    Complaint location validation schema.

    Validation Rules:
    - Either latitude + longitude (both required together), OR
    - A non-empty text address must be provided
    - Latitude must be between -90 and 90 degrees
    - Longitude must be between -180 and 180 degrees
    - Address maximum length: 250 characters
    - Address cannot be empty or whitespace only
    """

    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    address: Optional[str] = Field(default=None, max_length=250)

    @model_validator(mode="after")
    def validate_location(self) -> "ComplaintLocation":
        """Validate that location data is provided in an acceptable format."""
        has_latitude = self.latitude is not None
        has_longitude = self.longitude is not None
        has_address = bool(self.address and self.address.strip())

        if has_latitude != has_longitude:
            raise LocationValidationError(VAL_002, ERROR_MESSAGES[VAL_002])
        if not has_address and not (has_latitude and has_longitude):
            raise LocationValidationError(VAL_001, ERROR_MESSAGES[VAL_001])
        return self

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"latitude": 23.0225, "longitude": 72.5714},
                {"address": "Near Patel Chowk, Patan, Ward 5"},
            ]
        }
    )


class ComplaintLocationValidator:
    """Validator utilities for complaint location data."""

    @staticmethod
    def validate_coordinates(latitude: Optional[float], longitude: Optional[float]) -> bool:
        """Return True if both coordinates are present and within valid ranges."""
        if latitude is None or longitude is None:
            return False
        return -90 <= latitude <= 90 and -180 <= longitude <= 180

    @staticmethod
    def validate_address(address: Optional[str]) -> bool:
        """Return True if address contains non-whitespace text."""
        return bool(address and address.strip())

    @staticmethod
    def validate_location_data(
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        address: Optional[str] = None,
    ) -> tuple[bool, Optional[str]]:
        """
        Validate location data.

        Returns:
            (is_valid, error_code). error_code is None if valid.
        """
        has_latitude = latitude is not None
        has_longitude = longitude is not None

        if has_latitude != has_longitude:
            return False, VAL_002
        if ComplaintLocationValidator.validate_coordinates(latitude, longitude) or ComplaintLocationValidator.validate_address(address):
            return True, None
        return False, VAL_001

    @staticmethod
    def get_validation_error_details(
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        address: Optional[str] = None,
    ) -> dict:
        """
        Return API-ready error details, or an empty dict if valid.
        """
        is_valid, error_code = ComplaintLocationValidator.validate_location_data(latitude, longitude, address)
        if is_valid:
            return {}
        return {
            "error": {
                "code": error_code,
                "message": ERROR_MESSAGES[error_code],
                "details": [{"field": "location", "message": ERROR_MESSAGES[error_code]}],
            }
        }


# Example usage and test cases
if __name__ == "__main__":
    print("Location Validation Test Cases\n")
    print("=" * 50)

    # Test Case 1: Valid coordinates only
    try:
        loc1 = ComplaintLocation(latitude=23.0225, longitude=72.5714)
        print("✓ Test 1 PASSED: Valid coordinates only")
    except ValueError as e:
        print(f"✗ Test 1 FAILED: {e}")

    # Test Case 2: Valid address only
    try:
        loc2 = ComplaintLocation(address="Near Patel Chowk, Patan")
        print("✓ Test 2 PASSED: Valid address only")
    except ValueError as e:
        print(f"✗ Test 2 FAILED: {e}")

    # Test Case 3: Valid both coordinates and address
    try:
        loc3 = ComplaintLocation(
            latitude=23.0225, longitude=72.5714, address="Near Patel Chowk, Patan"
        )
        print("✓ Test 3 PASSED: Valid both coordinates and address")
    except ValueError as e:
        print(f"✗ Test 3 FAILED: {e}")

    # Test Case 4: Invalid - missing both
    try:
        loc4 = ComplaintLocation()
        print("✗ Test 4 FAILED: Should reject missing both")
    except ValueError as e:
        print("✓ Test 4 PASSED: Correctly rejected missing both" if VAL_001 in str(e)
              else f"✗ Test 4 FAILED: Wrong error: {e}")

    # Test Case 5: Invalid - only latitude
    try:
        loc5 = ComplaintLocation(latitude=23.0225)
        print("✗ Test 5 FAILED: Should reject only latitude")
    except ValueError as e:
        print("✓ Test 5 PASSED: Correctly rejected only latitude" if VAL_002 in str(e)
              else f"✗ Test 5 FAILED: Wrong error: {e}")

    # Test Case 6: Invalid - only longitude
    try:
        loc6 = ComplaintLocation(longitude=72.5714)
        print("✗ Test 6 FAILED: Should reject only longitude")
    except ValueError as e:
        print("✓ Test 6 PASSED: Correctly rejected only longitude" if VAL_002 in str(e)
              else f"✗ Test 6 FAILED: Wrong error: {e}")

    # Test Case 7: Invalid - empty address
    try:
        loc7 = ComplaintLocation(address="   ")
        print("✗ Test 7 FAILED: Should reject empty address")
    except ValueError as e:
        print("✓ Test 7 PASSED: Correctly rejected empty address" if VAL_001 in str(e)
              else f"✗ Test 7 FAILED: Wrong error: {e}")

    # Test Case 8: Boundary values
    try:
        loc8 = ComplaintLocation(latitude=-90, longitude=-180)
        print("✓ Test 8 PASSED: Valid boundary values")
    except ValueError as e:
        print(f"✗ Test 8 FAILED: {e}")

    # Test Case 9: Invalid coordinates out of range
    try:
        loc9 = ComplaintLocation(latitude=91, longitude=0)
        print("✗ Test 9 FAILED: Should reject invalid latitude")
    except ValueError as e:
        print("✓ Test 9 PASSED: Correctly rejected invalid latitude")

    print("\n" + "=" * 50)
    print("Static Validator Tests\n")

    print(ComplaintLocationValidator.validate_location_data(latitude=23.0225, longitude=72.5714))
    print(ComplaintLocationValidator.validate_location_data(address="Test Address"))
    print(ComplaintLocationValidator.validate_location_data())
    print(ComplaintLocationValidator.validate_location_data(latitude=23.0225))
    print(ComplaintLocationValidator.get_validation_error_details())
    print(ComplaintLocationValidator.get_validation_error_details(latitude=23.0225))
