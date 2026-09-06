/**
 * The setup spec creates this administrator and the auth specs sign in as it, so both files
 * have to agree on it. Sharing the constants keeps the two specs from drifting into mutually
 * exclusive expectations, which is what previously made `npm run test:e2e` unrunnable.
 */
export const ADMIN_USERNAME = 'admin'
export const ADMIN_PASSWORD = 'e2e-admin-password-1'
export const WRONG_PASSWORD = 'e2e-definitely-not-the-password'
