"""
pickup_locations.py – Business logic for the /pickup-locations-today endpoint.

Aggregates the database query (who should be picked up?) with Maps geocoding
(where are they?) and returns a priority-sorted list of pickup locations.
"""

from __future__ import annotations

from database_client import get_all_users_for_pickup_today, UserProfile
from maps_service import geocode_address
from models import Coordinates, PickupLocation


def _compute_priority(profile: UserProfile) -> tuple[int, float]:
    """
    Derive a priority rank and latest weight from a user profile.

    Priority 1 = highest (heaviest recent weight first).  Ties are broken
    alphabetically by user_id for determinism.

    Returns (priority, latest_weight).  Priority is assigned *after* sorting
    in ``get_pickup_locations_today``.
    """
    if profile.records:
        latest_weight = profile.records[-1].weight
    else:
        latest_weight = 0.0
    return (0, latest_weight)  # priority filled in later


async def get_pickup_locations_today() -> list[PickupLocation]:
    """
    Build the full list of pickup locations for today.

    Steps
    ─────
    1. Query the database for all users where ``should_pick_up_today`` is True.
    2. Geocode each user's address.
    3. Sort by descending weight (heaviest first) and assign priority numbers.
    """
    eligible: list[UserProfile] = get_all_users_for_pickup_today()

    # Attach latest weight and geocode in parallel-ish (async)
    enriched: list[tuple[UserProfile, Coordinates, float]] = []
    for profile in eligible:
        coords = await geocode_address(profile.address)
        latest_weight = profile.records[-1].weight if profile.records else 0.0
        enriched.append((profile, coords, latest_weight))

    # Sort by weight descending → heaviest gets priority 1
    enriched.sort(key=lambda t: t[2], reverse=True)

    locations: list[PickupLocation] = []
    for rank, (profile, coords, weight) in enumerate(enriched, start=1):
        locations.append(
            PickupLocation(
                user_id=profile.user_id,
                address=profile.address,
                coordinates=coords,
                priority=rank,
                latest_weight=round(weight, 2),
            )
        )

    return locations
