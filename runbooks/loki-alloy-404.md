# Runbook: Alloy Cannot Send Logs to Loki (HTTP 404)

## Symptoms
- Grafana Alloy logs show repeated HTTP 404 errors when pushing logs to Loki
- Loki dashboards show a gap in incoming log volume
- No new log entries appear in Grafana Explore for the affected host

## Likely Causes
- Alloy's remote_write endpoint URL is missing the required API path
- Loki push endpoint should be `/loki/api/v1/push`, not just the base URL
- Loki service may have restarted with a different port or path after an upgrade

## Diagnostic Commands
```bash
# Check Alloy's current config for the Loki endpoint
cat /etc/alloy/config.alloy | grep -A 3 "loki.write"

# Test the endpoint directly
curl -v http://<loki-host>:3100/loki/api/v1/push

# Check Alloy service logs for the exact error
journalctl -u alloy -n 50 --no-pager
```

## Remediation
1. Confirm the Loki endpoint in the Alloy config includes the full path: `http://<loki-host>:3100/loki/api/v1/push`
2. If the path is missing or incorrect, update the `loki.write` block in the Alloy config
3. Restart the Alloy service: `sudo systemctl restart alloy`

## Validation
- Confirm Alloy logs no longer show 404 errors: `journalctl -u alloy -f`
- Confirm new log entries appear in Grafana Explore within 1-2 minutes

## Escalation Conditions
- If the endpoint is correct but 404s persist, escalate to check Loki's own routing/ingress configuration
- If Loki itself is returning 500 errors instead of 404, this is a different issue — escalate immediately

## Security Considerations
- Do not expose the Loki push endpoint publicly without authentication
- Verify any reverse proxy in front of Loki preserves the full request path
