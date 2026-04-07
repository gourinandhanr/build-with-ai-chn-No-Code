"""
main.py – FastAPI application entry-point.

Endpoints
─────────
  POST /optimize-pickup         Single-user pickup decision + route
  GET  /pickup-locations-today   All pickups scheduled for today
  GET  /health                   Liveness probe

Start locally:
    uvicorn main:app --reload --port 8000

Interactive docs at http://localhost:8000/docs
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

from config import settings
from database_client import get_user_profile, should_pick_up_today, add_user, add_daily_weight
from maps_service import geocode_address, get_directions
from models import (
    Coordinates,
    OptimizePickupRequest,
    OptimizePickupResponse,
    PickupLocation,
    UserCreate,
    WeightUpdate,
)
from pickup_locations import get_pickup_locations_today

# ── App initialisation ──────────────────────────────────────────────────────

app = FastAPI(
    title="Pickup Optimizer API",
    description=(
        "Backend service for pickup-decision and route optimization. "
        "Uses historic weight profiles and Google Maps APIs."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health check ─────────────────────────────────────────────────────────────

@app.get("/health", tags=["ops"])
async def health():
    return {
        "status": "healthy",
        "mock_maps": settings.mock_maps,
    }


# ── POST /optimize-pickup ───────────────────────────────────────────────────

@app.post(
    "/optimize-pickup",
    response_model=OptimizePickupResponse,
    tags=["pickup"],
    summary="Single-user pickup optimization",
)
async def optimize_pickup(body: OptimizePickupRequest):
    """
    For a given user, decide whether they should be picked up today.
    If yes, geocode their address and compute an optimised route.
    """
    # 1. Validate user exists
    profile = get_user_profile(body.user_id)
    if profile is None:
        raise HTTPException(status_code=404, detail=f"User {body.user_id!r} not found")

    # 2. Evaluate pickup decision
    pickup = should_pick_up_today(body.user_id)

    if not pickup:
        return OptimizePickupResponse(
            user_id=body.user_id,
            should_pick_up_today=False,
            message="No pickup needed today based on current profile.",
        )

    # 3. Geocode the user's address
    coords = await geocode_address(body.address)

    # 4. Compute route (depot → user address)
    #    Using a fixed depot for demo; in production this would come from
    #    fleet management or a config.
    depot = Coordinates(lat=19.076, lng=72.8777)  # Mumbai city centre
    latest_weight = profile.records[-1].weight if profile.records else 0.0
    route = await get_directions(
        origin=depot,
        destination=coords,
        weight=latest_weight,
    )

    return OptimizePickupResponse(
        user_id=body.user_id,
        should_pick_up_today=True,
        pickup_address=body.address,
        pickup_coordinates=coords,
        route=route,
        message="Pickup scheduled. Route optimised for current load.",
    )


# ── GET /pickup-locations-today ──────────────────────────────────────────────

@app.get(
    "/pickup-locations-today",
    response_model=list[PickupLocation],
    tags=["pickup"],
    summary="All pickup locations for today",
)
async def pickup_locations_today():
    """
    Return every user whose profile warrants a pickup today, with
    geocoded coordinates and priority ranking.
    """
    locations = await get_pickup_locations_today()
    if not locations:
        return []
    return locations


# ── Dashboard Additions ──────────────────────────────────────────────────────

@app.post(
    "/add-user",
    tags=["dashboard"],
    summary="Create a new user profile",
)
async def api_add_user(user: UserCreate):
    """Insert a new user ID and their address into the system."""
    success = add_user(user.user_id, user.address)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to add user to database.")
    return {"status": "success", "user_id": user.user_id}


@app.post(
    "/add-weight",
    tags=["dashboard"],
    summary="Add daily weight record",
)
async def api_add_weight(body: WeightUpdate):
    """Insert a physical weight recording for a specific date for a user."""
    # Note: BQ streaming might delay this appearing in routes slightly
    success = add_daily_weight(body.user_id, body.date, body.weight)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to add weight record.")
    return {"status": "success", "user_id": body.user_id, "date": body.date}


# ── Static Frontend ─────────────────────────────────────────────────────────

# Mount the static directory to serve the frontend dashboard
import os
os.makedirs("static", exist_ok=True)
app.mount("/dashboard", StaticFiles(directory="static", html=True), name="static")

@app.get("/")
def redirect_to_dashboard():
    """Redirect root to the dashboard."""
    return RedirectResponse(url="/dashboard/index.html")
