{{ config(materialized='view') }}

select
    device_id,
    toDate(reading_hour)  as reading_date,
    avg(temperature)      as avg_temperature,
    max(temperature)      as max_temperature,
    avg(vibration)        as avg_vibration,
    max(vibration)        as max_vibration,
    avg(pressure)         as avg_pressure,
    avg(power_usage)      as avg_power_usage,
    sum(reading_count)    as reading_count
from {{ ref('int_device_hourly_stats') }}
group by
    device_id,
    toDate(reading_hour)
