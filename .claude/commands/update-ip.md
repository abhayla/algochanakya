# Update Remote Access IP (All Projects)

Update firewall rules and PostgreSQL pg_hba.conf for ALL projects to allow remote access from a new IP address.

## Arguments
- $ARGUMENTS: The new IP address (e.g., "116.75.158.249")

## Instructions

The user wants to update remote access for ALL projects to a new IP address: $ARGUMENTS

Run this PowerShell command on the VPS to update everything:

```powershell
powershell -ExecutionPolicy Bypass -File "C:\Apps\shared\scripts\Update-AlgoChanakyaIP.ps1" -NewIP "$ARGUMENTS"
```

This script will:
1. Delete old per-project firewall rules for all 5 projects
2. Create new per-project firewall rules (PostgreSQL + Redis) for the new IP
3. Update pg_hba.conf for all 5 users to the new IP with /32 mask (preserving each user's auth method)
4. Reload PostgreSQL configuration

Projects covered:
- **AlgoChanakya** → `algochanakya_user` (scram-sha-256)
- **CricApp** → `cricapp_user` (md5)
- **CricScores** → `cricscores_user` (scram-sha-256)
- **RasoiAI** → `rasoiai_user` (scram-sha-256)
- **PastelNoter** → `pastelnoter_user` (scram-sha-256)

After running, verify the changes by showing:
- The updated firewall rules for each project
- The updated pg_hba.conf entries for all 5 users

If no IP is provided in $ARGUMENTS, ask the user for their new IP address.

Server details:
- Host: 103.118.16.189
- PostgreSQL Port: 5432
- Redis Port: 6379
