{{ config(materialized='view') }}

select
    cast(event_id as String)       as event_id,
    cast(device_id as String)      as device_id,
    cast(device_type as String)    as device_type,
    cast(location as String)       as location,
    cast(timestamp as DateTime64(3)) as event_timestamp,
    cast(temperature as Float64)   as temperature,
    cast(vibration as Float64)     as vibration,
    cast(pressure as Float64)      as pressure,
    cast(humidity as Float64)      as humidity,
    cast(power_usage as Float64)   as power_usage,
    cast(rpm as Float64)           as rpm,
    error_code,
    ingested_at,
    toStartOfHour(timestamp)       as reading_hour
from {{ source('factory_pulse', 'raw_telemetry') }}
