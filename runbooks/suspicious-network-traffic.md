# Runbook: Suspicious Network Traffic Detected

## Symptoms
- IDS (e.g., Suricata) alerts flagging unusual outbound connections
- Unexpected spike in traffic to an unfamiliar external IP or port
- Fail2ban logs showing repeated failed authentication attempts from a single source

## Likely Causes
- Brute-force login attempts against SSH or another exposed service
- Compromised host attempting outbound command-and-control communication
- Misconfigured service unintentionally exposed to the public internet
- False positive from a legitimate but unusual traffic pattern (e.g., new integration)

## Diagnostic Commands
```bash
# Check active connections and listening ports
sudo netstat -tulpn

# Review Suricata alerts
sudo tail -100 /var/log/suricata/fast.log

# Check Fail2ban status and banned IPs
sudo fail2ban-client status sshd

# Review recent authentication attempts
sudo grep "Failed password" /var/log/auth.log | tail -50
```

## Remediation
1. If confirmed malicious: block the source IP at the firewall level immediately
2. If a brute-force pattern: confirm Fail2ban jail is active and ban duration is adequate
3. If a service is unintentionally exposed: correct security group / firewall rules to restrict access
4. If host compromise is suspected: isolate the host from the network before further investigation

## Validation
- Confirm the source IP no longer appears in active connections
- Confirm Suricata alerts for this pattern have stopped
- Confirm no new unauthorized authentication attempts in the following 30 minutes

## Escalation Conditions
- If host compromise is confirmed or suspected, escalate immediately to isolate and begin incident response
- If the traffic pattern affects multiple hosts simultaneously, escalate as a potential coordinated attack

## Security Considerations
- Do not delete logs during investigation — preserve for forensic review
- Document all remediation steps taken with timestamps for the incident report
- Follow least-privilege principle when granting temporary investigative access