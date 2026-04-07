"""
database_client.py – Data access layer & pickup-decision engine using BigQuery.

Pickup-decision rules
─────────────────────
The `should_pick_up_today` function applies a chain of rules against the
user's historical weight records. Each rule is a simple callable.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import NamedTuple

from google.cloud import bigquery
from google.api_core.exceptions import NotFound
from google.auth.exceptions import DefaultCredentialsError

from config import settings

# ── Data structures ──────────────────────────────────────────────────────────

class WeightRecord(NamedTuple):
    date: date
    weight: float


class UserProfile(NamedTuple):
    user_id: str
    address: str
    records: list[WeightRecord]


# ── BigQuery setup ───────────────────────────────────────────────────────────

_client: bigquery.Client | None = None

def _get_client() -> bigquery.Client:
    """Return the singleton BigQuery client."""
    global _client
    if _client is None:
        try:
            _client = bigquery.Client(project=settings.gcp_project)
            if settings.gcp_project == "mock-project-for-local-dev":
                print("WARNING: Using mock project for BigQuery. This will fail without ADC.")
        except DefaultCredentialsError:
            print("WARNING: GCP details missing or ADC not found. Mocking _client as None.")
    return _client


def initialize_and_seed_database() -> None:
    """Creates the dataset, tables, and inserts sample profiles.
    You should call this script as a one-off in the cloud project.
    """
    client = _get_client()
    if client is None:
        return
        
    dataset_id = f"{settings.gcp_project}.{settings.bigquery_dataset}"
    dataset = bigquery.Dataset(dataset_id)
    dataset.location = "US"
    try:
        dataset = client.create_dataset(dataset, exists_ok=True)
    except Exception as e:
        print(f"Skipping dataset creation: {e}")

    # Create users table
    users_table_id = f"{dataset_id}.users"
    users_schema = [
        bigquery.SchemaField("user_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("address", "STRING", mode="REQUIRED"),
    ]
    users_table = bigquery.Table(users_table_id, schema=users_schema)
    client.create_table(users_table, exists_ok=True)

    # Create weight_history table
    history_table_id = f"{dataset_id}.weight_history"
    history_schema = [
        bigquery.SchemaField("user_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("date", "DATE", mode="REQUIRED"),
        bigquery.SchemaField("weight", "FLOAT", mode="REQUIRED"),
    ]
    history_table = bigquery.Table(history_table_id, schema=history_schema)
    client.create_table(history_table, exists_ok=True)

    # Seed data
    today = date.today()

    users_data = [
        {"user_id": "U001", "address": "123 Main Street, Mumbai"},
        {"user_id": "U002", "address": "456 Park Avenue, Delhi"},
        {"user_id": "U003", "address": "789 Lake Road, Bangalore"},
        {"user_id": "U004", "address": "321 Hill View, Chennai"},
        {"user_id": "U005", "address": "654 River Side, Pune"},
        {"user_id": "U006", "address": "111 Garden Lane, Hyderabad"},
    ]
    
    # Simple check if users exist to avoid duplicate seed
    query = f"SELECT count(*) as cnt FROM `{users_table_id}`"
    try:
        results = list(client.query_and_wait(query))
        if results and results[0].cnt == 0:
            client.insert_rows_json(users_table_id, users_data)
            
            histories = []
            for i in range(30):
                d = (today - timedelta(days=29 - i)).isoformat()
                histories.append({"user_id": "U001", "date": d, "weight": 48.0 + i * 0.5})
                histories.append({"user_id": "U002", "date": d, "weight": 30.0 + (i % 3) * 0.2})
                histories.append({"user_id": "U003", "date": d, "weight": 40.0 + (0 if i < 25 else (i - 25) * 4)})
                histories.append({"user_id": "U004", "date": d, "weight": 55.0 - i * 0.3})

            for i in range(10):
                d = (today - timedelta(days=30 + i)).isoformat()
                histories.append({"user_id": "U005", "date": d, "weight": 60.0})

            for i in range(20):
                d = (today - timedelta(days=19 - i)).isoformat()
                histories.append({"user_id": "U006", "date": d, "weight": 42.0 + (i % 2)})

            # Batch insert
            chunk_size = 100
            for i in range(0, len(histories), chunk_size):
                client.insert_rows_json(history_table_id, histories[i:i + chunk_size])
    except NotFound:
        pass


# ── Public query helpers ─────────────────────────────────────────────────────

def get_user_profile(user_id: str) -> UserProfile | None:
    """Fetch a single user's profile and weight history from BigQuery."""
    client = _get_client()
    if client is None:
        return None
        
    dataset_id = f"{settings.gcp_project}.{settings.bigquery_dataset}"

    # Get User
    query_user = f"SELECT user_id, address FROM `{dataset_id}.users` WHERE user_id = @user_id"
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("user_id", "STRING", user_id)]
    )
    user_rows = list(client.query_and_wait(query_user, job_config=job_config))
    
    if not user_rows:
        return None
        
    row = user_rows[0]
    
    # Get History
    query_history = f"SELECT date, weight FROM `{dataset_id}.weight_history` WHERE user_id = @user_id ORDER BY date"
    history_rows = list(client.query_and_wait(query_history, job_config=job_config))
    
    records = []
    for hr in history_rows:
        # BQ date can be a datetime.date object directly
        d = hr.date if isinstance(hr.date, date) else datetime.fromisoformat(str(hr.date)).date()
        records.append(WeightRecord(date=d, weight=hr.weight))
        
    return UserProfile(user_id=row.user_id, address=row.address, records=records)


def get_all_user_profiles() -> list[UserProfile]:
    """Return every user profile in the database."""
    client = _get_client()
    if client is None:
        return []

    dataset_id = f"{settings.gcp_project}.{settings.bigquery_dataset}"
    
    # For a real application, doing a JOIN and grouping in BigQuery would be faster
    # But to match the previous structure and abstraction:
    query = f"SELECT user_id FROM `{dataset_id}.users` ORDER BY user_id"
    user_rows = client.query_and_wait(query)
    
    profiles: list[UserProfile] = []
    for r in user_rows:
        profile = get_user_profile(r.user_id)
        if profile is not None:
            profiles.append(profile)
    return profiles


# ── Pickup-decision rules ───────────────────────────────────────────────────
#
# Each rule is a function  (records, settings) → bool | None
#   • True   → definitely pick up
#   • False  → definitely skip
#   • None   → rule is inconclusive, continue to next rule
#
# The chain short-circuits on the first decisive result.  Add or reorder
# rules below to change behaviour; a TimesFM model call would slot in
# as just another rule.
# ─────────────────────────────────────────────────────────────────────────────

def _rule_high_recent_weight(records: list[WeightRecord], _s=settings) -> bool | None:
    """Pick up if the average weight over the look-back window exceeds the threshold."""
    if not records:
        return None
    cutoff = date.today() - timedelta(days=_s.pickup_trend_days)
    recent = [r.weight for r in records if r.date >= cutoff]
    if not recent:
        return None
    avg = sum(recent) / len(recent)
    if avg >= _s.pickup_weight_threshold:
        return True
    return None


def _rule_increasing_trend(records: list[WeightRecord], _s=settings) -> bool | None:
    """Pick up if the weight trend over the look-back window is increasing."""
    if not records:
        return None
    cutoff = date.today() - timedelta(days=_s.pickup_trend_days)
    recent = [r for r in records if r.date >= cutoff]
    if len(recent) < 3:
        return None

    # Simple linear-regression slope via least squares
    n = len(recent)
    x_vals = list(range(n))
    y_vals = [r.weight for r in recent]
    x_mean = sum(x_vals) / n
    y_mean = sum(y_vals) / n
    num = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_vals, y_vals))
    den = sum((x - x_mean) ** 2 for x in x_vals)
    if den == 0:
        return None
    slope = num / den
    if slope > 0.1:  # positive trend (> 0.1 kg/day)
        return True
    return None


def _rule_overdue_pickup(records: list[WeightRecord], _s=settings) -> bool | None:
    """Force pickup if there is no record within the max interval."""
    if not records:
        return True  # no data at all → overdue
    most_recent = max(r.date for r in records)
    days_since = (date.today() - most_recent).days
    if days_since > _s.pickup_max_interval_days:
        return True
    return None


# Ordered rule chain – evaluated top to bottom
_RULES = [
    _rule_high_recent_weight,
    _rule_increasing_trend,
    _rule_overdue_pickup,
]


def should_pick_up_today(user_id: str) -> bool:
    """
    Evaluate the pickup-decision rule chain for *user_id*.

    Returns True if at least one rule fires positively, False otherwise.
    """
    profile = get_user_profile(user_id)
    if profile is None:
        return False

    for rule in _RULES:
        result = rule(profile.records)
        if result is True:
            return True
        if result is False:
            return False

    # No rule was decisive → default to no pickup
    return False


def get_all_users_for_pickup_today() -> list[UserProfile]:
    """Return profiles of every user who should be picked up today."""
    return [p for p in get_all_user_profiles() if should_pick_up_today(p.user_id)]


# ── Dashboard Write Helpers ──────────────────────────────────────────────────

def add_user(user_id: str, address: str) -> bool:
    """Insert a new user into BigQuery."""
    client = _get_client()
    if client is None:
        return False
    dataset_id = f"{settings.gcp_project}.{settings.bigquery_dataset}"
    table_id = f"{dataset_id}.users"
    errors = client.insert_rows_json(table_id, [{"user_id": user_id, "address": address}])
    return not errors


def add_daily_weight(user_id: str, record_date: date, weight: float) -> bool:
    """Insert a daily weight log for a user."""
    client = _get_client()
    if client is None:
        return False
    dataset_id = f"{settings.gcp_project}.{settings.bigquery_dataset}"
    table_id = f"{dataset_id}.weight_history"
    errors = client.insert_rows_json(
        table_id,
        [{"user_id": user_id, "date": record_date.isoformat(), "weight": weight}]
    )
    return not errors
