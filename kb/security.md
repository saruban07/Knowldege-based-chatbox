# Security

## Overview

Security is a top priority for our platform. We provide multiple layers of protection including strong password policies, multi-factor authentication, session management, encryption, access controls, and security monitoring.

This article explains common security settings and best practices to help keep your account and organization secure.

---

## Password Requirements

To protect your account, all passwords must meet the following requirements:

* Minimum 12 characters
* At least one uppercase letter (A-Z)
* At least one lowercase letter (a-z)
* At least one number (0-9)
* At least one special character (!@#$%^&*)

Examples of strong passwords:

* MySecurePass2025!
* Team@Workspace123
* DataScience#2026

Avoid using:

* Your name
* Birth dates
* Common words
* Reused passwords from other websites

---

## Changing Your Password

To update your password:

1. Open **Settings**.
2. Navigate to **Security**.
3. Click **Change Password**.
4. Enter your current password.
5. Enter and confirm the new password.
6. Click **Save Changes**.

You will receive a confirmation email after a successful password update.

---

## Password Reset

If you forgot your password:

1. Go to the login page.
2. Click **Forgot Password**.
3. Enter your registered email address.
4. Open the password reset email.
5. Click the reset link.
6. Create a new password.

Password reset links expire after 24 hours for security reasons.

---

## Two-Factor Authentication (2FA)

We strongly recommend enabling Two-Factor Authentication.

Supported methods:

* Authenticator Apps
* SMS Verification
* Backup Recovery Codes

To enable 2FA:

1. Open **Settings > Security**.
2. Select **Two-Factor Authentication**.
3. Choose a verification method.
4. Complete the setup process.
5. Save your recovery codes.

Benefits of 2FA:

* Additional account protection
* Reduced risk of unauthorized access
* Protection against stolen passwords

---

## Login Verification

When suspicious login activity is detected:

* Additional verification may be required.
* Verification emails may be sent.
* Temporary login restrictions may be applied.

Examples of suspicious activity:

* Login from a new country.
* Login from a new device.
* Multiple failed login attempts.

---

## Account Lockout Policy

Accounts are temporarily locked after five consecutive failed login attempts.

When an account is locked:

* Login access is blocked for 15 minutes.
* Password reset remains available.
* Administrators may unlock accounts manually.

This policy helps prevent brute-force attacks.

---

## Active Sessions

You can review all active sessions associated with your account.

To view active sessions:

1. Open **Settings > Security**.
2. Select **Active Sessions**.

You can:

* View logged-in devices
* Review login locations
* See last activity timestamps
* Revoke suspicious sessions

---

## Session Timeout

For security purposes, inactive sessions automatically expire after 30 minutes.

You may be logged out when:

* The browser remains idle.
* The application is inactive.
* Security risks are detected.

Simply log in again to continue.

---

## Data Encryption

All customer data is protected using industry-standard encryption.

Security measures include:

* Encryption in transit using HTTPS/TLS
* Encryption at rest for stored data
* Secure password hashing
* Encrypted backups

Sensitive information is never stored in plain text.

---

## API Key Security

API keys should be treated like passwords.

Best practices:

* Store keys securely
* Never share keys publicly
* Rotate keys regularly
* Remove unused keys
* Use separate keys for different applications

To generate API keys:

1. Open **Settings > Security > API Keys**.
2. Click **Create API Key**.
3. Copy and store the key securely.

---

## Security Alerts

The platform automatically sends alerts for important security events.

Examples include:

* Password changes
* New device logins
* API key creation
* 2FA changes
* Account recovery requests

Alerts are delivered via email and in-app notifications.

---

## Reporting Security Issues

If you suspect unauthorized access:

1. Change your password immediately.
2. Revoke active sessions.
3. Rotate API keys.
4. Enable 2FA if not already enabled.
5. Contact support.

Our security team investigates all reported incidents promptly.

---

## Frequently Asked Questions

### How do I secure my account?

Enable 2FA, use a strong password, and regularly review active sessions.

### Why was my account locked?

Your account may be temporarily locked after multiple failed login attempts.

### How do I recover my account?

Use the password reset option or contact support if you cannot access your registered email address.

### How do I view active devices?

Navigate to **Settings > Security > Active Sessions**.

### Can I force logout all devices?

Yes. Use the **Revoke All Sessions** option under Active Sessions.
