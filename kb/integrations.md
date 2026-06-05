# Integrations

## Slack Integration

Connect your workspace to Slack:

1. Go to **Settings** > **Integrations** > **Slack**.
2. Click **Connect to Slack**.
3. Authorize the app in your Slack workspace.
4. Choose which channels receive notifications.
5. Click **Save Configuration**.

Supported events: new tickets, status updates, and daily summaries.

## Webhook Setup

Send events to your own endpoints:

1. Open **Settings** > **Integrations** > **Webhooks**.
2. Click **Create Webhook**.
3. Enter your endpoint URL (must use HTTPS).
4. Select event types to subscribe to.
5. Copy the signing secret and store it securely.
6. Click **Create**.

Webhook payloads are signed with HMAC-SHA256. Verify the `X-Signature` header on every request.

## API Access

Generate API keys under **Settings** > **Security** > **API Keys**.

- Rate limit: 100 requests per minute on Pro, 1000 on Enterprise.
- Use the `Authorization: Bearer <key>` header.
- API documentation: https://docs.example.com/api

## Disconnecting an Integration

1. Go to **Settings** > **Integrations**.
2. Find the integration you want to remove.
3. Click **Disconnect**.
4. Confirm the action.

Disconnecting stops all data flow immediately. Historical data in the third-party service is not deleted automatically.
