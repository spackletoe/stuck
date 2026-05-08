# Stuck Implementation Checklist

This document turns the v1 spec and technical architecture into a practical build plan.

## Goals

- build a clean Home Assistant custom integration foundation
- validate the object registry and timer model early
- expose useful entities before polishing the mobile UX
- keep v1 focused on scan flow, object state, and reset behavior

---

## Suggested Build Order

Build in this order:

1. repo scaffold
2. data models and storage
3. object registry operations
4. derived timing/status logic
5. entity platforms
6. services
7. tag scan routing
8. unknown tag onboarding flow
9. known tag detail/reset flow
10. dashboard support and polish
11. tests and docs cleanup

This order gives you something testable quickly and avoids getting stuck on mobile UX before the core model works.

---

## Milestone 0: Repo Bootstrap

### Deliverable

A valid Home Assistant custom integration skeleton with a clear place for all major components.

### Tasks

- [ ] create repo
- [ ] create `custom_components/stuck/`
- [ ] add `manifest.json`
- [ ] add `__init__.py`
- [ ] add `const.py`
- [ ] add `strings.json`
- [ ] add `translations/en.json`
- [ ] add `.gitignore`
- [ ] add `README.md`
- [ ] add license
- [ ] add basic project metadata and versioning plan

### Suggested Initial Structure

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

### Exit Criteria

- HA can load the integration skeleton without crashing
- repo structure feels stable enough to build into

---

## Milestone 1: Data Models and Storage

### Deliverable

Persistent storage for tracked objects, pending tags, and integration settings.

### Tasks

- [ ] define `TrackedObject` model
- [ ] define `PendingTag` model
- [ ] define storage schema version
- [ ] implement storage load/save helpers
- [ ] implement schema migration placeholder
- [ ] persist settings block
- [ ] validate timestamp serialization format
- [ ] validate uniqueness behavior for `tag_id`

### Recommended Decisions

- store timestamps in UTC ISO 8601
- key tracked objects by internal object id
- key pending tags by raw tag id
- keep derived values computed, not stored

### Exit Criteria

- objects can be created, loaded, updated, and deleted in storage
- pending tags can be created, updated, and deleted in storage
- restart/load behavior is reliable

---

## Milestone 2: Registry and Core Operations

### Deliverable

A working in-memory registry and CRUD layer on top of storage.

### Tasks

- [ ] implement object create operation
- [ ] implement object update operation
- [ ] implement object delete operation
- [ ] implement object deactivate/reactivate operation
- [ ] implement pending tag create/update operation
- [ ] implement pending tag dismiss/remove operation
- [ ] implement lookup by `object_id`
- [ ] implement lookup by `tag_id`
- [ ] add validation errors for duplicate tag assignment

### Recommended APIs

- `create_object(...)`
- `update_object(...)`
- `delete_object(object_id)`
- `reset_object(object_id)`
- `upsert_pending_tag(tag_id, context)`
- `dismiss_pending_tag(tag_id)`
- `get_object_by_tag(tag_id)`

### Exit Criteria

- all basic CRUD operations work from Python without HA entity layer yet
- duplicate tag assignment is blocked cleanly

---

## Milestone 3: Timing and Status Logic

### Deliverable

A reliable calculation layer for due dates and object status.

### Tasks

- [ ] implement interval parsing for day/week/month
- [ ] implement `next_due_at`
- [ ] implement `elapsed_duration`
- [ ] implement `remaining_duration`
- [ ] implement `overdue_duration`
- [ ] implement `is_overdue`
- [ ] implement `status`
- [ ] implement due-soon threshold logic
- [ ] handle month addition safely
- [ ] test timezone safety

### Edge Cases to Test

- [ ] exactly due right now
- [ ] long overdue object
- [ ] interval changed after object creation
- [ ] month-end rollover behavior
- [ ] inactive object behavior

### Exit Criteria

- timing math is consistent and predictable
- status buckets are stable

---

## Milestone 4: Entity Layer

### Deliverable

Tracked objects appear in Home Assistant as entities.

### Tasks

- [ ] implement coordinator or central state manager
- [ ] implement per-object sensor entities
- [ ] implement per-object binary sensor entities
- [ ] implement per-object reset button entities
- [ ] implement global summary sensors
- [ ] define entity naming conventions
- [ ] define unique ids
- [ ] handle entity removal on object delete
- [ ] handle entity updates after object reset/update

### Per-Object Entities

- [ ] `sensor.<slug>_status`
- [ ] `sensor.<slug>_next_due`
- [ ] `sensor.<slug>_time_remaining`
- [ ] `sensor.<slug>_time_elapsed`
- [ ] `binary_sensor.<slug>_overdue`
- [ ] `button.<slug>_reset`

### Global Entities

- [ ] tracked object count
- [ ] overdue count
- [ ] due soon count
- [ ] pending tag count

### Exit Criteria

- objects show up in HA as entities
- deleting an object removes its entities cleanly
- resetting/updating objects refreshes entity state immediately

---

## Milestone 5: Services

### Deliverable

Custom services for core integration operations.

### Tasks

- [ ] register `stuck.reset_object`
- [ ] register `stuck.create_object`
- [ ] register `stuck.update_object`
- [ ] register `stuck.delete_object`
- [ ] register `stuck.dismiss_pending_tag`
- [ ] define service schemas
- [ ] validate service inputs
- [ ] return useful errors for invalid calls

### Nice to Have

- [ ] `stuck.reassign_tag`
- [ ] `stuck.activate_object`
- [ ] `stuck.deactivate_object`

### Exit Criteria

- all core operations can be driven through HA services
- service calls update entities reliably

---

## Milestone 6: Tag Scan Routing

### Deliverable

The integration responds to NFC tag scans and routes them as known vs unknown.

### Tasks

- [ ] identify the HA event source for tag scans
- [ ] subscribe to tag scan events
- [ ] normalize incoming tag ids if necessary
- [ ] route scans through `tag_router.py`
- [ ] resolve known tags to tracked objects
- [ ] route unknown tags to pending-tag path
- [ ] prevent duplicate pending entries on repeated scans
- [ ] capture available scan context like source device if possible

### Known Scan Behavior

- [ ] look up object by tag id
- [ ] launch detail path or equivalent notification/action
- [ ] never auto-reset timer

### Unknown Scan Behavior

- [ ] create or update pending tag
- [ ] route user to registration path
- [ ] preserve recoverability if onboarding is interrupted

### Exit Criteria

- scanning a known tag resolves correctly every time
- scanning an unknown tag creates/updates pending state correctly

---

## Milestone 7: Unknown Tag Onboarding UX

### Deliverable

A working “new tag detected” registration flow.

### Tasks

- [ ] decide the actual mobile entry mechanism
- [ ] determine whether HA supports the ideal deep-link/form path directly
- [ ] create fallback notification-based flow if needed
- [ ] build registration form/page inputs
- [ ] pre-bind the scanned `tag_id`
- [ ] create object on submit
- [ ] remove pending tag on successful creation
- [ ] support resume-later behavior

### Required Registration Inputs

- [ ] object name
- [ ] interval value
- [ ] interval unit

### Optional v1 Inputs

- [ ] icon
- [ ] notes
- [ ] category
- [ ] due-soon threshold override

### UX Requirements

- [ ] no object is created automatically from scan alone
- [ ] user always has a clear next action
- [ ] abandoned onboarding can be resumed later

### Exit Criteria

- a fresh NFC tag can be scanned and turned into a tracked object from a phone flow

---

## Milestone 8: Known Tag Detail and Reset UX

### Deliverable

A clean status view for known tags, with explicit reset action.

### Tasks

- [ ] define object detail page/panel/path
- [ ] show object name
- [ ] show last reset
- [ ] show next due
- [ ] show elapsed time
- [ ] show remaining or overdue time
- [ ] add explicit reset action
- [ ] add link to full dashboard
- [ ] optionally add edit action

### UX Rules

- [ ] scan does not reset automatically
- [ ] reset must be one obvious tap
- [ ] status should be understandable immediately

### Exit Criteria

- scanning a known tag reliably gives useful status and reset access

---

## Milestone 9: Dashboard Support

### Deliverable

A usable dashboard surface for all tracked objects.

### Tasks

- [ ] verify entities support dashboard composition cleanly
- [ ] design recommended dashboard sections
- [ ] document example dashboard layout
- [ ] expose enough summary entities to power badges/sections
- [ ] expose pending tags count for admin visibility
- [ ] decide whether to ship example dashboard YAML or markdown examples

### Recommended Dashboard Sections

- [ ] overdue
- [ ] due soon
- [ ] all tracked objects
- [ ] pending/unassigned tags

### Exit Criteria

- users can build a useful dashboard with the provided entities and docs

---

## Milestone 10: Diagnostics and Repairs

### Deliverable

Basic observability and easier supportability.

### Tasks

- [ ] add diagnostics output
- [ ] include storage schema version
- [ ] include counts and sanitized registry state
- [ ] include pending tag count
- [ ] omit sensitive note content where possible
- [ ] consider repair issues for corrupted/duplicate state later

### Exit Criteria

- enough diagnostics exist to debug common user issues

---

## Milestone 11: Testing

### Deliverable

Reasonable confidence that the integration behaves correctly.

### Unit Tests

- [ ] object creation
- [ ] object update
- [ ] object deletion
- [ ] object reset
- [ ] duplicate tag rejection
- [ ] pending tag upsert behavior
- [ ] timing math
- [ ] overdue transitions
- [ ] due-soon transitions
- [ ] month interval behavior

### Integration Tests

- [ ] startup and storage load
- [ ] entity creation on object create
- [ ] entity cleanup on object delete
- [ ] service calls update state
- [ ] known tag routing
- [ ] unknown tag routing

### Manual Tests

- [ ] scan unknown tag from actual phone
- [ ] abandon onboarding and resume later
- [ ] scan known tag from actual phone
- [ ] reset via mobile flow
- [ ] confirm dashboard usefulness on mobile

### Exit Criteria

- core v1 flow works on a real phone, not just in test scaffolding

---

## MVP Cut Line

If you need to cut scope, keep these for MVP:

- [ ] storage-backed tracked objects
- [ ] storage-backed pending tags
- [ ] object timing/status logic
- [ ] sensors/binary sensor/button entities
- [ ] core services
- [ ] known/unknown tag routing
- [ ] unknown tag registration flow
- [ ] known tag status + reset flow

Cut or defer these first if needed:

- [ ] category support
- [ ] custom icons beyond basic support
- [ ] per-object due-soon override
- [ ] tag reassignment
- [ ] built-in notification engine
- [ ] fancy dashboard generation
- [ ] repairs framework

---

## Suggested Post-v1 Backlog

### v1.1

- [ ] tag reassignment
- [ ] archive/inactive filters
- [ ] better dashboard examples
- [ ] optional built-in daily reminder check

### v1.2

- [ ] maintenance history log
- [ ] first stuck / first tracked display
- [ ] average cycle / cadence metrics
- [ ] richer object detail view
- [ ] notification customization
- [ ] pending tag expiration rules

### v2

- [ ] multiple tracks per object
- [ ] support both reminder tracks and elapsed-only tracks
- [ ] analytics/history views
- [ ] QR support
- [ ] import/export
- [ ] autogenerated dashboards
- [ ] advanced recurring rules

## Scope Boundary Reminder

Keep Stuck focused on tagged-object timelines.

Good future additions:
- track history
- cadence metrics
- first tracked dates
- multiple tracks per object

Out-of-scope drift to resist:
- inventory quantities
- storage/bin tracking
- purchase/vendor/product catalogs
- serial-number / asset-database style metadata

---

## Recommended First Coding Session

If you want the best first session, do only this:

- [ ] scaffold repo
- [ ] implement models
- [ ] implement storage manager
- [ ] implement create/update/delete/reset object logic
- [ ] write unit tests for storage + registry

Do not start with dashboard or mobile flow first.

Get the registry right first. Everything else hangs off that.

---

## Practical Definition of Done for v1

Stuck v1 is done when a user can:

1. install the integration
2. scan a new NFC tag
3. create an object from their phone
4. see that object in Home Assistant entities and dashboard
5. scan the same tag later and see status
6. reset the timer explicitly
7. recover gracefully from interrupted onboarding

If those seven things work cleanly, you’ve got a real v1.
