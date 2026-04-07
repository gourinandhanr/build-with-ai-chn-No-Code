"""
models.py – Pydantic request / response schemas.

Every field is documented so the auto-generated OpenAPI docs (Swagger UI)
are immediately useful for frontend engineers.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


# ── Shared value objects ─────────────────────────────────────────────────────

class Coordinates(BaseModel):
    """Geographic coordinates."""
    lat: float = Field(..., description="Latitude")
    lng: float = Field(..., description="Longitude")


class RouteStep(BaseModel):
    """A single manoeuvre inside a route leg."""
    instruction: str = Field(..., description="Human-readable turn instruction")
    distance: str = Field(..., description="Distance for this step, e.g. '1.2 km'")
    duration: str = Field(..., description="Duration for this step, e.g. '3 mins'")


class RouteInfo(BaseModel):
    """Aggregated route information returned by the Directions API."""
    distance: str = Field(..., description="Total route distance, e.g. '12.4 km'")
    duration: str = Field(..., description="Total estimated travel time, e.g. '25 mins'")
    steps: list[RouteStep] = Field(default_factory=list, description="Ordered manoeuvre list")
    waypoints: list[str] = Field(
        default_factory=list,
        description="Ordered waypoint addresses (reverse-geocoded)",
    )


# ── /optimize-pickup ─────────────────────────────────────────────────────────

class OptimizePickupRequest(BaseModel):
    """Request body for POST /optimize-pickup."""
    user_id: str = Field(..., description="Unique user identifier, e.g. 'U123'")
    address: str = Field(..., description="Full street address for pickup")


class OptimizePickupResponse(BaseModel):
    """Response for POST /optimize-pickup."""
    user_id: str
    should_pick_up_today: bool = Field(
        ..., description="Whether a pickup is warranted today"
    )
    pickup_address: str | None = Field(
        None, description="The address that was geocoded (echoed back)"
    )
    pickup_coordinates: Coordinates | None = Field(
        None, description="Geocoded lat/lng of the pickup address"
    )
    route: RouteInfo | None = Field(
        None, description="Optimised route details (only when pickup is true)"
    )
    message: str = Field(
        "OK", description="Human-readable status / explanation"
    )


# ── /pickup-locations-today ──────────────────────────────────────────────────

class PickupLocation(BaseModel):
    """One scheduled pickup location for today."""
    user_id: str
    address: str
    coordinates: Coordinates
    priority: int = Field(
        ...,
        description="1 = highest priority (heaviest / most urgent)",
    )
    latest_weight: float = Field(
        ..., description="Most recent weight value (kg)"
    )


# ── Dashboard Additions ──────────────────────────────────────────────────────

class UserCreate(BaseModel):
    """Request body for creating a new user."""
    user_id: str = Field(..., description="Unique ID for the new user")
    address: str = Field(..., description="Pickup address for the user")


from datetime import date as dt_date

class WeightUpdate(BaseModel):
    """Request body for logging daily weight."""
    user_id: str = Field(..., description="Unique ID of the user")
    date: dt_date = Field(..., description="Date of the weight record")
    weight: float = Field(..., description="Weight in kg")
