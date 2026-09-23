# Pho65 App Container

## How to Build

```bash
docker build -t pho65-app .
```

## How to Run Standalone for a Quick Local Check

```bash
docker run -p 5000:5000 -e OVERDUE_MIN=20 -e NOW_OVERRIDE="2026-01-15 12:30" -v $(pwd)/../../sample-data:/data pho65-app
```

## Known-Answer Test

With `OVERDUE_MIN=20`, the packaged `pho65-orders-valid.csv`, and `NOW_OVERRIDE="2026-01-15 12:30"`, the app must show exactly **3 overdue orders** (O-001, O-002, O-003). This is the known-answer test documented in `week3/sample-data/README.md`. Do not change the fixture or this expected count.

## Environment Variables

- `ORDERS_CSV`: Can point at a different filename inside the mounted `/data` directory if a different fixture is used.
- `OVERDUE_MIN`: Minimum minutes for an order to be considered overdue.
- `NOW_OVERRIDE`: Override the current time for testing purposes.

## Startup Output

The app prints the following to stdout at startup:

```
Pho65 order tracker started. OVERDUE_MIN=<value> ORDERS_CSV=<path>
```

This line is important for later `docker logs` / SSH-based diagnosis exercises.
