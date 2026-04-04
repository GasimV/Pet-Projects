"""
Great Expectations Data Quality Validation Script
===================================================
Validates FactoryPulse telemetry data in ClickHouse using programmatic GX API.

Run:  python ge_validate.py
"""

import os
import sys

import clickhouse_connect


def get_ch_client():
    return clickhouse_connect.get_client(
        host=os.environ.get("CLICKHOUSE_HOST", "clickhouse"),
        port=int(os.environ.get("CLICKHOUSE_PORT", 8123)),
        username=os.environ.get("CLICKHOUSE_USER", "default"),
        password=os.environ.get("CLICKHOUSE_PASSWORD", "clickhouse"),
        database=os.environ.get("CLICKHOUSE_DB", "factory_pulse"),
    )


# Define expectations as simple rule checks — avoids heavy GX dependency issues
# while still demonstrating data quality validation concepts.
EXPECTATIONS = [
    {
        "name": "device_id_not_null",
        "query": "SELECT count() FROM raw_telemetry WHERE device_id IS NULL OR device_id = ''",
        "expect": 0,
        "description": "All telemetry rows must have a device_id",
    },
    {
        "name": "timestamp_not_null",
        "query": "SELECT count() FROM raw_telemetry WHERE timestamp IS NULL",
        "expect": 0,
        "description": "All telemetry rows must have a timestamp",
    },
    {
        "name": "temperature_in_range",
        "query": "SELECT count() FROM raw_telemetry WHERE temperature < -40 OR temperature > 300",
        "expect": 0,
        "description": "Temperature must be between -40 and 300 °C",
    },
    {
        "name": "vibration_non_negative",
        "query": "SELECT count() FROM raw_telemetry WHERE vibration < 0",
        "expect": 0,
        "description": "Vibration must be non-negative",
    },
    {
        "name": "pressure_in_range",
        "query": "SELECT count() FROM raw_telemetry WHERE pressure < 0 OR pressure > 1000",
        "expect": 0,
        "description": "Pressure must be between 0 and 1000 bar",
    },
    {
        "name": "humidity_in_range",
        "query": "SELECT count() FROM raw_telemetry WHERE humidity < 0 OR humidity > 100",
        "expect": 0,
        "description": "Humidity must be between 0 and 100 %",
    },
    {
        "name": "power_usage_non_negative",
        "query": "SELECT count() FROM raw_telemetry WHERE power_usage < 0",
        "expect": 0,
        "description": "Power usage must be non-negative",
    },
    {
        "name": "rpm_non_negative",
        "query": "SELECT count() FROM raw_telemetry WHERE rpm < 0",
        "expect": 0,
        "description": "RPM must be non-negative",
    },
    {
        "name": "known_device_types",
        "query": (
            "SELECT count() FROM raw_telemetry "
            "WHERE device_type NOT IN "
            "('CNC_Mill','Hydraulic_Press','Conveyor','Compressor','Welding_Robot')"
        ),
        "expect": 0,
        "description": "Device type must be one of the known types",
    },
    {
        "name": "data_freshness",
        "query": (
            "SELECT if(max(timestamp) > now() - INTERVAL 1 HOUR, 0, 1) FROM raw_telemetry"
        ),
        "expect": 0,
        "description": "Most recent data must be less than 1 hour old",
    },
]


def main():
    print("=" * 60)
    print("  FactoryPulse — Data Quality Validation")
    print("=" * 60)

    client = get_ch_client()

    # Check if table has data
    count_result = client.query("SELECT count() FROM raw_telemetry")
    total_rows = count_result.result_rows[0][0]
    print(f"\n  Total rows in raw_telemetry: {total_rows}\n")

    if total_rows == 0:
        print("  No data to validate. Exiting.")
        return

    passed = 0
    failed = 0
    results = []

    for exp in EXPECTATIONS:
        try:
            result = client.query(exp["query"])
            violations = result.result_rows[0][0]
            success = violations == exp["expect"]

            status = "PASS" if success else "FAIL"
            icon = "✓" if success else "✗"

            if success:
                passed += 1
            else:
                failed += 1

            results.append(
                {
                    "name": exp["name"],
                    "status": status,
                    "violations": violations,
                    "description": exp["description"],
                }
            )

            print(f"  {icon} [{status}] {exp['name']}: {exp['description']}")
            if not success:
                print(f"           → Found {violations} violations (expected {exp['expect']})")

        except Exception as exc:
            failed += 1
            results.append(
                {
                    "name": exp["name"],
                    "status": "ERROR",
                    "violations": -1,
                    "description": str(exc),
                }
            )
            print(f"  ✗ [ERROR] {exp['name']}: {exc}")

    print(f"\n{'=' * 60}")
    print(f"  Results: {passed} passed, {failed} failed, {len(EXPECTATIONS)} total")
    print(f"  Score: {passed / len(EXPECTATIONS) * 100:.1f}%")
    print(f"{'=' * 60}")

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
