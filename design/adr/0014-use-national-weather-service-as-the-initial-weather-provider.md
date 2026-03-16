# ADR 0014: Use National Weather Service as the Initial Weather Provider

- Status: Accepted
- Date: 2026-03-16

## Context
The first weather provider needs to supply current conditions and active alerts without weakening SPF5000's offline-first display model. The product also benefits from a provider that does not require secret management or a paid API tier for the initial household-focused implementation.

The first implementation does not need global provider coverage yet, but it should still fit behind the weather-provider abstraction defined in ADR 0013 so additional providers can be added later.

## Decision
Use the United States National Weather Service API as the initial weather and alert provider.

The weather subsystem stores a configured location as a label plus latitude/longitude, resolves that location through NWS points/observation/hourly-forecast endpoints for current conditions, and uses NWS active alerts for normalized weather-alert data. Provider-specific responses are normalized into SPF5000 weather and alert models before they are cached or exposed through backend APIs.

## Consequences
- SPF5000 gains a no-API-key initial provider that offers both current conditions and active weather alerts for U.S. deployments.
- The backend can normalize one practical first provider now while keeping room for future providers such as Open-Meteo or OpenWeatherMap.
- The first implementation is intentionally U.S.-focused and depends on a manually configured lat/lon location instead of a broader global location-resolution flow.
