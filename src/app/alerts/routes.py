def handle_alerts(monitor, query: dict) -> tuple[dict, int]:
    """GET /alerts?since=<timestamp>"""
    since = int(query.get("since", "0"))
    alerts = monitor.get_alerts(since=since)
    return {"alerts": alerts, "count": len(alerts)}, 200


def handle_alert_status(monitor) -> tuple[dict, int]:
    """GET /alerts/status"""
    return monitor.get_current_status(), 200
