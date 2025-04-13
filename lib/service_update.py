"""
service_update.py
- Contains the logic for forcibly updating a Docker Swarm service via Docker SDK.
"""

def force_update_service(client, service_name, version, spec, dry_run=False):
    if dry_run:
        print(f"[DRY RUN] Would update service: {service_name}")
        return True

    try:
        client.api.update_service(
            service_name,
            version=version,
            name=spec["Name"],
            task_template=spec["TaskTemplate"],
            labels=spec.get("Labels", {}),
            mode=spec.get("Mode"),
            update_config=spec.get("UpdateConfig"),
            rollback_config=spec.get("RollbackConfig"),
            networks=spec.get("Networks", []),
            endpoint_spec=spec.get("EndpointSpec"),
        )
        return True
    except Exception as e:
        print(f"Service update failed: {e}")
        return False
