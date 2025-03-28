


## build image

```bash
docker build -t ghcr.io/princinv/swarm-orchestration:latest .
docker compose down && docker compose up -d
```

## restart image

```bash
docker stop swarm-orchestration
docker rm swarm-orchestration
docker build -t ghcr.io/princinv/swarm-orchestration:latest .
docker run -d \
  -v ./logs:/var/log/ \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v ./dependencies.yml:/config/dependencies.yml \
  -e DATABASE_LIST="semaphore_db,gitea_db,komodo_db" \
  -e STACK_NAME="swarm-dev" \
  -e DEPENDENCIES_FILE=/config/dependencies.yml \
  -e RELABEL_TIME=60 \
  -e DRY_RUN=true \
#   -e RUN_ONCE=true \
  --name swarm-orchestration \
  ghcr.io/princinv/swarm-orchestration
```

## push image

```bash
docker push ghcr.io/princinv/swarm-orchestration:latest
```

def defines a reusable function
try/except handles errors gracefully
with open(...) as f: is Python's way of safely reading files (automatically closes)
yaml.safe_load(f) parses a YAML file into a Python dictionary
return hands the result back to whoever called the function
Most lines ending in : start a new indented code block
Python's dictionaries (dict) are like JSON or YAML mappings: {"key": "value"}

def ...: → function body
if ...: → conditional block
for ...: → loop body
try: and except: → error handling blocks


Let me know when you’d like to:

Add dependencies.yaml support
Switch to real service-to-anchor mappings
Build CLI flags for runtime overrides (argparse)
Learn how to unit test this using pytest in a container