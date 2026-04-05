# Sea State Service

Manages the state of the Red Sea for the Exodus Rush game.

## Overview

This service controls whether the Red Sea is closed, splitting, or split. Players must call the `/split` endpoint to part the waters before they can cross.

## Endpoints

- `GET /health` - Health check
- `GET /status` - Get current sea state
- `POST /split` - Initiate sea splitting
- `POST /close` - Close the sea (admin only, requires Bearer token)

## State Transitions

```
closed -> splitting -> split
   ^                     |
   |_____ (admin) _______|
```

## Configuration

### Environment Variables

- `PORT` - Service port (default: 8080)
- `STATE_CACHE_URL` - Etcd connection URL (format: "host:port")
- `ADMIN_TOKEN` - Token for admin operations

### State Backends

The service supports two backend types:

1. **EtcdBackend** (distributed) - Used when `STATE_CACHE_URL` is set
   - Ensures consistent state across all pods
   - Required for production multi-replica deployments

2. **InMemoryBackend** (per-pod) - Used when `STATE_CACHE_URL` is NOT set
   - Each pod maintains its own state
   - ⚠️ WARNING: Causes inconsistent behavior in multi-replica deployments!

## Development

### Local Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Run locally
python app.py
```

### Testing Endpoints

```bash
# Check health
curl http://localhost:8080/health

# Get status
curl http://localhost:8080/status

# Split the sea
curl -X POST http://localhost:8080/split

# Close the sea (admin)
curl -X POST http://localhost:8080/close \
  -H "Authorization: Bearer exodus-admin-2026"
```

## Docker

### Build

```bash
docker build -t sea-state-service .
```

### Run

```bash
# Without etcd (in-memory backend)
docker run -p 8080:8080 sea-state-service

# With etcd (distributed backend)
docker run -p 8080:8080 \
  -e STATE_CACHE_URL=etcd:2379 \
  sea-state-service
```

## Kubernetes Deployment

### Deploy

```bash
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
```

### Configuration Notes

The deployment runs 3 replicas by default. For proper operation in production:

1. Deploy an etcd cluster
2. Set the `STATE_CACHE_URL` environment variable in the deployment
3. Verify all pods are using `EtcdBackend` via the `/health` endpoint

### Verify Deployment

```bash
# Check pods
kubectl get pods -l app=sea-state-service

# Check service
kubectl get svc sea-state-service

# Test from within cluster
kubectl run -it --rm debug --image=curlimages/curl --restart=Never -- \
  curl http://sea-state-service/status
```

## Architecture

```
┌─────────────────────────────────────────┐
│         sea-state-service               │
│  ┌────────────┐      ┌──────────────┐  │
│  │    Flask   │──────│ StateManager │  │
│  │    App     │      └──────────────┘  │
│  └────────────┘              │          │
│                               │          │
│                    ┌──────────▼────────┐│
│                    │  Backend Factory  ││
│                    └──────────┬────────┘│
│                               │          │
│              ┌────────────────┴─────────┐
│              │                          │
│      ┌───────▼────────┐      ┌─────────▼──────┐
│      │ InMemoryBackend│      │  EtcdBackend   │
│      │   (per-pod)    │      │ (distributed)  │
│      └────────────────┘      └────────┬───────┘
│                                       │        │
└───────────────────────────────────────┼────────┘
                                        │
                                   ┌────▼────┐
                                   │  etcd   │
                                   │ cluster │
                                   └─────────┘
```

## License


