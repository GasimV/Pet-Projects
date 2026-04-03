{{ config(materialized='view') }}

select
    device_id,
    reading_hour,
    avg(temperature)   as avg_temperature,
    max(temperature)   as max_temperature,
    avg(vibration)     as avg_vibration,
    max(vibration)     as max_vibration,
    avg(pressure)      as avg_pressure,
    avg(power_usage)   as avg_power_usage,
    count()            as reading_count
from {{ ref('stg_telemetry') }}
group by
    device_id,
    reading_hour
