{{ config(
    materialized='table',
    engine='MergeTree()',
    order_by='device_id'
) }}

with device_health as (
    select
        device_id,
        device_type,
        location,
        zone,
        status,
        maintenance_due,
        -- Take the most recent health score per device
        argMax(health_score, reading_date)  as latest_health_score,
        max(reading_date)                   as last_reading_date
    from {{ ref('fct_device_health') }}
    group by
        device_id,
        device_type,
        location,
        zone,
        status,
        maintenance_due
),

devices_needing_action as (
    select * from device_health
    where maintenance_due = 1 or latest_health_score < 50
)

select
    device_id,
    device_type,
    location,
    zone,
    status,
    maintenance_due          as overdue,
    latest_health_score      as health_score,
    last_reading_date,
    -- Columns for API compatibility (devices router expects these)
    0                        as days_since_maintenance,
    0                        as maintenance_interval_days,
    multiIf(
        maintenance_due = 1 and latest_health_score < 50,
            'URGENT: Maintenance overdue and health score critically low. Schedule immediate maintenance and inspection.',
        maintenance_due = 1,
            'Maintenance overdue. Schedule maintenance within the next 48 hours.',
        latest_health_score < 25,
            'CRITICAL: Health score very low. Perform emergency diagnostic and consider taking device offline.',
        latest_health_score < 50,
            'WARNING: Health score below acceptable threshold. Investigate anomalous readings and plan maintenance.',
        'No action required.'
    ) as recommendation,
    multiIf(
        maintenance_due = 1 and latest_health_score < 50, 'critical',
        maintenance_due = 1, 'high',
        latest_health_score < 25, 'critical',
        latest_health_score < 50, 'high',
        'low'
    ) as priority
from devices_needing_action
