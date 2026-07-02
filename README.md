# SatDump_Publisher

Minimal satdump publisher CLI.

Usage
-----

Install locally:

```bash
pip install .
# or for editable install during development
pip install -e .
```

Run the CLI:

```bash
satdump_publisher --message "Hello from satdump_publisher"
```

Docker
------

Build the image:

```bash
docker build -t satdump-publisher .
```

Run the container:

```bash
docker run --rm satdump-publisher --message "Hello from container"
```

Docker Compose
--------------

Run using Docker Compose:

- Mount your incoming data into the container at `/data/input` (read-only). Example host path used in the compose file: `Z:\drewsum\SatDump\live_output`.
- The container will write DB and generated site into `/data`, which is bound to the repository `./output` folder, so the generated site will appear at `./output/www` on the host.

Compose maps (example):

```
Z:\drewsum\SatDump\live_output -> /data/input (read-only)
./output -> /data
```

```bash
docker compose up --build
```

To run the service once and remove the container:

```bash
docker compose run --rm publisher --message "Hello via compose"
```

Files of interest
- `satdump_publisher/__init__.py` - package entry and version
- `satdump_publisher/cli.py` - main CLI implementation
- `pyproject.toml` - packaging metadata
- `Dockerfile` and `.dockerignore`
