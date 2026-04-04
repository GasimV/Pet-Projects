{{ config(materialized='view') }}

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
    greatest(0, least(100,
        100
        - if(ds.max_temperature > 85, 20, if(ds.max_temperature > 70, 10, 0))
        - if(ds.max_vibration > 10, 25, if(ds.max_vibration > 5, 10, 0))
        - if(ds.avg_pressure < 1 or ds.avg_pressure > 5, 15, 0)
        - if(ds.avg_power_usage > 50, 10, 0)
        - if(d.maintenance_due = 1, 15, 0)
        - if(upper(coalesce(la.latest_alert_severity, '')) = 'CRITICAL', 15,
            if(upper(coalesce(la.latest_alert_severity, '')) = 'WARNING', 5, 0))
    )) as health_score
from {{ ref('int_device_daily_stats') }} as ds
inner join {{ ref('dim_devices') }} as d
    on ds.device_id = d.device_id
left join (
    select
        device_id,
        argMax(severity, alert_timestamp) as latest_alert_severity,
        count() as alert_count
    from {{ ref('stg_alerts') }}
    group by device_id
) as la
    on ds.device_id = la.device_id
