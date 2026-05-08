# Stuck

<p align="center">
  <img src="https://raw.githubusercontent.com/spackletoe/stuck/main/assets/stuck-logo.png" alt="Stuck logo" width="220" />
</p>

<p align="center">
  <strong>Stick a tag on a thing. Scan it. Know when it needs attention again.</strong>
</p>

**Stuck** is a Home Assistant custom integration for binding NFC tags to physical objects and tracking recurring time-based reminders.

It is built for real-world things like:

- litter boxes
- HVAC filters
- water filters
- bins or supplies that need periodic refresh
- appliance maintenance points
- anything physical that benefits from a recurring reminder tied to the object itself

Stuck is not really a chore app.
It is closer to **object-based recurring reminders**.

---

## What Stuck does

Stuck lets you:

- create tracked objects with a name, tag, and interval
- track when an object was last reset
- see when it is next due
- see how long it has been since it was last handled
- see whether it is overdue
- reset the timer from Home Assistant
- route NFC tag scans into known vs unknown tag behavior

The long-term goal is simple:

> put an NFC sticker on a real object, scan it with your phone, and immediately see or reset its state.

---

## Current status

Stuck is in active development.

Right now it already includes:

- a custom integration scaffold
- config flow and options flow
- storage-backed tracked objects and pending tags
- services for creating, updating, deleting, dismissing, and resetting
- sensors, binary sensors, and reset buttons
- a first dashboard concept
- planning docs for the product, architecture, and implementation plan

It is usable for development and testing, but still early.

---

## Installation

### Option 1: HACS custom repository

If you are installing from another machine or want a normal custom-integration workflow, HACS is the easiest path.

1. Push this repo to GitHub.
2. In Home Assistant, open **HACS**.
3. Add this repo as a **Custom repository**.
4. Set the category to **Integration**.
5. Install **Stuck**.
6. Restart Home Assistant.
7. Go to **Settings → Devices & Services**.
8. Add the **Stuck** integration.

### Option 2: Local custom component install

If you prefer a direct local install, copy:

```text
custom_components/stuck/
```

into your Home Assistant config directory under:

```text
/config/custom_components/stuck/
```

Then restart Home Assistant and add the integration from **Settings → Devices & Services**.

---

## Initial setup

When you add the integration, Stuck currently asks for a small set of global defaults:

- default due-soon threshold in days
- whether inactive objects should be shown

These settings can be adjusted later through the integration options.

---

## Creating your first tracked object

At the moment, the easiest way to create objects is through Home Assistant services.

Open **Developer Tools → Actions/Services** and call:

```text
stuck.create_object
```

Example data:

```yaml
config_entry_id: YOUR_CONFIG_ENTRY_ID
name: Litter Box
tag_id: litterbox-test-tag
interval_value: 30
interval_unit: day
notes: Main litter box
active: true
```

If the call succeeds, Stuck should create entities for that object and make them visible after the integration reloads.

---

## Testing tag scan behavior

Before the full polished mobile flow exists, the easiest way to test scan behavior is by firing Home Assistant events.

Open **Developer Tools → Events** and fire:

```text
tag_scanned
```

### Unknown tag example

```yaml
tag_id: brand-new-unknown-tag
device_id: phone-test
```

Expected behavior:

- the tag is treated as unknown
- pending tag count should increase

### Known tag example

```yaml
tag_id: litterbox-test-tag
device_id: phone-test
```

Expected behavior:

- the tag resolves to an existing object
- it should not create a new pending tag

---

## Associating an existing Home Assistant tag

Stuck can now also turn an existing Home Assistant tag into a tracked object.

Use either:

```text
stuck.associate_existing_tag
```

or

```text
stuck.associate_existing_tag_from_helpers
```

or, if you are driving the flow from dashboard helpers:

```text
stuck.associate_selected_existing_tag_from_helpers
```

Example service data:

```yaml
config_entry_id: YOUR_CONFIG_ENTRY_ID
tag_entity_id: tag.garage_door
name: HVAC Filter
interval_value: 90
interval_unit: day
```

This is useful for the "Use Existing HA Tag" flow where Home Assistant owns tag creation and Stuck owns object tracking.

Stuck also now exposes a dynamic inventory of HA tag entities via:

```text
sensor.stuck_available_ha_tags
```

Its attributes separate:
- `available_tags`
- `assigned_tags`

so the long-term UI does not need to rely on a manually maintained dropdown helper.

## Resetting an object

You can reset an object in two ways:

### 1. Use the reset button entity
Each tracked object exposes a reset button.

### 2. Call the reset service
Service:

```text
stuck.reset_object
```

Example data:

```yaml
config_entry_id: YOUR_CONFIG_ENTRY_ID
tag_id: litterbox-test-tag
```

The service can now resolve by `tag_id`, which is much easier than using internal object IDs.

---

## Dashboard

A first dashboard can be built from the entities Stuck exposes.

Right now the integration supports a dashboard with:

- tracked object count
- overdue count
- due soon count
- pending tag count
- latest pending tag
- pending tag inbox sensor/attributes
- dynamic Home Assistant tag inventory via `sensor.stuck_available_ha_tags`
- per-object status
- next due
- elapsed time
- remaining time
- overdue state
- reset buttons

A polished dashboard experience is still evolving, but the entities are already there.

---

## Docs

Planning and implementation docs live here:

- [`docs/stuck-v1-spec.md`](./docs/stuck-v1-spec.md)
- [`docs/stuck-technical-architecture.md`](./docs/stuck-technical-architecture.md)
- [`docs/stuck-implementation-checklist.md`](./docs/stuck-implementation-checklist.md)

These are useful if you want to understand the product direction or contribute to development.

---

## Known rough edges

This project is still early, so expect some rough edges, especially around:

- dynamic entity management after runtime object changes
- tag-scan UX polish
- dashboard generation and layout
- service ergonomics
- documentation polish

The core model is working, but the product experience is still being shaped.

---

## Roadmap direction

Near-term priorities:

1. improve tag scan UX
2. make object creation and editing less dependent on dev tools
3. improve dashboard layout and object presentation
4. harden runtime behavior and error handling
5. improve installation and end-user docs

Longer-term goals:

- mobile-friendly “scan unknown tag → create object” flow
- better "add new tag" and "use existing HA tag" onboarding flows
- known tag detail and reset view / direct-open behavior
- better pending tag management
- friendlier setup and onboarding
- a more polished HACS-ready release experience

---

## Why this exists

A lot of Home Assistant flows are great at automating rooms, devices, and sensors.

Stuck is trying to make **physical objects** first-class too.

Not everything is a light, lock, or motion sensor.
Sometimes you just want to stick a tag on a thing and remember when it needs attention again.
