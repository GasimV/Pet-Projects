"""
FactoryPulse IoT Sensor Simulator
==================================
Continuously generates realistic factory telemetry and publishes to Kafka.
Also periodically publishes synthetic incident reports.
"""

import json
import logging
import os
import random
import time
import uuid
from datetime import datetime, timezone

from kafka import KafkaProducer

# ---------------------------------------------------------------------------
#  Configuration
# ---------------------------------------------------------------------------
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")
KAFKA_TOPIC_TELEMETRY = os.getenv("KAFKA_TOPIC_TELEMETRY", "factory.telemetry.raw")
KAFKA_TOPIC_INCIDENTS = os.getenv("KAFKA_TOPIC_INCIDENTS", "factory.incidents")
DEVICE_COUNT = int(os.getenv("SIMULATOR_DEVICE_COUNT", "10"))
INTERVAL_MS = int(os.getenv("SIMULATOR_INTERVAL_MS", "2000"))
ANOMALY_RATE = float(os.getenv("SIMULATOR_ANOMALY_RATE", "0.05"))

# Incident publishing interval (seconds)
INCIDENT_INTERVAL_S = 300  # every 5 minutes

# ---------------------------------------------------------------------------
#  Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("sensor_stream")

# ---------------------------------------------------------------------------
#  Device types and their typical characteristics
# ---------------------------------------------------------------------------
DEVICE_TYPES = ["CNC_Mill", "Hydraulic_Press", "Conveyor", "Compressor", "Welding_Robot"]
LOCATIONS = ["Zone_A", "Zone_B", "Zone_C", "Zone_D"]

ERROR_CODES = [
    "ERR_OVERHEAT",
    "ERR_VIBRATION",
    "ERR_PRESSURE",
    "ERR_POWER_SURGE",
    "ERR_MOTOR_STALL",
    "ERR_BEARING_WEAR",
]

# Incident templates — used to generate realistic factory incident descriptions
INCIDENT_TEMPLATES = [
    {
        "type": "overheat",
        "descriptions": [
            "Temperature sensor on {device_id} ({device_type}) in {location} exceeded safe threshold — "
            "recorded {temp:.1f}°C. Cooling system inspection initiated.",
            "Thermal alarm triggered for {device_id} in {location}. "
            "Peak temperature reached {temp:.1f}°C during high-load cycle on {device_type}.",
        ],
        "resolutions": [
            "Replaced clogged coolant filter. Temperature returned to nominal range within 15 minutes.",
            "Reduced feed rate by 20% and cleaned heat exchanger fins. Monitoring for recurrence.",
            "Thermal paste on spindle motor reapplied. Unit cleared for production after 30-min cool-down.",
        ],
    },
    {
        "type": "vibration",
        "descriptions": [
            "Abnormal vibration detected on {device_id} ({device_type}) in {location} — "
            "{vib:.2f} mm/s RMS, exceeding 4.0 mm/s limit.",
            "Vibration spike on {device_id} at {location}. "
            "Amplitude measured at {vib:.2f} mm/s on {device_type} drive axis.",
        ],
        "resolutions": [
            "Bearing on main shaft replaced. Post-maintenance vibration measured at 0.45 mm/s.",
            "Coupling alignment corrected and bolts re-torqued. Vibration now within spec.",
            "Loose mounting bolts tightened on base plate. Scheduled follow-up in 48 hours.",
        ],
    },
    {
        "type": "pressure",
        "descriptions": [
            "Hydraulic pressure drop on {device_id} ({device_type}) in {location} — "
            "system pressure fell to {press:.0f} bar (minimum 100 bar required).",
            "Pressure anomaly on {device_id} at {location}. "
            "Gauge reading {press:.0f} bar on {device_type}, outside nominal 100-200 bar window.",
        ],
        "resolutions": [
            "Hydraulic line leak at fitting #7 sealed. System re-pressurized to 160 bar.",
            "Pressure relief valve recalibrated. System holding steady at 150 bar under load.",
            "Replaced worn piston seal in hydraulic cylinder. Pressure test passed at 180 bar.",
        ],
    },
    {
        "type": "power",
        "descriptions": [
            "Power consumption spike on {device_id} ({device_type}) in {location} — "
            "drew {power:.1f} kW, 40% above normal operating range.",
            "Electrical fault indicator on {device_id} at {location}. "
            "{device_type} pulling {power:.1f} kW, suspected motor winding issue.",
        ],
        "resolutions": [
            "VFD drive parameters reconfigured. Power draw returned to 65 kW nominal.",
            "Replaced degraded capacitor bank on motor starter. Current draw normalized.",
            "Cleaned and re-seated contactor connections. Power monitoring shows stable readings.",
        ],
    },
    {
        "type": "general",
        "descriptions": [
            "Unplanned stoppage on {device_id} ({device_type}) in {location}. "
            "Operator reported unusual noise followed by automatic shutdown.",
            "Safety interlock activated on {device_id} at {location}. "
            "{device_type} halted mid-cycle; diagnostics in progress.",
        ],
        "resolutions": [
            "Foreign object removed from conveyor track. Full inspection completed before restart.",
            "Safety sensor recalibrated after false trigger. Root cause: dust accumulation on optics.",
            "Emergency stop caused by loose wire in control panel. Wiring harness secured and tested.",
        ],
    },
]


# ---------------------------------------------------------------------------
#  Device fleet setup
# ---------------------------------------------------------------------------
def build_device_fleet(count: int) -> list[dict]:
    """Create a fleet of virtual IoT devices with random baselines."""
    devices = []
    for i in range(count):
        device_type = DEVICE_TYPES[i % len(DEVICE_TYPES)]
        location = LOCATIONS[i % len(LOCATIONS)]
        device = {
            "device_id": f"DEV-{i + 1:04d}",
            "device_type": device_type,
            "location": location,
            # Per-device baselines add realism — each device runs slightly differently
            "baseline": {
                "temperature": random.uniform(65.0, 75.0),
                "vibration": random.uniform(0.3, 0.7),
                "pressure": random.uniform(130.0, 170.0),
                "humidity": random.uniform(35.0, 45.0),
                "power_usage": random.uniform(30.0, 70.0),
                "rpm": random.uniform(1000, 2500),
            },
        }
        devices.append(device)
    return devices


# ---------------------------------------------------------------------------
#  Telemetry generation
# ---------------------------------------------------------------------------
def generate_telemetry(device: dict) -> dict:
    """
    Generate a single telemetry reading for a device.
    With probability ANOMALY_RATE, inject an anomaly.
    """
    base = device["baseline"]
    is_anomaly = random.random() < ANOMALY_RATE
    error_code = None

    if is_anomaly:
        anomaly_kind = random.choice(["overheat", "vibration", "pressure"])
        if anomaly_kind == "overheat":
            temperature = random.uniform(120.0, 160.0)
            vibration = base["vibration"] + random.uniform(-0.2, 0.3)
            pressure = base["pressure"] + random.uniform(-10, 10)
            error_code = "ERR_OVERHEAT"
        elif anomaly_kind == "vibration":
            temperature = base["temperature"] + random.uniform(-3, 5)
            vibration = random.uniform(5.0, 12.0)
            pressure = base["pressure"] + random.uniform(-10, 10)
            error_code = "ERR_VIBRATION"
        else:  # pressure
            temperature = base["temperature"] + random.uniform(-3, 5)
            vibration = base["vibration"] + random.uniform(-0.2, 0.3)
            pressure = random.uniform(250.0, 350.0)
            error_code = "ERR_PRESSURE"
    else:
        temperature = base["temperature"] + random.uniform(-10, 10)  # ~60-80
        vibration = base["vibration"] + random.uniform(-0.2, 0.3)  # ~0.1-1.0
        pressure = base["pressure"] + random.uniform(-30, 30)       # ~100-200
        vibration = max(0.1, vibration)

    # Fields that are always generated normally
    humidity = base["humidity"] + random.uniform(-5, 5)         # ~30-50
    power_usage = base["power_usage"] + random.uniform(-20, 30) # ~10-100
    rpm = base["rpm"] + random.uniform(-500, 500)               # ~500-3000

    # Clamp to reasonable physical minimums
    humidity = max(10.0, humidity)
    power_usage = max(10.0, power_usage)
    rpm = max(500.0, rpm)

    return {
        "event_id": str(uuid.uuid4()),
        "device_id": device["device_id"],
        "device_type": device["device_type"],
        "location": device["location"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "temperature": round(temperature, 2),
        "vibration": round(vibration, 4),
        "pressure": round(pressure, 2),
        "humidity": round(humidity, 2),
        "power_usage": round(power_usage, 2),
        "rpm": round(rpm, 1),
        "error_code": error_code,
    }


# ---------------------------------------------------------------------------
#  Incident generation
# ---------------------------------------------------------------------------
def generate_incident(device: dict) -> dict:
    """Generate a realistic factory incident event."""
    template = random.choice(INCIDENT_TEMPLATES)
    fmt_kwargs = {
        "device_id": device["device_id"],
        "device_type": device["device_type"],
        "location": device["location"],
        "temp": random.uniform(125.0, 155.0),
        "vib": random.uniform(5.0, 11.0),
        "press": random.uniform(50.0, 90.0),
        "power": random.uniform(110.0, 180.0),
    }
    description = random.choice(template["descriptions"]).format(**fmt_kwargs)
    resolution = random.choice(template["resolutions"])

    return {
        "incident_id": str(uuid.uuid4()),
        "device_id": device["device_id"],
        "device_type": device["device_type"],
        "location": device["location"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "incident_type": template["type"],
        "description": description,
        "resolution": resolution,
        "severity": random.choice(["low", "medium", "high", "critical"]),
    }


# ---------------------------------------------------------------------------
#  Kafka producer setup
# ---------------------------------------------------------------------------
def create_producer(retries: int = 30, delay: int = 5) -> KafkaProducer:
    """Create a KafkaProducer, retrying until the broker is available."""
    for attempt in range(1, retries + 1):
        try:
            producer = KafkaProducer(
                bootstrap_servers=KAFKA_BROKER,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                key_serializer=lambda k: k.encode("utf-8") if k else None,
                acks="all",
                retries=3,
                linger_ms=50,
            )
            logger.info("Connected to Kafka broker at %s", KAFKA_BROKER)
            return producer
        except Exception as exc:
            logger.warning(
                "Kafka connection attempt %d/%d failed: %s — retrying in %ds",
                attempt,
                retries,
                exc,
                delay,
            )
            time.sleep(delay)
    raise RuntimeError(f"Could not connect to Kafka at {KAFKA_BROKER} after {retries} attempts")


# ---------------------------------------------------------------------------
#  Main loop
# ---------------------------------------------------------------------------
def main() -> None:
    logger.info("=== FactoryPulse IoT Simulator starting ===")
    logger.info(
        "Config: %d devices | interval=%dms | anomaly_rate=%.2f | telemetry_topic=%s | incidents_topic=%s",
        DEVICE_COUNT,
        INTERVAL_MS,
        ANOMALY_RATE,
        KAFKA_TOPIC_TELEMETRY,
        KAFKA_TOPIC_INCIDENTS,
    )

    fleet = build_device_fleet(DEVICE_COUNT)
    logger.info("Device fleet initialised:")
    for d in fleet:
        logger.info("  %s  %-16s  %s", d["device_id"], d["device_type"], d["location"])

    producer = create_producer()

    interval_s = INTERVAL_MS / 1000.0
    last_incident_time = time.monotonic()
    cycle = 0

    try:
        while True:
            cycle += 1
            now = time.monotonic()

            # --- Telemetry ---
            for device in fleet:
                reading = generate_telemetry(device)
                producer.send(
                    KAFKA_TOPIC_TELEMETRY,
                    key=device["device_id"],
                    value=reading,
                )
                if reading["error_code"]:
                    logger.warning(
                        "ANOMALY  %s  %s  temp=%.1f  vib=%.3f  press=%.1f  err=%s",
                        reading["device_id"],
                        reading["location"],
                        reading["temperature"],
                        reading["vibration"],
                        reading["pressure"],
                        reading["error_code"],
                    )

            if cycle % 50 == 0:
                logger.info(
                    "Cycle %d — sent %d telemetry messages to [%s]",
                    cycle,
                    len(fleet),
                    KAFKA_TOPIC_TELEMETRY,
                )

            # --- Incidents (every 5 minutes) ---
            if now - last_incident_time >= INCIDENT_INTERVAL_S:
                device = random.choice(fleet)
                incident = generate_incident(device)
                producer.send(
                    KAFKA_TOPIC_INCIDENTS,
                    key=device["device_id"],
                    value=incident,
                )
                logger.info(
                    "INCIDENT  %s  %s  type=%s  severity=%s — %s",
                    incident["device_id"],
                    incident["location"],
                    incident["incident_type"],
                    incident["severity"],
                    incident["description"][:120],
                )
                last_incident_time = now

            producer.flush()
            time.sleep(interval_s)

    except KeyboardInterrupt:
        logger.info("Shutdown requested — flushing remaining messages")
    finally:
        producer.flush(timeout=10)
        producer.close()
        logger.info("Producer closed. Goodbye.")


if __name__ == "__main__":
    main()
