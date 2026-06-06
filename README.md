# Facebook Page Distributed API

[![Docker Compose](https://img.shields.io/badge/Docker%20Compose-ready-blue?logo=docker)](docker-compose.yml)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://python.org)
[![Django](https://img.shields.io/badge/Django-5.x-092E20?logo=django)](https://djangoproject.com)
[![Kafka](https://img.shields.io/badge/Apache%20Kafka-7.6-231F20?logo=apachekafka)](https://kafka.apache.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

An event-driven, microservices-based pipeline for automating Facebook Page interactions — comment classification, auto-reply, spam detection, and intelligent content moderation — powered by AI (Gemini / OpenAI) with full observability and fault tolerance.

---

## Table of Contents

- [Assignment Information](#assignment-information)
- [Architecture](#architecture)
- [Services](#services)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Quick Start](#quick-start)
  - [Environment Variables](#environment-variables)
- [Kafka Topics](#kafka-topics)
- [API Reference](#api-reference)
- [Public Webhook with Cloudflare Tunnel](#public-webhook-with-cloudflare-tunnel)
- [Observability](#observability)
- [Failure Handling](#failure-handling)
- [Testing](#testing)
- [GitHub Workflow](#github-workflow)
- [Project Structure](#project-structure)
- [License](#license)

---

## Assignment Information

| Field | Value |
|-------|-------|
| Course | Lập trình API |
| Topic | Hệ thống quản lý Facebook Page phân tán |
| Repository | https://github.com/BienTranNgoc/Facebook-API |
| Repository visibility | Public. If changed to Private, add the lecturer as a collaborator before submission. |
| Swagger UI | http://localhost:3000/swagger/ (planned for the REST/OpenAPI requirement) |

### Team Members

| Student ID | Full name | Class | Responsibility |
|------------|-----------|-------|----------------|
| 6451071004 | Trần Ngọc Biên | CQ.64.CNTT | System design, backend API, Kafka workflow, AI automation, deployment/testing report |

### Functional Scope

- Receive Facebook Page webhook events and normalize comment payloads.
- Publish events to Kafka for asynchronous processing.
- Classify comment intent, sentiment, and spam signals with AI or heuristic fallback.
- Generate automation commands for reply, hide, no-op, or manual review.
- Execute Facebook Graph API commands through the backend API.
- Store command state, idempotency keys, retry attempts, and processing errors.
- Monitor dead-letter and consumer lag signals through Prometheus, Grafana, and Alertmanager.

---

## Architecture

```
┌──────────────┐       ┌────────────────┐       ┌──────────────┐
│   Facebook   │──────▶│ webhook-service│──────▶│    Kafka      │
│   Platform   │ POST  │   :3001        │       │  raw_events   │
└──────────────┘       └────────────────┘       └──────┬───────┘
                                                       │
                                                       ▼
                                                ┌──────────────┐
                                                │ core-service  │
                                                │   :3002       │
                                                │ AI classify   │
                                                └──────┬───────┘
                                                       │
                                                       ▼
                                                ┌──────────────┐
                                       ┌───────│    Kafka      │
                                       │       │reply_commands │
                                       │       └──────────────┘
                                       ▼
                                ┌──────────────┐
                                │ backend-api   │──────▶ Facebook Graph API
                                │   :3000       │
                                └──────┬───────┘
                                       │ on failure
                                       ▼
                                ┌──────────────┐       ┌──────────────┐
                                │    Kafka      │──────▶│ retry-service │
                                │  send_failed  │       │   :3003       │
                                └──────────────┘       └──────┬───────┘
                                                              │
                                              ┌───────────────┼───────────────┐
                                              ▼                               ▼
                                       ┌──────────────┐                ┌──────────────┐
                                       │  send_retry   │                │  dead_letter  │
                                       │  (back to     │                │  (alert +     │
                                       │   backend)    │                │   manual)     │
                                       └──────────────┘                └──────────────┘
```

---

## Services

| Service | Port | Description |
|---------|------|-------------|
| **backend-api** | `3000` | REST proxy for Facebook Graph API, idempotent command sender, admin dashboard |
| **webhook-service** | `3001` | Facebook webhook verification, HMAC-SHA256 validation, payload normalization |
| **core-service** | `3002` | AI-powered intent/sentiment classification, automation rules engine |
| **retry-service** | `3003` | Exponential backoff retry with Dead Letter Queue |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend Framework | Django 5.x (Python 3.11+) |
| Message Broker | Apache Kafka (Confluent 7.6) |
| Database | PostgreSQL 16 |
| AI Provider | Google Gemini / OpenAI (with heuristic fallback) |
| Monitoring | Prometheus + Grafana + Alertmanager |
| Tracing | Jaeger |
| Log Analytics | OpenSearch + OpenSearch Dashboards |
| Tunnel | Cloudflare Tunnel (trycloudflare) |
| Containerization | Docker + Docker Compose |

---

## Getting Started

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) ≥ 24.0
- [Docker Compose](https://docs.docker.com/compose/install/) ≥ 2.20
- (Optional) A Facebook App with Page subscriptions for live mode

### Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/your-username/fb-page-distributed-api.git
cd fb-page-distributed-api

# 2. Copy and configure environment variables
cp .env.example .env

# 3. Start all services
docker compose up --build
```

Once all containers are healthy, verify the pipeline:

```bash
curl http://localhost:3000/health   # backend-api
curl http://localhost:3001/health   # webhook-service
curl http://localhost:3002/health   # core-service
curl http://localhost:3003/health   # retry-service
```

> **Tip:** Set `FACEBOOK_API_MODE=mock` (default) to run the full pipeline without real Facebook credentials.

### Environment Variables

All configuration is managed through `.env`. Copy from `.env.example` and customize:

| Variable | Default | Description |
|----------|---------|-------------|
| `FACEBOOK_API_MODE` | `mock` | `mock` for demo, `live` for real Facebook API |
| `FACEBOOK_PAGE_ID` | — | Your Facebook Page ID |
| `FACEBOOK_PAGE_ACCESS_TOKEN` | — | Page Access Token from Facebook Developer |
| `FACEBOOK_APP_SECRET` | — | Facebook App Secret for webhook signature validation |
| `WEBHOOK_VERIFY_TOKEN` | `local-verify-token` | Token for Facebook webhook verification handshake |
| `GEMINI_API_KEY` | — | Google Gemini API key for AI classification |
| `GEMINI_MODEL` | `gemini-1.5-flash` | Gemini model to use |
| `DASHBOARD_API_TOKEN` | — | Token to protect admin-mutating endpoints |
| `MAX_RETRY_COUNT` | `3` | Maximum retry attempts before Dead Letter Queue |
| `RETRY_BACKOFF_BASE_SECONDS` | `1` | Base delay (seconds) for exponential backoff |

See [`.env.example`](.env.example) for the complete list including database, Kafka topics, and port mappings.

---

## Kafka Topics

All inter-service communication flows through Kafka. Topics are auto-created by the `kafka-init` container:

| Topic | Producer | Consumer | Purpose |
|-------|----------|----------|---------|
| `raw_events` | webhook-service | core-service | Normalized Facebook events |
| `reply_commands` | core-service | backend-api | Automation commands (reply, hide, noop) |
| `send_retry` | retry-service | backend-api | Commands scheduled for another attempt |
| `send_failed` | backend-api | retry-service | Failed send attempts |
| `dead_letter` | retry-service | — (manual) | Exhausted / non-retryable messages |

---

## API Reference

### Swagger UI / OpenAPI

Required assignment link: http://localhost:3000/swagger/

Current status: the REST endpoints are implemented and listed below. The Swagger/OpenAPI endpoint will be enabled when the REST documentation requirement is completed.

### Backend API (`backend-api`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/posts` | List Facebook Page posts |
| `POST` | `/post` | Create a new post |
| `GET` | `/comments?post_id=...` | List comments on a post |
| `GET` | `/events` | List processed events |
| `GET` | `/errors` | List processing errors |
| `POST` | `/commands/process` | Manually submit a command |
| `GET` | `/commands/<command_id>` | Get command status |

**Response format:**

```json
// Success
{ "ok": true, "data": { ... } }

// Error
{ "ok": false, "error": { "code": "NOT_FOUND", "message": "..." } }
```

### Webhook Service (`webhook-service`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/webhook` | Facebook verification challenge |
| `POST` | `/webhook` | Receive Facebook event payloads |

---

## Public Webhook with Cloudflare Tunnel

Expose your local webhook to Facebook using the built-in Cloudflare Tunnel profile:

```bash
# Start all services + tunnel
docker compose --profile tunnel up --build

# Get the generated public URL
docker compose logs -f cloudflared
```

Copy the `https://<generated-subdomain>.trycloudflare.com` URL and configure it in your Facebook App:

```
Callback URL: https://<generated-subdomain>.trycloudflare.com/webhook
Verify Token: <same as WEBHOOK_VERIFY_TOKEN in .env>
```

---

## Observability

| Tool | URL | Purpose |
|------|-----|---------|
| Kafka UI | http://localhost:8080 | Topic inspection, consumer groups |
| Prometheus | http://localhost:9090 | Metrics & alerting rules |
| Alertmanager | http://localhost:9093 | Alert routing & notifications |
| Grafana | http://localhost:3004 | Dashboards & visualization |
| Jaeger | http://localhost:16686 | Distributed tracing |
| OpenSearch Dashboards | http://localhost:5601 | Log analytics |

### Alerting

Prometheus monitors Kafka consumer lag and Dead Letter Queue growth. When `dead_letter` offset increases, Alertmanager triggers a notification. Rules are defined in [`prometheus/alert.rules.yml`](prometheus/alert.rules.yml).

---

## Failure Handling

The system implements four mandatory fault-tolerance mechanisms:

| Mechanism | Implementation |
|-----------|---------------|
| **Retry with Exponential Backoff** | `retry-service` consumes `send_failed`, delays with `base × 2^attempt`, publishes to `send_retry` |
| **Circuit Breaker** | Facebook Graph API client and AI analyzer in `core-service` |
| **Idempotent Consumers** | `core-service` deduplicates by `event_id`; `backend-api` deduplicates by `command_id` via `IdempotencyKey` |
| **Dead Letter Queue + Alerting** | Messages exceeding `MAX_RETRY_COUNT` or non-retryable errors → `dead_letter` topic → Prometheus alert |

---

## Testing

```bash
# Backend API tests
cd services/backend-api
python manage.py test applications

# Retry service tests
cd services/retry-service
python tests.py

# Core service AI tests
cd services/core-service
python -m pytest test_ai.py

# Validate Docker Compose syntax
docker compose config --quiet
```

---

## GitHub Workflow

### Repository Rules

- The repository must remain Public for grading.
- If the repository is changed to Private, the lecturer must be added as a collaborator before submission.
- All team-facing project information must stay in this `README.md`: topic name, team members, functional scope, run instructions, and Swagger UI link.

### Branching Model

| Branch pattern | Purpose | Rule |
|----------------|---------|------|
| `main` | Stable production-ready code | Do not commit directly. Merge only from `develop`. |
| `develop` | Main integration branch | Merge reviewed `feature/*` and `defect/*` branches here. |
| `feature/<name>` | New feature work | Branch from `develop`, then create a Pull Request back to `develop`. |
| `defect/<name>` | Bug fix work | Branch from `develop`, then create a Pull Request back to `develop`. |

Local compatibility branches using `feature/*` have been created for the older `feat/*` branches. New work should use `feature/<name>` or `defect/<name>` to match the assignment rule.

### Required Development Flow

1. Update `develop`.

```bash
git switch develop
git pull origin develop
```

2. Create a working branch.

```bash
git switch -c feature/<feature-name>
```

3. Commit with the required message format.

```bash
git commit -m "feat: add webhook normalization"
```

4. Push and open a Pull Request into `develop`.

```bash
git push origin feature/<feature-name>
```

5. Another member reviews the Pull Request.
6. Merge into `develop` only after review and test evidence.
7. Merge `develop` into `main` only when the project is stable for submission/demo.

### Commit Message Standard

Use this format:

```text
<type>: <short description>
```

Allowed types:

| Type | Meaning |
|------|---------|
| `feat` | Add a feature |
| `fix` | Fix a bug |
| `docs` | Update documentation |
| `refactor` | Improve code structure without behavior change |
| `test` | Add or update tests |
| `chore` | Build, tooling, configuration, or maintenance |

Examples:

```text
feat: add facebook webhook validation
fix: prevent duplicate reply command processing
docs: update docker compose run guide
test: cover retry dead letter flow
```

---

## Project Structure

```
.
├── services/
│   ├── backend-api/          # Django REST API + Kafka consumer worker
│   ├── webhook-service/      # Flask webhook receiver + Kafka producer
│   ├── core-service/         # AI classification + automation engine
│   └── retry-service/        # Retry logic + DLQ handler
├── prometheus/
│   ├── prometheus.yml        # Scrape configuration
│   └── alert.rules.yml       # Alerting rules (DLQ, consumer lag)
├── alertmanager/
│   └── alertmanager.yml      # Alert routing configuration
├── grafana/
│   ├── datasources.yml       # Prometheus + OpenSearch datasources
│   └── config.monitoring     # Grafana environment config
├── scripts/
│   └── create_topics.sh      # Manual Kafka topic creation
├── docs/                     # Assignment specification
├── docker-compose.yml        # Full stack orchestration
├── .env.example              # Environment variable template
└── README.md
```

---

## License

This project is licensed under the [MIT License](LICENSE).

