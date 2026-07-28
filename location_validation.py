""" NOTE:
Location Field Validation Module for NAGRIK AI Complaint System

This module implements location validation logic ensuring that complaint submissions
include valid location data either as GPS coordinates (latitude/longitude) or as a
non-empty text address.

Error Code: VAL_001 - Returned when neither valid coordinates nor address is provided
"""

from pydantic import BaseModel, Field, model_validator, ConfigDict
from typing import Optional


class LocationValidationError(Exception):
    """Custom exception for location validation failures."""
    
    def __init__(self, error_code: str, message: str, field: str = "location"):
        self.error_code = error_code
        self.message = message
        self.field = field
        super().__init__(message)


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
    
    Error Codes:
    - VAL_001: Neither valid coordinates nor address provided
    """
    
    latitude: Optional[float] = Field(
        default=None,
        ge=-90,
        le=90,
        description="GPS latitude coordinate (-90 to 90)",
    )
    
    longitude: Optional[float] = Field(
        default=None,
        ge=-180,
        le=180,
        description="GPS longitude coordinate (-180 to 180)",
    )
    
    address: Optional[str] = Field(
        default=None,
        max_length=250,
        description="Text address, ward, or landmark (max 250 characters)",
    )
    
    @model_validator(mode="after")
    def validate_location(self) -> "ComplaintLocation":
        """
        Validate that location data is provided in an acceptable format.
        
        Returns:
            self: The validated location object
            
        Raises:
            ValueError: If validation fails with appropriate error message
        """
        has_latitude = self.latitude is not None
        has_longitude = self.longitude is not None
        has_address = bool(self.address and self.address.strip())
        
        # Check if coordinates are provided as a pair
        if has_latitude != has_longitude:
            raise ValueError(
                "Latitude and longitude must be provided together."
            )
        
        # Check if at least one valid location format is provided
        if not has_address and not (has_latitude and has_longitude):
            raise ValueError(
                "VAL_001: Either latitude and longitude or address must be provided."
            )
        
        return self
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "latitude": 23.0225,
                    "longitude": 72.5714,
                    "address": "Near Patel Chowk, Patan"
                },
                {
                    "latitude": 23.0225,
                    "longitude": 72.5714
                },
                {
                    "address": "Near Patel Chowk, Patan, Ward 5"
                }
            ]
        }
    )


class ComplaintLocationValidator:
    """
    Validator class for complaint location data with additional utility methods.
    
    This class provides static methods for location validation and can be used
    independently of the Pydantic model for custom validation scenarios.
    """
    
    @staticmethod
    def validate_coordinates(latitude: Optional[float], longitude: Optional[float]) -> bool:
        """
        Validate GPS coordinates.
        
        Args:
            latitude: Latitude value (-90 to 90)
            longitude: Longitude value (-180 to 180)
            
        Returns:
            bool: True if coordinates are valid, False otherwise
        """
        if latitude is None or longitude is None:
            return False
        
        return (-90 <= latitude <= 90) and (-180 <= longitude <= 180)
    
    @staticmethod
    def validate_address(address: Optional[str]) -> bool:
        """
        Validate text address.
        
        Args:
            address: Address string
            
        Returns:
            bool: True if address is valid (non-empty after trimming), False otherwise
        """
        if address is None:
            return False
        
        return bool(address.strip())
    
    @staticmethod
    def validate_location_data(
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        address: Optional[str] = None
    ) -> tuple[bool, Optional[str]]:
        """
        Comprehensive location data validation.
        
        Args:
            latitude: Optional latitude coordinate
            longitude: Optional longitude coordinate
            address: Optional text address
            
        Returns:
            tuple: (is_valid: bool, error_message: Optional[str])
        """
        has_valid_coordinates = ComplaintLocationValidator.validate_coordinates(
            latitude, longitude
        )
        has_valid_address = ComplaintLocationValidator.validate_address(address)
        
        if has_valid_coordinates or has_valid_address:
            return True, None
        
        return False, "VAL_001: Either latitude and longitude or address must be provided."
    
    @staticmethod
    def get_validation_error_details(
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        address: Optional[str] = None
    ) -> dict:
        """
        Get detailed validation error information for API responses.
        
        Args:
            latitude: Optional latitude coordinate
            longitude: Optional longitude coordinate
            address: Optional text address
            
        Returns:
            dict: Error details in standard API format
        """
        is_valid, error_message = ComplaintLocationValidator.validate_location_data(
            latitude, longitude, address
        )
        
        if is_valid:
            return {}
        
        return {
            "error": {
                "code": "VAL_001",
                "message": "Either latitude and longitude or address must be provided",
                "details": [
                    {
                        "field": "location",
                        "message": error_message
                    }
                ]
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
            latitude=23.0225,
            longitude=72.5714,
            address="Near Patel Chowk, Patan"
        )
        print("✓ Test 3 PASSED: Valid both coordinates and address")
    except ValueError as e:
        print(f"✗ Test 3 FAILED: {e}")
    
    # Test Case 4: Invalid - missing both
    try:
        loc4 = ComplaintLocation()
        print("✗ Test 4 FAILED: Should reject missing both")
    except ValueError as e:
        if "VAL_001" in str(e):
            print("✓ Test 4 PASSED: Correctly rejected missing both with VAL_001")
        else:
            print(f"✗ Test 4 FAILED: Wrong error: {e}")
    
    # Test Case 5: Invalid - only latitude
    try:
        loc5 = ComplaintLocation(latitude=23.0225)
        print("✗ Test 5 FAILED: Should reject only latitude")
    except ValueError as e:
        if "together" in str(e):
            print("✓ Test 5 PASSED: Correctly rejected only latitude")
        else:
            print(f"✗ Test 5 FAILED: Wrong error: {e}")
    
    # Test Case 6: Invalid - only longitude
    try:
        loc6 = ComplaintLocation(longitude=72.5714)
        print("✗ Test 6 FAILED: Should reject only longitude")
    except ValueError as e:
        if "together" in str(e):
            print("✓ Test 6 PASSED: Correctly rejected only longitude")
        else:
            print(f"✗ Test 6 FAILED: Wrong error: {e}")
    
    # Test Case 7: Invalid - empty address
    try:
        loc7 = ComplaintLocation(address="   ")
        print("✗ Test 7 FAILED: Should reject empty address")
    except ValueError as e:
        if "VAL_001" in str(e):
            print("✓ Test 7 PASSED: Correctly rejected empty address with VAL_001")
        else:
            print(f"✗ Test 7 FAILED: Wrong error: {e}")
    
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
    
    # Test static validator methods
    print("\n" + "=" * 50)
    print("Static Validator Tests\n")
    
    is_valid, error = ComplaintLocationValidator.validate_location_data(
        latitude=23.0225, longitude=72.5714
    )
    print(f"Valid coordinates: {is_valid}, Error: {error}")
    
    is_valid, error = ComplaintLocationValidator.validate_location_data(
        address="Test Address"
    )
    print(f"Valid address: {is_valid}, Error: {error}")
    
    is_valid, error = ComplaintLocationValidator.validate_location_data()
    print(f"Invalid (no data): {is_valid}, Error: {error}")
    
    error_details = ComplaintLocationValidator.get_validation_error_details()
    print(f"\nError details for invalid location: {error_details}")
