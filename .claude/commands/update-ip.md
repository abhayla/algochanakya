# Update AlgoChanakya Remote Access IP

Update the firewall rules and PostgreSQL pg_hba.conf to allow remote access from a new IP address.

## Arguments
- $ARGUMENTS: The new IP address (e.g., "116.75.158.249")

## Instructions

The user wants to update the AlgoChanakya remote access configuration for a new IP address: $ARGUMENTS

Run this PowerShell command on the VPS to update everything:

```powershell
powershell -ExecutionPolicy Bypass -File "C:\Apps\shared\scripts\Update-AlgoChanakyaIP.ps1" -NewIP "$ARGUMENTS"
```

This script will:
1. Delete old firewall rules (AlgoChanakya-PostgreSQL, AlgoChanakya-Redis)
2. Create new firewall rules for the new IP
3. Update pg_hba.conf with the new IP
4. Reload PostgreSQL configuration

After running, verify the changes by showing:
- The updated firewall rules
- The updated pg_hba.conf entry for algochanakya

If no IP is provided in $ARGUMENTS, ask the user for their new IP address.

Connection details remain:
- Host: 103.118.16.189
- PostgreSQL Port: 5432
- Redis Port: 6379
- Database: algochanakya
- User: algochanakya_user
- Password: AlgoChanakya2024Secure
- Redis DB: 1
