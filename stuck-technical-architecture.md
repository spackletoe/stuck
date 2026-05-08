# Stuck Technical Architecture

## Overview

This document describes the technical architecture for **Stuck**, a Home Assistant custom integration for NFC-bound object lifecycle tracking.

The integration should:

- detect unknown and known NFC tag scans
- maintain an internal registry of tracked objects
- maintain a registry of pending/unassigned tags
- expose Home Assistant entities for object state
- support mobile-friendly registration and object detail flows
- provide a clean foundation for dashboards and automations

---

## Design Principles

### 1. Object-First Model

The system models **physical objects**, not chores or tasks.

A tag is bound to an object, and the object owns the recurring interval.

This should evolve toward the tag identifying the object itself, while the object may eventually own multiple timeline tracks.

### 2. Storage-Backed Registry

Do not use a pile of helpers as the source of truth.

Persist tracked objects and pending tags in integration-managed storage.

### 3. Explicit Actions

A known tag scan should never auto-reset a timer.

Resetting must be a deliberate user action.

### 4. Resilient Unknown Tag Flow

Unknown scans must not be lossy.

If registration is interrupted, the pending tag remains recoverable.

### 5. HA-Native Surfaces

Expose meaningful entities so users can build dashboards, automations, and notifications naturally.

### 6. Scope Discipline

Stuck should remain a tagged-object timeline tracker, not become a general inventory platform.

That means:
- lightweight object metadata is good
- timeline history and cadence metrics are good
- product catalog / stock-management fields are out of scope

---

## High-Level Architecture

Core components:

- **Config Entry**
- **Storage Manager**
- **Tag Scan Resolver**
- **Tracked Object Registry**
- **Pending Tag Registry**
- **Entity Platform Layer**
- **Service Layer**
- **Dashboard / Navigation Support**
- **Optional Notification Hook Points**

---

## Integration Structure

Suggested custom integration structure:

```text
custom_components/stuck/
  __init__.py
  manifest.json
  const.py
  config_flow.py
  coordinator.py
  storage.py
  models.py
  tag_router.py
  services.py
  sensor.py
  binary_sensor.py
  button.py
  diagnostics.py
  strings.json
  translations/
    en.json
```

### Optional Later Files

```text
  entity.py
  helpers.py
  repair.py
  websocket_api.py
```

---

## Data Model

### Tracked Object Model

Suggested shape:

```python
TrackedObject:
    id: str
    name: str
    tag_id: str
    interval_value: int
    interval_unit: str   # day | week | month
    created_at: datetime
    last_reset_at: datetime
    notes: str | None
    icon: str | None
    category: str | None
    due_soon_threshold_days: int | None
    active: bool
```

This is the v1 single-track shape.
It is intentionally simple so the object registry and scan flow can stabilize first.

### Future Model Direction

A likely future model is:

```python
TrackedObject:
    id: str
    name: str
    tag_id: str
    created_at: datetime   # first stuck / first tracked
    notes: str | None
    icon: str | None
    category: str | None
    active: bool

TrackedObjectTrack:
    id: str
    object_id: str
    name: str
    track_type: str   # reminder | elapsed
    interval_value: int | None
    interval_unit: str | None
    created_at: datetime
    last_reset_at: datetime
    active: bool
```

This keeps the tag bound to the object rather than to a specific timer.

### Derived Fields

These should be computed, not stored redundantly unless caching becomes necessary.

```python
elapsed_duration
next_due_at
remaining_duration
is_overdue
overdue_duration
status
```

For future history-aware tracks, additional derived values may include:
- first_stuck_at display
- average cycle length
- average early/late timing
- cadence consistency metrics

### Pending Tag Model

```python
PendingTag:
    tag_id: str
    first_seen_at: datetime
    last_seen_at: datetime
    scan_count: int
    source_device: str | None
```

### Metadata Boundary

Allowed object metadata should stay intentionally lightweight:
- name
- notes
- icon/category
- first tracked date

Avoid broad product-record fields such as:
- serial number
- SKU/model catalog data
- purchase/vendor/price data
- quantity or location fields

---

## Persistence Strategy

Use Home Assistant’s storage helper.

### Storage Contents

Suggested persisted structure:

```json
{
  "version": 1,
  "objects": {
    "object_id_1": {
      "id": "object_id_1",
      "name": "HVAC Filter",
      "tag_id": "04AABBCCDD",
      "interval_value": 90,
      "interval_unit": "day",
      "created_at": "2026-05-06T08:00:00Z",
      "last_reset_at": "2026-05-06T08:00:00Z",
      "notes": "",
      "icon": "mdi:air-filter",
      "category": "Filters",
      "due_soon_threshold_days": 3,
      "active": true
    }
  },
  "pending_tags": {
    "04FFEEDD11": {
      "tag_id": "04FFEEDD11",
      "first_seen_at": "2026-05-06T08:05:00Z",
      "last_seen_at": "2026-05-06T08:05:00Z",
      "scan_count": 1,
      "source_device": "pixel_9"
    }
  },
  "settings": {
    "default_due_soon_threshold_days": 3,
    "show_inactive_objects": false
  }
}
```

### Storage Rules

- `objects` keyed by internal object id
- `pending_tags` keyed by raw tag id
- tag id must be unique among tracked objects
- writes should be debounced where practical
- migration path should exist from future schema versions

---

## Config Flow

### Initial Setup

v1 config flow should be minimal.

Suggested options:

- default due-soon threshold
- whether inactive objects appear in dashboard views
- optional pending tag expiration behavior

### Options Flow

Provide editing for global integration settings.

Do not require users to define objects in config flow. Object creation should happen from scan-driven onboarding.

---

## Tag Scan Handling

### Source of Tag Events

Home Assistant tag events from the mobile app / tag integration.

The integration should listen for tag scan events and resolve by `tag_id`.

### Routing Rules

#### Unknown Tag

If scanned tag id does not match any tracked object:

- create or update `PendingTag`
- trigger registration path
- expose unknown tag as recoverable state

#### Known Tag

If scanned tag id matches a tracked object:

- resolve the object
- trigger object detail/status path
- do not modify timer automatically

---

## Tag Router Responsibilities

`tag_router.py` should handle:

- normalization of tag ids if needed
- lookup in tracked objects
- lookup/update in pending tags
- dispatching follow-up actions
- avoiding duplicated onboarding state

Pseudo-flow:

```python
on_tag_scanned(tag_id, context):
    if tag_id in tracked_objects:
        return handle_known_tag(tag_id, context)

    return handle_unknown_tag(tag_id, context)
```

---

## Unknown Tag Registration Flow

### Required Behavior

When an unknown tag is scanned:

1. persist/update a pending tag record
2. initiate a user-facing registration path
3. allow registration to be resumed later

### Registration Inputs

Required:

- object name
- interval value
- interval unit

Optional:

- icon
- notes
- category
- active state
- due-soon threshold override

### Registration Result

On successful submit:

- create `TrackedObject`
- bind `tag_id`
- remove pending tag entry
- refresh entities
- update dashboard-visible state

---

## Known Tag Detail Flow

When a known tag is scanned, user should be taken to a detail/status view.

### Required Information

- object name
- last reset
- next due
- elapsed duration
- remaining time or overdue time
- status

### Required Actions

- reset timer
- open dashboard

### Optional Action

- edit object

---

## Reset Behavior

Reset is an explicit action, never automatic.

### Service-Level Behavior

A reset action should:

- update `last_reset_at` to current time
- persist storage
- refresh all relevant entities immediately

### Optional Enhancement

Support a reset timestamp override for future admin/debug use, but do not expose it in default v1 UX.

---

## Entity Platform Design

Expose only useful, high-signal entities.

### Sensor Platform

Per object sensors:

- status
- next due
- time remaining
- time elapsed

Recommended entity ids:

- `sensor.<slug>_status`
- `sensor.<slug>_next_due`
- `sensor.<slug>_time_remaining`
- `sensor.<slug>_time_elapsed`

Global sensors:

- tracked object count
- overdue count
- due soon count
- pending tag count

### Binary Sensor Platform

Per object:

- overdue state

Recommended entity id:

- `binary_sensor.<slug>_overdue`

### Button Platform

Per object:

- reset timer

Recommended entity id:

- `button.<slug>_reset`

---

## Entity Update Model

Use a coordinator or lightweight centralized registry refresh pattern.

### Coordinator Responsibilities

- load stored data
- calculate derived states
- refresh entities after writes
- expose current snapshot to entity classes

This avoids duplicated calculation logic across entities.

---

## Services

Suggested custom services:

### `stuck.reset_object`

Parameters:

- `object_id`

Behavior:

- update `last_reset_at`
- persist
- refresh entities

### `stuck.create_object`

Parameters:

- `tag_id`
- `name`
- `interval_value`
- `interval_unit`
- optional metadata

Behavior:

- validate uniqueness of `tag_id`
- create tracked object
- remove matching pending tag
- persist
- refresh entities

### `stuck.update_object`

Parameters:

- `object_id`
- editable fields

Behavior:

- validate
- update object
- persist
- refresh entities

### `stuck.delete_object`

Parameters:

- `object_id`

Behavior:

- delete object
- free tag binding
- persist
- refresh entities

### `stuck.dismiss_pending_tag`

Parameters:

- `tag_id`

Behavior:

- remove pending tag
- persist
- refresh entities

---

## Validation Rules

### Tag Rules

- one tag id may bind to only one tracked object
- repeated unknown scans should update the same pending tag, not create duplicates
- deleting an object frees the tag id

### Interval Rules

- `interval_value` must be positive integer
- `interval_unit` must be one of allowed units
- month-based due calculations must be deterministic and timezone-safe

### Object Rules

- object id is immutable after creation
- name is editable
- tag reassignment must validate uniqueness

---

## Time Calculations

All stored timestamps should be UTC.

### Recommended Practices

- persist timestamps in UTC ISO 8601
- convert for UI presentation via HA mechanisms
- compute:
  - `next_due_at = last_reset_at + interval`
  - `elapsed_duration = now - last_reset_at`
  - `remaining_duration = next_due_at - now`
  - `overdue_duration = now - next_due_at` when overdue

### Month Handling

Month intervals are the only slightly annoying case.

Use a calendar-aware month addition strategy rather than approximating month as 30 days.

---

## Dashboard Strategy

The integration should not hardcode a full dashboard, but should support dashboards cleanly.

### v1 Recommendation

Provide:

- stable entity model
- global summary sensors
- clear per-object entities

Optional later:

- autogenerated dashboard resources
- blueprint or dashboard example package

### Dashboard Sections Supported by Entities

- overdue
- due soon
- all tracked objects
- pending tags count

---

## Navigation / Deep Link Strategy

Known and unknown scans should route the user into useful mobile UI.

### Unknown Tag

Target:

- registration form or registration page

### Known Tag

Target:

- object detail/status page

### Fallback

If direct deep-link UX is limited by HA/mobile constraints:

- create notification with action buttons
- provide reliable path into dashboard or detail page

This part should be designed around what HA mobile app currently supports best.

---

## Pending Tag Recovery

Pending tags are a core resilience feature.

### Required Behavior

- pending tags survive restart
- repeated scans update `last_seen_at` and `scan_count`
- pending tags can be dismissed or completed
- pending tags should be visible somewhere in admin/setup UI

### Optional Future Behavior

- expiry after X days
- notification when pending tags linger

---

## Editing and Lifecycle Operations

### Supported in v1

- create object
- update object metadata
- reset object timer
- deactivate object
- reactivate object
- delete object

### Optional in v1 if Straightforward

- reassign tag to another NFC sticker

### Not Needed in v1

- history timeline
- merge/split object records
- multi-tag aliases

---

## Deletion Behavior

Deleting a tracked object should:

- remove it from storage
- remove related entities
- release the tag id for reuse
- leave scans of that tag as unknown in the future

Deletion should require confirmation in any UI path.

---

## Error Handling

### Unknown Tag Registered Twice

Prevent by enforcing tag uniqueness at creation.

### Interrupted Registration

Pending tag remains available for retry.

### Duplicate Scan Bursts

Debounce where practical, but preserve correctness even if multiple events arrive.

### Missing Navigation Support

Fallback to a notification-driven path.

### Invalid Stored Data

Gracefully skip broken entries where possible and surface diagnostics.

---

## Diagnostics

Provide a diagnostics surface for support/debugging.

Suggested diagnostics contents:

- object count
- pending tag count
- sanitized object registry
- scan routing status
- storage schema version

Do not expose sensitive personal note content unless necessary.

---

## Internationalization

Use `strings.json` and translations from the start.

Even if v1 only ships English text, structure it properly for HA integration conventions.

---

## Testing Strategy

### Unit Tests

Test:

- tag routing
- status calculations
- due/overdue transitions
- pending tag lifecycle
- object creation/update/delete
- uniqueness validation

### Integration Tests

Test:

- startup loads storage correctly
- entities appear/disappear correctly
- service calls update state correctly

### Manual UX Tests

Test on actual phone:

- unknown scan
- known scan
- reset flow
- abandoned registration recovery
- dashboard usefulness

---

## Suggested Milestone Order

### Milestone 1: Core Registry + Storage

- models
- storage
- create/update/delete object logic
- pending tag logic

### Milestone 2: Entity Layer

- sensors
- binary sensors
- buttons
- coordinator refresh model

### Milestone 3: Tag Routing

- listen for tag scans
- known vs unknown dispatch
- pending tag update behavior

### Milestone 4: User Flows

- registration flow
- object detail path
- reset action path

### Milestone 5: Dashboard and Polish

- global summary entities
- example dashboard
- diagnostics
- translation structure

---

## v1 Technical Success Criteria

The architecture is successful if it supports:

1. durable storage of tracked objects and pending tags
2. reliable known/unknown tag routing
3. clean entity exposure for dashboards and automation
4. explicit timer reset behavior
5. recoverable interrupted onboarding
6. mobile-friendly interaction paths
7. clean deletion and tag reuse
