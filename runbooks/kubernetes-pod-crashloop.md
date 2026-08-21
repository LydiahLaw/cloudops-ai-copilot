# Runbook: Kubernetes Pod CrashLoopBackOff

## Symptoms
- `kubectl get pods` shows pod status as `CrashLoopBackOff`
- Restart count increasing steadily over time
- Application unavailable or serving intermittent errors

## Likely Causes
- Application fails to start due to a misconfiguration (bad env var, missing secret/configmap)
- Insufficient memory causing OOMKilled restarts
- Failing liveness/readiness probe killing the container before it's ready
- Missing dependency (database, downstream service) unreachable at startup

## Diagnostic Commands
```bash
kubectl describe pod <pod-name> -n <namespace>
kubectl logs <pod-name> -n <namespace> --previous
kubectl get events -n <namespace> --sort-by='.lastTimestamp'
```

## Remediation
1. Check `kubectl describe pod` output for the exact reason (OOMKilled, probe failure, etc.)
2. If OOMKilled: increase memory limits in the deployment manifest
3. If probe failure: verify the liveness/readiness probe path and initial delay settings
4. If missing config: confirm the ConfigMap/Secret exists and is correctly mounted
5. Apply the fix and monitor: `kubectl rollout status deployment/<name> -n <namespace>`

## Validation
- Confirm pod status shows `Running` and stays stable: `kubectl get pods -w`
- Confirm restart count stops increasing after 5 minutes

## Escalation Conditions
- If the pod crashes only under production load but not in staging, escalate to check resource limits and horizontal scaling
- If the root cause is a downstream dependency outage, escalate to the owning team

## Security Considerations
- Do not log sensitive environment variables when debugging via `kubectl logs`
- Verify RBAC permissions before granting broader `describe`/`logs` access to debug