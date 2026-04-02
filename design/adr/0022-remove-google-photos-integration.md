# ADR 0022: Remove Google Photos Integration

**Date:** 2026-04-02

**Status:** Accepted

**Author:** Steven Hildreth

## Context

SPF5000 originally included integration with Google Photos using the Google Photos Ambient API. This integration was intended to allow users to sync photos from their Google Photos albums to the frame for offline playback.

The implementation included:
- OAuth 2.0 device flow authentication
- Google Photos Ambient API device registration
- Background sync coordinator for automatic photo downloads
- Deletion sync (removing photos from frame when removed from Google album)
- Full UI integration in the admin Sources page
- Doctor diagnostics and troubleshooting features

## Problem

During deployment and testing, the Google Photos integration proved completely non-functional due to Google's API restrictions:

1. **Device Registration Blocked:** Every attempt to register an Ambient API device returned HTTP 403 Forbidden, even with valid OAuth tokens.

2. **API Access Restricted:** The Google Photos Ambient API is intentionally restricted to Google-approved hardware partners (Nest Hub, etc.). Third-party devices cannot register regardless of OAuth configuration.

3. **OAuth Consent Screen Insufficient:** Even with a published OAuth consent screen and test users properly configured, Google blocks device creation for unapproved clients.

4. **No Alternative API:** The Google Photos Library API (which allowed broader access) was deprecated and shut down by Google in 2021.

5. **Verification Process Opaque:** Google's app verification process for Photos API access is lengthy (weeks to months), expensive, and offers no guarantee of approval for non-Google hardware.

## Decision

**Remove all Google Photos integration from SPF5000, effective immediately.**

This decision removes:
- All Google Photos provider code
- OAuth device flow implementation
- Ambient API client code
- Sync coordinators and services
- Database tables for provider state
- Frontend UI components
- Documentation

## Consequences

### Positive
- **Reduced complexity:** ~2,000 lines of code removed
- **No more support burden:** No users will encounter broken Google Photos setup
- **Cleaner codebase:** No dead code or non-functional features
- **Faster startup:** No Google Photos coordinator threads
- **Lower memory usage:** No httpx client accumulation from Google API calls

### Negative
- **No Google Photos sync:** Users cannot directly sync from Google Photos albums
- **Manual import required:** Users must download photos from Google Photos and copy to import directory

### Neutral
- **Database migration:** Existing Google Photos tables remain in existing databases but are no longer used or created for new installations

## Alternatives Considered

### 1. Use gphotos-sync Integration
**Rejected.** While gphotos-sync successfully backs up Google Photos, integrating it would:
- Add Python dependency management complexity
- Require users to run separate sync tool
- Still not provide real-time sync
- Add another point of failure

### 2. Wait for Google Approval
**Rejected.** The verification process:
- Takes weeks to months
- Costs money to submit
- No guarantee of approval
- Google actively hostile to third-party photo frame devices

### 3. Use Google Takeout
**Documented as workaround.** Users can:
- Export photos via Google Takeout
- Extract to local import directory
- Run manual import in SPF5000

This is the recommended approach for users with existing Google Photos libraries.

## Workaround for Users

Users who want to display photos from Google Photos should:

1. Go to https://takeout.google.com
2. Select only "Google Photos"
3. Choose export frequency and format
4. Download the export archive
5. Extract photos to `/var/lib/spf5000/sources/local-files/import/`
6. Run "Scan now" in SPF5000 Sources page
7. Import discovered photos

## Conclusion

Google's Photos API restrictions make third-party photo frame integration impossible without Google's explicit approval, which is not granted to open source projects or non-partner hardware.

Rather than maintain non-functional code and frustrate users, we remove the feature entirely and document the manual import workaround.

**Google Photos integration is dead. Long live manual imports.**

---

## References

- Original Google Photos ADR: ~~0012-use-google-photos-ambient-api-for-offline-first-local-sync.md~~ (deleted)
- Google Photos Ambient API: https://developers.google.com/photos/ambient
- gphotos-sync: https://github.com/gilesknap/gphotos-sync
- Google Takeout: https://takeout.google.com
