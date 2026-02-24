# Multi-Service Architecture Design

Designing and implementing a scalable system that handles diverse booking behaviors and pricing models for various pet services.

## Phase 1: Planning & Design
- [x] Create detailed Implementation Plan for Multi-Service Architecture
- [x] Get user approval on the proposed model changes

## Phase 2: Super Admin Model Updates
- [x] Update `Service` model with protocol enums (Shared)
- [x] Update `PricingRule` model with `service_duration_type`, `pricing_model`, and capacity fields
- [x] Apply database migrations

## Phase 3: Super Admin Builder UI Updates
- [x] Revert `ServiceForm.vue` to original state
- [x] Update `FacilityForm.vue` with protocol selection and auto-mapping
- [x] Update `StepPricing.vue` with protocol selection and auto-mapping
- [x] Hide advanced pricing unit/strategy fields for cleaner UX

## Phase 4: Backend Booking Engines
- [x] Implement `BaseEngine`, `SlotEngine`, and `DayEngine` in `customer_service`
- [x] Implement `BookingRouter` factory
- [x] Update `service_provider_service` with protocol metadata fields
- [x] Refactor `BookingViewSet.perform_create` to use engines
- [/] Verify with test scripts

## Phase 5: Provider Dashboard & Frontend
- [ ] Update Provider Dashboard to handle diverse booking types
- [ ] Refine Checkout flow with duration selection (e.g. Boarding date range)
