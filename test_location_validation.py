"""
Pytest tests for location validation module.

Tests the ComplaintLocation model and ComplaintLocationValidator class
to ensure proper validation of location data in complaint submissions.
"""

import pytest
from pydantic import ValidationError

from location_validation import (
    ComplaintLocation,
    ComplaintLocationValidator,
    LocationValidationError
)


class TestComplaintLocationModel:
    """Test cases for ComplaintLocation Pydantic model."""
    
    def test_valid_lat_lng_submission_passes(self):
        """Test that valid latitude and longitude coordinates pass validation."""
        location = ComplaintLocation(
            latitude=23.0225,
            longitude=72.5714
        )
        
        assert location.latitude == 23.0225
        assert location.longitude == 72.5714
        assert location.address is None
    
    def test_valid_text_address_only_submission_passes(self):
        """Test that valid text address without coordinates passes validation."""
        location = ComplaintLocation(
            address="Near Patel Chowk, Patan, Ward 5"
        )
        
        assert location.latitude is None
        assert location.longitude is None
        assert location.address == "Near Patel Chowk, Patan, Ward 5"
    
    def test_valid_both_coordinates_and_address_passes(self):
        """Test that providing both coordinates and address passes validation."""
        location = ComplaintLocation(
            latitude=23.0225,
            longitude=72.5714,
            address="Near Patel Chowk, Patan"
        )
        
        assert location.latitude == 23.0225
        assert location.longitude == 72.5714
        assert location.address == "Near Patel Chowk, Patan"
    
    def test_missing_location_is_rejected(self):
        """Test that missing location data (no coordinates, no address) is rejected with VAL_001."""
        with pytest.raises(ValidationError) as exc_info:
            ComplaintLocation()
        
        error_message = str(exc_info.value)
        assert "VAL_001" in error_message
        assert "Either latitude and longitude or address must be provided" in error_message
    
    def test_malformed_coordinates_only_latitude_rejected(self):
        """Test that providing only latitude without longitude is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ComplaintLocation(latitude=23.0225)
        
        error_message = str(exc_info.value)
        assert "together" in error_message.lower()
        assert "latitude and longitude must be provided together" in error_message.lower()
    
    def test_malformed_coordinates_only_longitude_rejected(self):
        """Test that providing only longitude without latitude is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ComplaintLocation(longitude=72.5714)
        
        error_message = str(exc_info.value)
        assert "together" in error_message.lower()
        assert "latitude and longitude must be provided together" in error_message.lower()
    
    def test_malformed_coordinates_latitude_out_of_range_high(self):
        """Test that latitude > 90 is rejected."""
        with pytest.raises(ValidationError):
            ComplaintLocation(latitude=91.0, longitude=72.5714)
    
    def test_malformed_coordinates_latitude_out_of_range_low(self):
        """Test that latitude < -90 is rejected."""
        with pytest.raises(ValidationError):
            ComplaintLocation(latitude=-91.0, longitude=72.5714)
    
    def test_malformed_coordinates_longitude_out_of_range_high(self):
        """Test that longitude > 180 is rejected."""
        with pytest.raises(ValidationError):
            ComplaintLocation(latitude=23.0225, longitude=181.0)
    
    def test_malformed_coordinates_longitude_out_of_range_low(self):
        """Test that longitude < -180 is rejected."""
        with pytest.raises(ValidationError):
            ComplaintLocation(latitude=23.0225, longitude=-181.0)
    
    def test_empty_address_is_rejected(self):
        """Test that empty string address is rejected with VAL_001."""
        with pytest.raises(ValidationError) as exc_info:
            ComplaintLocation(address="")
        
        error_message = str(exc_info.value)
        assert "VAL_001" in error_message
    
    def test_whitespace_only_address_is_rejected(self):
        """Test that whitespace-only address is rejected with VAL_001."""
        with pytest.raises(ValidationError) as exc_info:
            ComplaintLocation(address="   ")
        
        error_message = str(exc_info.value)
        assert "VAL_001" in error_message
    
    def test_address_maximum_length_boundary(self):
        """Test that address at maximum length (250 characters) passes."""
        max_address = "A" * 250
        location = ComplaintLocation(address=max_address)
        assert len(location.address) == 250
    
    def test_address_exceeds_maximum_length_rejected(self):
        """Test that address exceeding 250 characters is rejected."""
        long_address = "A" * 251
        with pytest.raises(ValidationError):
            ComplaintLocation(address=long_address)
    
    def test_coordinate_boundary_values(self):
        """Test that coordinate boundary values are accepted."""
        location = ComplaintLocation(latitude=-90, longitude=-180)
        assert location.latitude == -90
        assert location.longitude == -180
        
        location = ComplaintLocation(latitude=90, longitude=180)
        assert location.latitude == 90
        assert location.longitude == 180
    
    def test_coordinate_zero_values(self):
        """Test that zero coordinates are accepted."""
        location = ComplaintLocation(latitude=0, longitude=0)
        assert location.latitude == 0
        assert location.longitude == 0


class TestComplaintLocationValidator:
    """Test cases for ComplaintLocationValidator utility class."""
    
    def test_validate_coordinates_valid(self):
        """Test validate_coordinates with valid coordinates."""
        assert ComplaintLocationValidator.validate_coordinates(23.0225, 72.5714) is True
    
    def test_validate_coordinates_invalid_latitude_only(self):
        """Test validate_coordinates with only latitude."""
        assert ComplaintLocationValidator.validate_coordinates(23.0225, None) is False
    
    def test_validate_coordinates_invalid_longitude_only(self):
        """Test validate_coordinates with only longitude."""
        assert ComplaintLocationValidator.validate_coordinates(None, 72.5714) is False
    
    def test_validate_coordinates_invalid_both_none(self):
        """Test validate_coordinates with both None."""
        assert ComplaintLocationValidator.validate_coordinates(None, None) is False
    
    def test_validate_coordinates_out_of_range(self):
        """Test validate_coordinates with out of range values."""
        assert ComplaintLocationValidator.validate_coordinates(91.0, 72.5714) is False
        assert ComplaintLocationValidator.validate_coordinates(23.0225, 181.0) is False
    
    def test_validate_address_valid(self):
        """Test validate_address with valid address."""
        assert ComplaintLocationValidator.validate_address("Near Patel Chowk") is True
    
    def test_validate_address_empty_string(self):
        """Test validate_address with empty string."""
        assert ComplaintLocationValidator.validate_address("") is False
    
    def test_validate_address_whitespace_only(self):
        """Test validate_address with whitespace only."""
        assert ComplaintLocationValidator.validate_address("   ") is False
    
    def test_validate_address_none(self):
        """Test validate_address with None."""
        assert ComplaintLocationValidator.validate_address(None) is False
    
    def test_validate_location_data_valid_coordinates(self):
        """Test validate_location_data with valid coordinates."""
        is_valid, error = ComplaintLocationValidator.validate_location_data(
            latitude=23.0225,
            longitude=72.5714
        )
        assert is_valid is True
        assert error is None
    
    def test_validate_location_data_valid_address(self):
        """Test validate_location_data with valid address."""
        is_valid, error = ComplaintLocationValidator.validate_location_data(
            address="Test Address"
        )
        assert is_valid is True
        assert error is None
    
    def test_validate_location_data_invalid_no_data(self):
        """Test validate_location_data with no location data."""
        is_valid, error = ComplaintLocationValidator.validate_location_data()
        assert is_valid is False
        assert "VAL_001" in error
    
    def test_validate_location_data_invalid_only_latitude(self):
        """Test validate_location_data with only latitude."""
        is_valid, error = ComplaintLocationValidator.validate_location_data(
            latitude=23.0225
        )
        assert is_valid is False
        assert error is not None
    
    def test_get_validation_error_details_valid(self):
        """Test get_validation_error_details with valid data returns empty dict."""
        details = ComplaintLocationValidator.get_validation_error_details(
            latitude=23.0225,
            longitude=72.5714
        )
        assert details == {}
    
    def test_get_validation_error_details_invalid(self):
        """Test get_validation_error_details with invalid data returns error dict."""
        details = ComplaintLocationValidator.get_validation_error_details()
        
        assert "error" in details
        assert details["error"]["code"] == "VAL_001"
        assert details["error"]["message"] == "Either latitude and longitude or address must be provided"
        assert len(details["error"]["details"]) == 1
        assert details["error"]["details"][0]["field"] == "location"


class TestLocationValidationError:
    """Test cases for LocationValidationError custom exception."""
    
    def test_location_validation_error_creation(self):
        """Test that LocationValidationError can be created with proper attributes."""
        error = LocationValidationError(
            error_code="VAL_001",
            message="Test error message",
            field="location"
        )
        
        assert error.error_code == "VAL_001"
        assert error.message == "Test error message"
        assert error.field == "location"
    
    def test_location_validation_error_default_field(self):
        """Test that LocationValidationError has default field value."""
        error = LocationValidationError(
            error_code="VAL_001",
            message="Test error message"
        )
        
        assert error.field == "location"
    
    def test_location_validation_error_string_representation(self):
        """Test that LocationValidationError string representation is the message."""
        error = LocationValidationError(
            error_code="VAL_001",
            message="Test error message"
        )
        
        assert str(error) == "Test error message"


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_negative_coordinates(self):
        """Test negative coordinate values."""
        location = ComplaintLocation(latitude=-23.0225, longitude=-72.5714)
        assert location.latitude == -23.0225
        assert location.longitude == -72.5714
    
    def test_floating_point_precision(self):
        """Test high precision floating point coordinates."""
        location = ComplaintLocation(
            latitude=23.02250512345678,
            longitude=72.57140512345678
        )
        assert location.latitude == 23.02250512345678
        assert location.longitude == 72.57140512345678
    
    def test_address_with_special_characters(self):
        """Test address with special characters."""
        location = ComplaintLocation(
            address="Near Patel Chowk, Patan - Ward 5 (Near School)"
        )
        assert "Near Patel Chowk, Patan - Ward 5 (Near School)" == location.address
    
    def test_address_with_unicode(self):
        """Test address with unicode characters."""
        location = ComplaintLocation(address="पटेल चौक, पाटन")
        assert location.address == "पटेल चौक, पाटन"
    
    def test_very_short_address(self):
        """Test very short but valid address."""
        location = ComplaintLocation(address="A")
        assert location.address == "A"
    
    def test_coordinates_at_equator_and_prime_meridian(self):
        """Test coordinates at equator (0) and prime meridian (0)."""
        location = ComplaintLocation(latitude=0, longitude=0)
        assert location.latitude == 0
        assert location.longitude == 0
    
    def test_coordinates_at_antimeridian(self):
        """Test coordinates at antimeridian (180)."""
        location = ComplaintLocation(latitude=0, longitude=180)
        assert location.longitude == 180
        
        location = ComplaintLocation(latitude=0, longitude=-180)
        assert location.longitude == -180
    
    def test_coordinates_at_poles(self):
        """Test coordinates at north and south poles."""
        location = ComplaintLocation(latitude=90, longitude=0)
        assert location.latitude == 90
        
        location = ComplaintLocation(latitude=-90, longitude=0)
        assert location.latitude == -90
