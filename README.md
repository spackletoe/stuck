# Stuck Docs

This folder contains planning docs for **Stuck**, a Home Assistant concept for binding NFC tags to physical objects and tracking recurring time-based reminders.

## Documents

- [`stuck-v1-spec.md`](./stuck-v1-spec.md)
  - Product definition for v1
  - User stories
  - scope boundaries
  - dashboard and UX expectations
  - entity model and success criteria

- [`stuck-technical-architecture.md`](./stuck-technical-architecture.md)
  - Integration architecture
  - storage model
  - scan routing
  - entity and service design
  - navigation strategy
  - testing and milestones

## Suggested Next Steps

1. Review the v1 spec and trim anything that feels too big for first release.
2. Confirm the mobile scan UX based on what Home Assistant mobile deep links and actions support today.
3. Create a repo for the integration.
4. Turn the technical architecture into an implementation checklist.
5. Build the storage/model layer first, then entity platforms, then scan routing.
