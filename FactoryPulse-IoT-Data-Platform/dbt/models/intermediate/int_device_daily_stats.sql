{{ config(materialized='view') }}

select
    device_id,
    toDate(reading_hour)  as reading_date,
    avg(avg_temperature)  as avg_temperature,
    max(max_temperature)  as max_temperature,
    avg(avg_vibration)    as avg_vibration,
    max(max_vibration)    as max_vibration,
    avg(avg_pressure)     as avg_pressure,
    avg(avg_power_usage)  as avg_power_usage,
    sum(reading_count)    as reading_count
from {{ ref('int_device_hourly_stats') }}
group by
    device_id,
    toDate(reading_hour)
