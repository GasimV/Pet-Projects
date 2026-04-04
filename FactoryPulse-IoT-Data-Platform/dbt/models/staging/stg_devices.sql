{{ config(materialized='view') }}

select
    cast(device_id as String)                   as device_id,
    cast(device_type as String)                 as device_type,
    cast(manufacturer as String)                as manufacturer,
    cast(model as String)                       as model,
    cast(install_date as Date)                  as install_date,
    cast(location as String)                    as location,
    cast(zone as String)                        as zone,
    cast(maintenance_interval_days as UInt16)   as maintenance_interval_days,
    cast(last_maintenance_date as Date)         as last_maintenance_date,
    cast(status as String)                      as status,
    updated_at,
    dateDiff('day', last_maintenance_date, today()) as days_since_maintenance
from {{ source('factory_pulse', 'raw_devices') }} FINAL
