"""Constants for the Stuck integration."""

from __future__ import annotations

DOMAIN = "stuck"

PLATFORMS: list[str] = ["sensor", "binary_sensor", "button"]

STORAGE_VERSION = 1
STORAGE_KEY = DOMAIN

DEFAULT_DUE_SOON_THRESHOLD_DAYS = 3
DEFAULT_SHOW_INACTIVE_OBJECTS = False

CONF_DEFAULT_DUE_SOON_THRESHOLD_DAYS = "default_due_soon_threshold_days"
CONF_SHOW_INACTIVE_OBJECTS = "show_inactive_objects"

DATA_COORDINATOR = "coordinator"
DATA_STORAGE = "storage"
DATA_TAG_ROUTER = "tag_router"

EVENT_TAG_SCANNED = "tag_scanned"
EVENT_STUCK_TAG_SCANNED = "stuck_tag_scanned"

ATTR_OBJECT_ID = "object_id"
ATTR_TAG_ID = "tag_id"
ATTR_INTERVAL_VALUE = "interval_value"
ATTR_INTERVAL_UNIT = "interval_unit"
ATTR_LAST_RESET_AT = "last_reset_at"

UNIT_DAY = "day"
UNIT_WEEK = "week"
UNIT_MONTH = "month"
VALID_INTERVAL_UNITS = {UNIT_DAY, UNIT_WEEK, UNIT_MONTH}

STATUS_HEALTHY = "healthy"
STATUS_DUE_SOON = "due_soon"
STATUS_DUE_NOW = "due_now"
STATUS_OVERDUE = "overdue"

SERVICE_CREATE_OBJECT = "create_object"
SERVICE_UPDATE_OBJECT = "update_object"
SERVICE_DELETE_OBJECT = "delete_object"
SERVICE_RESET_OBJECT = "reset_object"
SERVICE_DISMISS_PENDING_TAG = "dismiss_pending_tag"
SERVICE_CLAIM_PENDING_TAG = "claim_pending_tag"
SERVICE_CLAIM_LATEST_PENDING_TAG = "claim_latest_pending_tag"
SERVICE_CLAIM_LATEST_PENDING_TAG_FROM_HELPERS = "claim_latest_pending_tag_from_helpers"
