"""
maps_service.py – Google Maps Platform integration.

Wraps three APIs:
  1. Geocoding          – address → (lat, lng)
  2. Directions         – origin + destination → route info
  3. Reverse Geocoding  – (lat, lng) → address string

When `settings.mock_maps` is True (the default for local dev), every
function returns deterministic fake data so you can develop and test
without a real API key.

How to enable live mode
───────────────────────
1. Create a Google Maps API key at https://console.cloud.google.com
2. Enable "Geocoding API" and "Directions API" in your GCP project
3. Set the following in your .env file:
       GOOGLE_MAPS_API_KEY=<your-key>
       MOCK_MAPS=false
"""

from __future__ import annotations

import httpx

from config import settings
from models import Coordinates, RouteInfo, RouteStep

_BASE = "https://maps.googleapis.com/maps/api"


# ═══════════════════════════════════════════════════════════════════════════
#  Geocoding:  address string → Coordinates
# ═══════════════════════════════════════════════════════════════════════════

async def geocode_address(address: str) -> Coordinates:
    """Convert a street address into geographic coordinates."""
    if settings.mock_maps:
        return _mock_geocode(address)

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            f"{_BASE}/geocode/json",
            params={"address": address, "key": settings.google_maps_api_key},
        )
        resp.raise_for_status()
        data = resp.json()

    if data.get("status") != "OK" or not data.get("results"):
        raise ValueError(f"Geocoding failed for '{address}': {data.get('status')}")

    loc = data["results"][0]["geometry"]["location"]
    return Coordinates(lat=loc["lat"], lng=loc["lng"])


# ═══════════════════════════════════════════════════════════════════════════
#  Reverse Geocoding:  (lat, lng) → address string
# ═══════════════════════════════════════════════════════════════════════════

async def reverse_geocode(lat: float, lng: float) -> str:
    """Convert coordinates back into a human-readable address."""
    if settings.mock_maps:
        return f"Mock Address at ({lat:.4f}, {lng:.4f})"

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            f"{_BASE}/geocode/json",
            params={"latlng": f"{lat},{lng}", "key": settings.google_maps_api_key},
        )
        resp.raise_for_status()
        data = resp.json()

    if data.get("status") != "OK" or not data.get("results"):
        return f"Unknown location ({lat}, {lng})"

    return data["results"][0]["formatted_address"]


# ═══════════════════════════════════════════════════════════════════════════
#  Directions:  origin + destination → RouteInfo
# ═══════════════════════════════════════════════════════════════════════════

async def get_directions(
    origin: Coordinates,
    destination: Coordinates,
    weight: float = 0.0,
    waypoint_coords: list[Coordinates] | None = None,
) -> RouteInfo:
    """
    Compute an optimised route from *origin* to *destination*.

    Parameters
    ----------
    origin, destination : Coordinates
        Start and end points.
    weight : float
        The user's latest weight value.  Currently used as a simple
        heuristic: heavier loads prefer shorter-distance routes
        (``alternatives=true`` when weight > threshold).  This hook is
        intentionally kept simple so you can plug in a real vehicle-
        capacity model later.
    waypoint_coords : list[Coordinates] | None
        Optional intermediate stops.  The Directions API will optimise
        their order when ``optimize:true`` is prepended.
    """
    if settings.mock_maps:
        return await _mock_directions(origin, destination, weight)

    params: dict[str, str] = {
        "origin": f"{origin.lat},{origin.lng}",
        "destination": f"{destination.lat},{destination.lng}",
        "key": settings.google_maps_api_key,
        "mode": "driving",
        "alternatives": "true" if weight > settings.pickup_weight_threshold else "false",
    }

    if waypoint_coords:
        wp_str = "|".join(f"{c.lat},{c.lng}" for c in waypoint_coords)
        params["waypoints"] = f"optimize:true|{wp_str}"

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(f"{_BASE}/directions/json", params=params)
        resp.raise_for_status()
        data = resp.json()

    if data.get("status") != "OK" or not data.get("routes"):
        raise ValueError(f"Directions API error: {data.get('status')}")

    route = data["routes"][0]
    leg = route["legs"][0]

    steps = [
        RouteStep(
            instruction=s.get("html_instructions", ""),
            distance=s["distance"]["text"],
            duration=s["duration"]["text"],
        )
        for s in leg.get("steps", [])
    ]

    # Reverse-geocode waypoints for human-readable display
    waypoints_addr: list[str] = []
    if waypoint_coords:
        for c in waypoint_coords:
            addr = await reverse_geocode(c.lat, c.lng)
            waypoints_addr.append(addr)

    return RouteInfo(
        distance=leg["distance"]["text"],
        duration=leg["duration"]["text"],
        steps=steps,
        waypoints=waypoints_addr,
    )


# ═══════════════════════════════════════════════════════════════════════════
#  Mock implementations  (used when MOCK_MAPS=true)
# ═══════════════════════════════════════════════════════════════════════════

def _mock_geocode(address: str) -> Coordinates:
    """Deterministic fake geocode – produces coords based on hash of address."""
    h = hash(address) % 10_000
    lat = 18.0 + (h % 100) / 100.0   # roughly around Mumbai latitude
    lng = 72.0 + (h // 100) / 100.0
    return Coordinates(lat=round(lat, 6), lng=round(lng, 6))


async def _mock_directions(
    origin: Coordinates,
    destination: Coordinates,
    weight: float,
) -> RouteInfo:
    """Generate plausible fake route data."""
    # Fake distance scales with weight (heavier → prefer shorter route)
    base_km = 12.4
    factor = max(0.5, 1.0 - (weight - 50) * 0.01) if weight > 50 else 1.0
    km = round(base_km * factor, 1)
    mins = int(km * 2.5)

    steps = [
        RouteStep(instruction="Head north on Main St", distance="0.5 km", duration="2 mins"),
        RouteStep(instruction="Turn right onto Park Ave", distance=f"{km - 1.0} km", duration=f"{mins - 5} mins"),
        RouteStep(instruction="Arrive at destination", distance="0.5 km", duration="3 mins"),
    ]

    origin_addr = await reverse_geocode(origin.lat, origin.lng) if settings.mock_maps else ""
    dest_addr = await reverse_geocode(destination.lat, destination.lng) if settings.mock_maps else ""

    return RouteInfo(
        distance=f"{km} km",
        duration=f"{mins} mins",
        steps=steps,
        waypoints=[origin_addr, dest_addr],
    )
