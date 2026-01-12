# AVIATOR CRASH (Aviator predict Vector)

This project unifies logic from multiple Aviator predictor fronts and provides a Telegram bot that centralizes features into **AVIATOR CRASH**, the bot name in Telegram is **Aviator predict Vector**.

Quick start

1. Copy `.env.example` to `.env` and fill `BOT_TOKEN`, `API_ID`, `API_HASH`, `ADMIN_USERNAME`.
2. Build and run with Docker (or run locally):
   - docker build -t aviator-crash .
   - docker run -e BOT_TOKEN=... -e API_ID=... -e API_HASH=... -p 8000:8000 aviator-crash
3. Message your bot on Telegram. Use `/verify` to begin the phone/code flow, `/predict [site]` to request a prediction, `/subscribe` to receive periodic signals.

Deploying on Render

- The Docker image listens on the port provided by the `PORT` environment variable. Render sets `PORT` automatically for Docker services.
- Ensure the following environment variables are configured in your Render service (leave empty where appropriate): `BOT_TOKEN`, `API_ID`, `API_HASH`, `ADMIN_USERNAME`, `PREDICTION_INTERVAL`, `COLLECTION_INTERVAL`, `PROXY_URL` (if needed), `DEFAULT_LANG`, `WEBHOOK_BASE_URL` (e.g. `https://your-service.onrender.com`).
- **Webhooks recommended on Render (free plan):** set `WEBHOOK_BASE_URL` to your service URL; on startup the app will automatically call Telegram `setWebhook` to `WEBHOOK_BASE_URL + /webhook/<BOT_TOKEN>`. If `WEBHOOK_BASE_URL` is empty the server **will not** set a webhook automatically — That's fine for local/polling development but for Render (prod) you should set it.
- Health check path: `/healthz`. The manifest `backend/render.yaml` contains `healthCheckPath: /healthz` so Render can verify service readiness.

Note: If Render reports schema errors on `render.yaml`, paste the exact error lines here and I will fix them precisely.

Security notes

- Storing phone numbers and session files must be done securely. This prototype stores Telethon session files in `app/sessions/` per user.
- Be careful with `API_ID`/`API_HASH` and do not publish them.

Features

- /start, /verify, /contact_admin
- /predict, /subscribe, /unsubscribe, /sites
- Multi-language support via `app/translations/*.json`
- Site connectors and live odds scraping pipeline (prototype) via `app/scrapers.py`

Notes on predictions

- A realistic prediction system requires historical data. This prototype implements a **data collection pipeline** (scrapers + `observations` table) and a **heuristic predictor** to return actionable odds and confidence.
- For production-quality predictions we should:
  1. Collect historical multipliers and odds over time and store in `observations`.
  2. Implement training / backtesting (e.g., using scikit-learn or XGBoost) on labeled data.
  3. Continuously evaluate and calibrate the model and add monitoring/alerts.

Legal & scraping caution

- Many betting sites restrict scraping in their Terms of Service; prefer **official APIs** when available and ensure compliance with local laws and site rules.
- Do not store sensitive user data longer than necessary. Keep `API_HASH`/`API_ID`/`BOT_TOKEN` secure and use environment variables.

TODO

- Improve scrapers for specific sites and add robust parsers
- Implement dataset collection, model training and backtesting
- Unit tests, CI, and Render deployment instructions
