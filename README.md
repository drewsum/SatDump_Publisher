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

Run using Docker Compose (binds `./data` to `/data` in container):

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
