"""
Location Field Validation Module for NAGRIK AI Complaint System

Validation Rules:
- Location must be provided as either:
  1. Latitude + Longitude coordinates, OR
  2. A non-empty text address.
- Reject submissions with VAL_001 if neither is provided.
- No GPS auto-capture is performed; only validates received data.
"""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ComplaintLocation(BaseModel):
    """Complaint location validation schema."""

    latitude: Optional[float] = Field(
        default=None,
        ge=-90,
        le=90,
        description="GPS latitude (-90 to 90)",
    )

    longitude: Optional[float] = Field(
        default=None,
        ge=-180,
        le=180,
        description="GPS longitude (-180 to 180)",
    )

    address: Optional[str] = Field(
        default=None,
        max_length=250,
        description="Text address or landmark",
    )

    @model_validator(mode="after")
    def validate_location(self):
        has_latitude = self.latitude is not None
        has_longitude = self.longitude is not None
        has_address = bool(self.address and self.address.strip())

        # Coordinates must be provided together
        if has_latitude != has_longitude:
            raise ValueError(
                "Latitude and longitude must be provided together."
            )

        # Either coordinates OR address is required
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
                },
                {
                    "address": "Near Patel Chowk, Patan",
                },
                {
                    "latitude": 23.0225,
                    "longitude": 72.5714,
                    "address": "Near Patel Chowk, Patan",
                },
            ]
        }
    )


class ComplaintLocationValidator:
    """Utility validation methods."""

    @staticmethod
    def validate_coordinates(
        latitude: Optional[float],
        longitude: Optional[float],
    ) -> bool:
        if latitude is None or longitude is None:
            return False

        return (-90 <= latitude <= 90) and (-180 <= longitude <= 180)

    @staticmethod
    def validate_address(address: Optional[str]) -> bool:
        return bool(address and address.strip())

    @staticmethod
    def validate_location_data(
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        address: Optional[str] = None,
    ):
        has_latitude = latitude is not None
        has_longitude = longitude is not None

        if has_latitude != has_longitude:
            return False, "Latitude and longitude must be provided together."

        if ComplaintLocationValidator.validate_coordinates(
            latitude, longitude
        ):
            return True, None

        if ComplaintLocationValidator.validate_address(address):
            return True, None

        return (
            False,
            "VAL_001: Either latitude and longitude or address must be provided.",
        )

    @staticmethod
    def get_validation_error_details(
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        address: Optional[str] = None,
    ):
        valid, error = ComplaintLocationValidator.validate_location_data(
            latitude,
            longitude,
            address,
        )

        if valid:
            return {}

        code = (
            "VAL_001"
            if "VAL_001" in error
            else "VAL_002"
        )

        return {
            "error": {
                "code": code,
                "message": error,
                "details": [
                    {
                        "field": "location",
                        "message": error,
                    }
                ],
            }
        }
