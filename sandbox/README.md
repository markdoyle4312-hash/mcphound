# Sandbox (Phase 4 / v1.5)

Dynamic analysis of untrusted MCP servers runs ONLY here.

## Rules
1. Never run a fixture or third-party MCP server on the host or in a developer shell.
2. The `target` container mounts no source tree, no credentials (dummy env only), no host network.
3. Every outbound connection traverses `egress-proxy`; flows are recorded to `flows/` and turned into findings (undeclared egress, token exfiltration attempts).
4. Containers are destroyed after each scan; scan artifacts persist only via the mcpvet results JSON.
5. While this scaffold is unbuilt (pre-Phase 4), do dynamic exploration in a throwaway VM with no credentials.

## Local run (when implemented)
```bash
docker compose -f sandbox/docker-compose.sandbox.yml build
docker compose -f sandbox/docker-compose.sandbox.yml up
# mcpvet will publish a scan driver:
# uv run mcpvet sandbox-run <server-ref> --output results.json
```
