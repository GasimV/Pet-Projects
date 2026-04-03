{{ config(materialized='view') }}

select
    cast(alert_id as String)       as alert_id,
    cast(device_id as String)      as device_id,
    cast(alert_type as String)     as alert_type,
    cast(severity as String)       as severity,
    cast(message as String)        as message,
    cast(metric_name as String)    as metric_name,
    cast(metric_value as Float64)  as metric_value,
    cast(threshold as Float64)     as threshold,
    cast(timestamp as DateTime64(3)) as alert_timestamp,
    cast(resolved as UInt8)        as resolved,
    ingested_at
from {{ source('factory_pulse', 'raw_alerts') }}
