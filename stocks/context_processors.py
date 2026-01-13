def notification_settings(request):
    """
    Add notification settings to template context
    """
    return {
        'NOTIFICATION_SETTINGS': {
            'snapshot_ready_timeout': 10000,  # 10 seconds
            'snapshot_generated_timeout': 15000,  # 15 seconds
            'show_notifications': True,  # Can be controlled via user preferences
        }
    } 