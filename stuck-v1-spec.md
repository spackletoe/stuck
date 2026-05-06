# Stuck v1 Specification

## Overview

**Stuck** is a Home Assistant integration for binding NFC tags to physical objects and tracking recurring time-based reminders for those objects.

A user can:

- scan a new NFC tag
- register it to a physical object from their phone
- define a recurring interval
- later scan that same tag to:
  - view current status
  - reset its timer
  - jump to the main dashboard

This is not a chore manager.  
This is object-based recurring time tracking.

---


## Product Goal

Create a Home Assistant integration that lets a user:

- scan a **new NFC tag**
- register it to a physical object from their phone
- define a reminder interval
- later scan that same tag to:
  - view current status
  - reset the timer
  - jump to the main dashboard

---

## Primary User Stories

### 1. Register a New Tagged Object

As a user, I scan a brand-new NFC tag and get a phone form where I can create a new tracked object.

#### Acceptance Criteria

- unknown tag scan is detected
- user is routed to a registration flow
- form captures at least:
  - object name
  - interval value
  - interval unit
- save binds the tag to the object
- object immediately appears in the system/dashboard

---

### 2. Check Status of an Existing Object

As a user, I scan an already-registered tag and see the current status of that object.

#### Acceptance Criteria

- known tag scan resolves to the correct object
- user sees:
  - object name
  - last reset time
  - next due time/date
  - time elapsed
  - time remaining or overdue amount
- user can navigate to full dashboard

---

### 3. Reset Object Timer

As a user, I scan a registered tag and choose to reset its timer after completing the real-world action.

#### Acceptance Criteria

- reset is explicit, not automatic
- reset updates last-reset timestamp
- derived due/remaining values update immediately
- dashboard reflects change right away

---

### 4. View All Tracked Objects

As a user, I can open a dashboard showing every tagged object and its current state.

#### Acceptance Criteria

- dashboard shows all registered objects
- each object shows enough status to be useful at a glance
- dashboard highlights due/overdue items first

---

### 5. Recover from Incomplete Setup

As a user, if I scan a new tag but don’t finish setup, I can come back later and complete it.

#### Acceptance Criteria

- unknown tags can remain in a pending/unassigned state
- pending tags are visible in an admin/setup area
- user can complete registration later

---

## Out of Scope for v1

The following are not in v1:

- multiple timers per object
- one tag linked to multiple objects
- automatic task completion on scan
- advanced recurring rules
- maintenance history beyond last reset
- QR code support
- multi-user permissions model
- desktop authoring workflows
- import/export
- analytics charts
- object photos / attachments
- advanced notification scheduling

---

## Core Domain Model

### Tracked Object

Represents a physical thing with a timer attached.

#### Required Fields

- `id`
- `name`
- `tag_id`
- `interval_value`
- `interval_unit`
- `created_at`
- `last_reset_at`

#### Optional Fields

- `notes`
- `icon`
- `category`
- `due_soon_threshold_days`
- `active`

#### Derived Fields

- `elapsed_duration`
- `next_due_at`
- `remaining_duration`
- `is_overdue`
- `overdue_duration`
- `status`

---

### Pending Tag

Represents an NFC tag seen by the system but not yet assigned.

#### Fields

- `tag_id`
- `first_seen_at`
- `last_seen_at`
- `scan_count`
- `source_device` if available

---

## Status Model

Tracked objects should expose a simple status bucket.

### Recommended Statuses

- `healthy`
- `due_soon`
- `due_now`
- `overdue`

### Suggested Logic

- `overdue` when `now > next_due_at`
- `due_soon` when remaining time is less than or equal to a configured threshold
- `healthy` otherwise

### Default Due Soon Threshold

Use a fixed default threshold of **3 days** for v1.

---

## Interval Model

### Required Units

- days
- weeks
- months

### Optional

- hours

### Recommended Structure

- `interval_value: integer`
- `interval_unit: day | week | month`

Examples:

- 30 days
- 2 weeks
- 3 months

---

## Scan Behavior

### Unknown Tag Scan

When a scanned `tag_id` is not registered:

#### System Behavior

- create or update a `Pending Tag`
- route the user to a registration experience
- bind the registration form to the pending tag

#### User Experience

- “New tag detected”
- form to create object

#### Rule

Unknown tag scan never auto-creates a tracked object.

---

### Known Tag Scan

When a scanned `tag_id` matches a tracked object:

#### System Behavior

- resolve object
- present object status UI
- offer explicit actions

#### User Experience

- object detail/status
- reset timer
- open dashboard
- optionally edit object

---

## User Flows

### Flow 1: Register New Object

1. User scans fresh NFC tag
2. Integration sees unknown `tag_id`
3. Tag goes into pending state
4. Phone opens registration form
5. User enters:
   - name
   - interval value
   - interval unit
   - optional icon
   - optional notes
6. User taps save
7. System creates tracked object
8. Pending tag is consumed or cleared
9. Object appears in dashboard/entities

---

### Flow 2: Check Object Status

1. User scans known tag
2. System resolves object
3. Phone opens object detail/status
4. User sees timing information and actions

---

### Flow 3: Reset Timer

1. User scans known tag
2. User taps **Reset timer**
3. `last_reset_at = now`
4. Derived status updates immediately

#### Rule

Scan should not auto-reset. Reset must be explicit.

---

### Flow 4: Resume Incomplete Onboarding

1. User scans unknown tag
2. Registration starts but is abandoned
3. User later opens setup/admin area
4. Pending tag is visible
5. User completes setup

---

## Dashboard Requirements

### Main Purpose

Show the status of all “stuck” objects in one place.

### Required Sections

#### A. Attention Needed

- overdue first
- due soon second

#### B. All Objects

List or grid of all tracked objects

#### C. Pending / Unassigned Tags

Visible somewhere, even if collapsed or admin-only

### Per-Object Data

- name
- icon
- status
- interval
- elapsed
- remaining or overdue
- last reset
- next due

### Per-Object Actions

- reset timer
- open details

---

## Home Assistant Entities

Expose a modest entity set in v1.

### Per Tracked Object

#### Sensors

- `sensor.<slug>_status`
- `sensor.<slug>_next_due`
- `sensor.<slug>_time_remaining`
- `sensor.<slug>_time_elapsed`

#### Binary Sensor

- `binary_sensor.<slug>_overdue`

#### Button

- `button.<slug>_reset`

### Global Sensors

- total tracked objects
- overdue count
- due soon count
- pending tag count

---

## Editing Capabilities

### Must Support

- rename object
- change interval value/unit
- change icon/notes
- deactivate/reactivate object

### Nice to Have

- reassign tag to a different tag
- detach tag and keep object

### Can Wait Until v2

- merge objects
- duplicate objects
- bulk edit

---

## Delete Behavior

### Required

User must be able to delete a tracked object.

### Expected Behavior

- object removed from registry
- entities removed cleanly
- original tag becomes unknown again if scanned later

### Optional

- archive instead of hard delete

---

## Error Handling and Edge Cases

### Repeated Unknown Tag Scans

- do not create duplicate pending entries
- update existing pending tag instead

### Abandoned Registration

- pending tag persists
- can be resumed later

### Already Assigned Tag

- scan must resolve to existing object
- never create a duplicate object accidentally

### Double Reset Tap

- should be safe and idempotent enough
- no corruption

### Interval Changed Later

- next due recalculates from last reset using the new interval

### Long Overdue Object

- UI should clearly show overdue duration

### Missing Mobile Deep Link Support

- fallback path should still exist into dashboard/setup

---

## Mobile UX Requirements

### Unknown Tag

Should feel like:

- “This tag isn’t set up yet”
- one obvious next action: **Create object**

### Known Tag

Should feel like:

- “This is the HVAC Filter”
- status visible immediately
- one obvious action: **Reset timer**

### Navigation Goals

- at most 1–2 taps after scan
- mobile-first layout
- avoid forcing users through HA menus

---

## Configuration and Settings

### Global Settings

- default due-soon threshold
- default icon/category optional
- whether inactive objects appear on main dashboard
- pending tag retention timeout, optional

### Per-Object Settings

- interval value
- interval unit
- name
- icon
- notes
- optional due-soon threshold override

---

## Notifications in v1

Keep notifications minimal.

### Recommendation

Expose entities/status well enough that users can create their own notifications.

### Optional Built-In

- one simple daily check for overdue/due-soon objects

Do not let notification logic dominate v1.

---

## Safety Rules

- no automatic reset on scan
- no automatic registration on unknown scan
- deletes require confirmation
- tag reassignment requires confirmation

---

## Success Criteria for v1

v1 is successful if a user can:

1. install the integration
2. scan a new NFC tag
3. create a tracked object from phone in under a minute
4. see it on a dashboard
5. scan it later and understand its status immediately
6. reset it with one tap
7. have due/overdue states update correctly

---

## Release Statement

> Stuck is a Home Assistant integration for binding NFC tags to physical objects and tracking recurring time-based reminders for those objects. Scan a new tag to create an object, scan an existing tag to view status or reset its timer, and manage everything from a dashboard.
