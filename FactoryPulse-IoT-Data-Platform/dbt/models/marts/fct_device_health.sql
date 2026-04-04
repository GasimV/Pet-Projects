{{ config(
    materialized='table',
    engine='MergeTree()',
    order_by='(device_id, reading_date)'
) }}

with daily_stats as (
    select * from {{ ref('int_device_daily_stats') }}
),

devices as (
    select * from {{ ref('dim_devices') }}
),

latest_alerts as (
    select
        device_id,
        argMax(severity, alert_timestamp) as latest_alert_severity,
        count() as alert_count
    from {{ ref('stg_alerts') }}
    group by device_id
),

health as (
    select
        ds.device_id,
        ds.reading_date,
        d.device_type,
        d.location,
        d.zone,
        d.status,
        d.maintenance_due,
        ds.avg_temperature,
        ds.max_temperature,
        ds.avg_vibration,
        ds.max_vibration,
        ds.avg_pressure,
        ds.avg_power_usage,
        ds.reading_count,
        coalesce(la.alert_count, 0) as alert_count,
        la.latest_alert_severity,
        ds.reading_date as last_reading,

        -- Health score: start at 100, subtract penalty points
        greatest(0, least(100,
            100
            -- High temperature penalty: -20 if max temp > 85, -10 if > 70
            - if(ds.max_temperature > 85, 20, if(ds.max_temperature > 70, 10, 0))
            -- High vibration penalty: -25 if max vibration > 10, -10 if > 5
            - if(ds.max_vibration > 10, 25, if(ds.max_vibration > 5, 10, 0))
            -- Pressure anomaly penalty: -15 if avg pressure outside 1-5 range
            - if(ds.avg_pressure < 1 or ds.avg_pressure > 5, 15, 0)
            -- High power usage penalty: -10 if avg power > 50
            - if(ds.avg_power_usage > 50, 10, 0)
            -- Maintenance overdue penalty: -15
            - if(d.maintenance_due = 1, 15, 0)
            -- Critical alert penalty: -15 for critical, -5 for warning
            - if(la.latest_alert_severity = 'critical', 15,
                if(la.latest_alert_severity = 'warning', 5, 0))
        )) as health_score

    from daily_stats as ds
    inner join devices as d
        on ds.device_id = d.device_id
    left join latest_alerts as la
        on ds.device_id = la.device_id
)

select * from health
