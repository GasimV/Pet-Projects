"""
FactoryPulse Batch Reference Data Generator
=============================================
Generates device reference CSVs, historical telemetry Parquet files,
and incident-manual JSON documents, then uploads them all to MinIO.
Designed to run once (e.g. via ``docker compose run simulator python batch_reference_gen.py``).
"""

import csv
import io
import json
import logging
import os
import random
import time
import uuid
from datetime import datetime, timedelta, timezone

import boto3
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from faker import Faker

# ---------------------------------------------------------------------------
#  Configuration
# ---------------------------------------------------------------------------
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://minio:9000")
MINIO_BUCKET = os.getenv("MINIO_BUCKET_RAW", "factory-raw")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "minioadmin")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "minioadmin")
DEVICE_COUNT = int(os.getenv("SIMULATOR_DEVICE_COUNT", "10"))
HISTORICAL_ROWS = 1000

# ---------------------------------------------------------------------------
#  Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("batch_reference_gen")

fake = Faker()
Faker.seed(42)
random.seed(42)

# ---------------------------------------------------------------------------
#  Constants
# ---------------------------------------------------------------------------
DEVICE_TYPES = ["CNC_Mill", "Hydraulic_Press", "Conveyor", "Compressor", "Welding_Robot"]
LOCATIONS = ["Zone_A", "Zone_B", "Zone_C", "Zone_D"]
MANUFACTURERS = {
    "CNC_Mill": [("Haas Automation", "VF-2SS"), ("DMG Mori", "CMX 600 V"), ("Mazak", "VCN-530C")],
    "Hydraulic_Press": [("Schuler", "MSD 200"), ("Beckwood", "4P-200"), ("Macrodyne", "HP-500")],
    "Conveyor": [("Hytrol", "EZLogic"), ("Dorner", "3200 Series"), ("FlexLink", "XH")],
    "Compressor": [("Atlas Copco", "GA 90+"), ("Ingersoll Rand", "R-Series 110"), ("Kaeser", "CSG-2")],
    "Welding_Robot": [("FANUC", "Arc Mate 120iD"), ("ABB", "IRB 1520ID"), ("KUKA", "KR CYBERTECH")],
}
STATUSES = ["active", "active", "active", "active", "maintenance", "decommissioned"]


# ---------------------------------------------------------------------------
#  S3 / MinIO client
# ---------------------------------------------------------------------------
def get_s3_client(retries: int = 15, delay: int = 4):
    """Create a boto3 S3 client pointing at MinIO, with retry logic."""
    for attempt in range(1, retries + 1):
        try:
            client = boto3.client(
                "s3",
                endpoint_url=MINIO_ENDPOINT,
                aws_access_key_id=AWS_ACCESS_KEY_ID,
                aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                region_name="us-east-1",
            )
            # Verify connectivity by listing buckets
            client.list_buckets()
            logger.info("Connected to MinIO at %s", MINIO_ENDPOINT)
            return client
        except Exception as exc:
            logger.warning(
                "MinIO connection attempt %d/%d failed: %s — retrying in %ds",
                attempt, retries, exc, delay,
            )
            time.sleep(delay)
    raise RuntimeError(f"Could not connect to MinIO at {MINIO_ENDPOINT} after {retries} attempts")


def ensure_bucket(s3, bucket: str) -> None:
    """Create the bucket if it does not already exist."""
    try:
        s3.head_bucket(Bucket=bucket)
        logger.info("Bucket '%s' already exists", bucket)
    except Exception:
        try:
            s3.create_bucket(Bucket=bucket)
            logger.info("Created bucket '%s'", bucket)
        except Exception as exc:
            # Bucket may have been created concurrently by minio-init
            logger.warning("Bucket creation note: %s", exc)


# ---------------------------------------------------------------------------
#  1. Device reference CSV
# ---------------------------------------------------------------------------
def generate_devices_csv() -> tuple[str, list[dict]]:
    """Return CSV string and list of device dicts."""
    devices = []
    now = datetime.now(timezone.utc)

    for i in range(DEVICE_COUNT):
        device_type = DEVICE_TYPES[i % len(DEVICE_TYPES)]
        location = LOCATIONS[i % len(LOCATIONS)]
        manufacturer, model = random.choice(MANUFACTURERS[device_type])
        install_date = fake.date_between(start_date="-5y", end_date="-1y")
        maintenance_interval = random.choice([30, 60, 90, 180])
        last_maintenance = fake.date_between(
            start_date=install_date,
            end_date=now.date(),
        )
        status = random.choice(STATUSES)

        device = {
            "device_id": f"DEV-{i + 1:04d}",
            "device_type": device_type,
            "manufacturer": manufacturer,
            "model": model,
            "install_date": install_date.isoformat(),
            "location": location,
            "zone": location,
            "maintenance_interval_days": maintenance_interval,
            "last_maintenance_date": last_maintenance.isoformat(),
            "status": status,
        }
        devices.append(device)

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(devices[0].keys()))
    writer.writeheader()
    writer.writerows(devices)
    return buf.getvalue(), devices


# ---------------------------------------------------------------------------
#  2. Historical telemetry Parquet
# ---------------------------------------------------------------------------
def generate_historical_telemetry(devices: list[dict], n_rows: int = HISTORICAL_ROWS) -> bytes:
    """Generate n_rows of historical telemetry and return Parquet bytes."""
    rows = []
    base_time = datetime.now(timezone.utc) - timedelta(days=7)

    for i in range(n_rows):
        device = random.choice(devices)
        ts = base_time + timedelta(seconds=i * 30)
        is_anomaly = random.random() < 0.05
        error_code = None

        if is_anomaly:
            temperature = round(random.uniform(120.0, 160.0), 2)
            vibration = round(random.uniform(5.0, 12.0), 4)
            pressure = round(random.uniform(250.0, 350.0), 2)
            error_code = random.choice(["ERR_OVERHEAT", "ERR_VIBRATION", "ERR_PRESSURE"])
        else:
            temperature = round(random.uniform(60.0, 80.0), 2)
            vibration = round(random.uniform(0.1, 1.0), 4)
            pressure = round(random.uniform(100.0, 200.0), 2)

        rows.append({
            "event_id": str(uuid.uuid4()),
            "device_id": device["device_id"],
            "device_type": device["device_type"],
            "location": device["location"],
            "timestamp": ts.isoformat(),
            "temperature": temperature,
            "vibration": vibration,
            "pressure": pressure,
            "humidity": round(random.uniform(30.0, 50.0), 2),
            "power_usage": round(random.uniform(10.0, 100.0), 2),
            "rpm": round(random.uniform(500.0, 3000.0), 1),
            "error_code": error_code,
        })

    df = pd.DataFrame(rows)
    table = pa.Table.from_pandas(df)
    buf = io.BytesIO()
    pq.write_table(table, buf)
    return buf.getvalue()


# ---------------------------------------------------------------------------
#  3. Incident manuals JSON (for vector search / RAG)
# ---------------------------------------------------------------------------
def generate_incident_manuals(count: int = 20) -> str:
    """Generate sample factory maintenance manual entries as JSON."""
    procedures = [
        {
            "title": "CNC Mill Spindle Overheating — Troubleshooting Guide",
            "content": (
                "When spindle temperature exceeds 110°C, immediately reduce feed rate to 50%. "
                "Inspect coolant flow rate at the spindle nose — minimum 15 L/min required. "
                "Check coolant filter (part #CF-200) for blockage; replace every 500 operating hours. "
                "Verify thermal paste application on spindle motor mount. If temperature persists "
                "above 100°C after coolant system check, inspect spindle bearings for wear using "
                "vibration analysis (threshold: 2.5 mm/s RMS). Schedule bearing replacement if "
                "vibration exceeds threshold for 3 consecutive readings."
            ),
        },
        {
            "title": "Hydraulic Press Emergency Pressure Loss Procedure",
            "content": (
                "If system pressure drops below 90 bar during operation, initiate emergency stop. "
                "Visually inspect all hydraulic lines for leaks, starting at cylinder connections. "
                "Check accumulator pre-charge pressure — should be 60% of working pressure. "
                "Inspect pressure relief valve (PRV) setting; factory default is 210 bar. "
                "If PRV is venting prematurely, recalibrate or replace. Verify hydraulic fluid "
                "level in reservoir — minimum 80% fill line. Test pump output with flow meter; "
                "minimum 40 L/min at 150 bar. Document all findings in maintenance log MNT-HYD-001."
            ),
        },
        {
            "title": "Conveyor Belt Tracking and Alignment",
            "content": (
                "Misaligned conveyor belts cause edge wear and product spillage. To correct: "
                "1) Stop conveyor and lock out energy sources. 2) Check belt tension using "
                "tension gauge — target 3-5 kN depending on belt width. 3) Adjust tracking "
                "idlers in 1/4-turn increments, allowing 3 full belt revolutions between adjustments. "
                "4) Verify crowned pulleys are free of debris. 5) Check belt splice integrity. "
                "Maximum allowable belt wander: 25 mm from center. Log adjustments in "
                "maintenance record CVR-TRK-001."
            ),
        },
        {
            "title": "Compressor Vibration Analysis and Bearing Replacement",
            "content": (
                "Perform vibration analysis monthly on all compressor units. Mount accelerometer "
                "on drive-end bearing housing (horizontal, vertical, and axial). Alert thresholds: "
                "2.8 mm/s (warning), 4.5 mm/s (alarm), 7.1 mm/s (shutdown). When alarm threshold "
                "is exceeded: order replacement bearings (SKF 6310-2RS or equivalent), schedule "
                "downtime within 72 hours. Bearing replacement procedure: drain oil, remove coupling "
                "guard, extract bearing with hydraulic puller, install new bearing with induction "
                "heater (110°C), re-grease with Mobil SHC 100, realign coupling to 0.05 mm TIR."
            ),
        },
        {
            "title": "Welding Robot Arc Fault Troubleshooting",
            "content": (
                "Common arc faults: porosity, spatter, undercut, incomplete fusion. "
                "For excessive spatter: verify wire feed speed (typical 3-8 m/min for MIG), "
                "check contact tip wear (replace every 8 hours of arc-on time), ensure gas "
                "flow rate 15-20 L/min. For porosity: inspect gas hose for leaks, verify "
                "shielding gas composition (75% Ar / 25% CO2 for mild steel), check for drafts "
                "near weld zone. For undercut: reduce travel speed by 10%, adjust work angle. "
                "Log all parameter changes in weld procedure specification WPS-FAC-001."
            ),
        },
        {
            "title": "Preventive Maintenance Schedule — CNC Mill",
            "content": (
                "Daily: check coolant level, clean chip tray, verify axis home positions. "
                "Weekly: lubricate linear guides (ISO VG 68 oil), inspect way covers, check "
                "spindle runout (<0.005 mm). Monthly: replace spindle air filter, calibrate "
                "tool length sensor, test emergency stop circuit. Quarterly: change hydraulic "
                "oil, inspect ball screws for backlash (<0.02 mm), calibrate axes with laser "
                "interferometer. Annual: full geometric alignment check, replace all seals, "
                "inspect electrical cabinet for loose connections. Reference: PM-CNC-001."
            ),
        },
        {
            "title": "Emergency Shutdown Procedure — All Equipment",
            "content": (
                "In case of emergency: 1) Press nearest E-stop button (red mushroom head). "
                "2) Evacuate immediate area if chemical or fire hazard. 3) Notify shift supervisor. "
                "4) Call plant emergency line ext. 5555. 5) Do NOT attempt restart until area is "
                "cleared by safety officer. Post-shutdown checklist: verify all axes at zero speed, "
                "check for trapped personnel, inspect for fluid leaks, document event in "
                "EHS system within 1 hour. Reference: SOP-EMG-001."
            ),
        },
        {
            "title": "Hydraulic Fluid Contamination Testing",
            "content": (
                "Test hydraulic fluid monthly using particle counter. Target cleanliness: "
                "ISO 4406 code 17/15/12 or better. Sample from live line (not reservoir) "
                "using minimess sampling port. If contamination exceeds target: install or "
                "replace 10-micron return line filter, check breather cap, inspect seals on "
                "all cylinders. Water content must be below 0.1% — test with Karl Fischer "
                "titration. Fluid replacement interval: 2000 operating hours or when acid "
                "number exceeds 2.0 mg KOH/g. Use only approved fluid: Shell Tellus S2 MX 46."
            ),
        },
        {
            "title": "Conveyor Motor Overload — Root Cause Analysis",
            "content": (
                "Motor overload trips indicate excessive load or mechanical binding. "
                "Diagnostic steps: 1) Measure motor current with clamp meter — compare to "
                "nameplate FLA. 2) Check belt tension — overtension increases load by 15-30%. "
                "3) Inspect idler bearings for seizure (spin by hand). 4) Verify product load "
                "does not exceed belt rating (kg/m). 5) Check gearbox oil level and condition. "
                "6) Measure supply voltage — low voltage increases current draw. If motor "
                "winding resistance is unbalanced (>5% between phases), schedule motor rewind. "
                "Reference: TRB-CVR-MOTOR-001."
            ),
        },
        {
            "title": "Welding Robot TCP Calibration Procedure",
            "content": (
                "Tool Center Point (TCP) calibration must be performed after any torch "
                "replacement or collision. Use 4-point method: approach fixed reference point "
                "from 4 different orientations. Maximum allowable TCP error: 0.5 mm. "
                "Procedure: 1) Mount calibration spike on torch. 2) Jog to reference point. "
                "3) Record position from 4 orientations (0°, 90°, 180°, 270° rotation). "
                "4) Execute automatic TCP calculation. 5) Verify by approaching reference "
                "from 2 additional test angles. Document calibration in robot maintenance log."
            ),
        },
        {
            "title": "Compressed Air System Leak Detection",
            "content": (
                "Air leaks waste 20-30% of compressor output in typical plants. Detection "
                "methods: ultrasonic leak detector (preferred), soapy water on joints (manual). "
                "Survey all fittings, hoses, FRLs, and quick-connect couplings quarterly. "
                "Tag each leak with repair priority (red = >5 CFM, yellow = 1-5 CFM, "
                "green = <1 CFM). Common leak points: threaded fittings (apply PTFE tape), "
                "worn quick-connects (replace O-ring or coupling), cracked hoses (replace "
                "entire section). Target: system pressure drop <0.5 bar in 15-minute static test."
            ),
        },
        {
            "title": "CNC Mill Tool Breakage Prevention",
            "content": (
                "Tool breakage causes scrap, rework, and potential machine damage. Prevention: "
                "1) Monitor tool wear with in-process measurement (laser or touch probe). "
                "2) Set conservative tool life limits — replace at 80% of empirical life. "
                "3) Verify correct feeds and speeds for material (refer to Machining Data "
                "Handbook). 4) Ensure adequate coolant pressure at tool tip (20+ bar for "
                "deep-hole drilling). 5) Use tool breakage detection sensor post-tool-change. "
                "6) Inspect collet and tool holder taper for wear — replace if TIR >0.01 mm. "
                "Log all breakage events for trend analysis in MES system."
            ),
        },
        {
            "title": "Hydraulic Cylinder Seal Replacement",
            "content": (
                "Symptoms of seal failure: external fluid leak, slow cylinder drift under load, "
                "spongy operation. Replacement procedure: 1) Depressurize system and lock out. "
                "2) Disconnect hydraulic lines and cap immediately. 3) Remove cylinder from "
                "machine using overhead crane (min 2-ton rated). 4) Disassemble on clean "
                "bench — note seal orientation and order. 5) Inspect bore for scoring (max "
                "Ra 0.4 μm). 6) Install new seal kit (use correct material: NBR for mineral "
                "oil, FKM for synthetic). 7) Lubricate seals with system fluid before assembly. "
                "8) Pressure test to 1.5x working pressure for 15 minutes. Reference: MNT-HYD-SEAL-001."
            ),
        },
        {
            "title": "Electrical Cabinet Thermal Management",
            "content": (
                "Cabinet internal temperature must stay below 40°C for reliable PLC and VFD "
                "operation. Monitoring: install temperature sensor (PT100 or thermocouple) "
                "connected to PLC analog input. Alarm at 38°C, shutdown at 45°C. Cooling "
                "methods: filtered fan (clean filter monthly), cabinet air conditioner (for "
                "harsh environments), or vortex cooler (ATEX zones). Ensure positive pressure "
                "inside cabinet to prevent dust ingress. Inspect door gaskets annually — "
                "replace if cracked or compressed. Check all ventilation openings are unobstructed."
            ),
        },
        {
            "title": "Conveyor Belt Splicing — Hot Vulcanization",
            "content": (
                "Hot vulcanization produces the strongest splice (90%+ of belt rated strength). "
                "Equipment: vulcanizing press, splice rubber, bonding cement, buffer tool. "
                "Procedure: 1) Cut belt ends square. 2) Mark and cut bias steps (number of "
                "steps = number of plies). 3) Buff exposed surfaces to remove oxidation. "
                "4) Apply bonding cement, allow to tack dry. 5) Lay splice rubber between "
                "steps. 6) Close press and cure at 145°C for 20-30 min depending on belt "
                "thickness. 7) Trim excess rubber. 8) Test splice by running belt under load "
                "for 1 hour. Maximum elongation at splice: 2%. Reference: CVR-SPLICE-001."
            ),
        },
        {
            "title": "Compressor Oil Analysis Program",
            "content": (
                "Collect oil samples every 500 operating hours from the sample valve downstream "
                "of the oil filter. Send to certified lab for: viscosity (ISO 4), particle count "
                "(ISO 4406), water content (Karl Fischer), acid number (ASTM D974), and wear "
                "metal analysis (ICP spectroscopy). Action limits: viscosity change >10%, "
                "iron >50 ppm, copper >30 ppm, silicon >20 ppm (indicates air filter bypass). "
                "Change oil if any parameter exceeds limits. Use only OEM-approved lubricant — "
                "mixing brands can cause foaming and additive depletion. Record all results in "
                "oil analysis tracking spreadsheet OIL-COMP-001."
            ),
        },
        {
            "title": "Robot Safety System Inspection",
            "content": (
                "Inspect robot safety systems monthly per ISO 10218 and local regulations. "
                "Checklist: 1) Test all E-stop buttons — robot must halt within 0.5 seconds. "
                "2) Verify safety-rated monitored stop (SOS) function. 3) Test light curtains "
                "with test rod (14 mm diameter). 4) Check safety interlock switches on all "
                "access doors. 5) Verify reduced speed mode limits (250 mm/s max). 6) Test "
                "enabling device (3-position deadman switch). 7) Inspect floor markings and "
                "safety signage. 8) Review safety configuration checksum in robot controller. "
                "Document all tests in safety inspection log SAF-ROB-001."
            ),
        },
        {
            "title": "Power Quality Monitoring for CNC Equipment",
            "content": (
                "Poor power quality causes servo faults, tool path errors, and premature "
                "component failure. Install power quality analyzer at main panel feeding CNC "
                "machines. Monitor: voltage sags/swells (limit: ±10% of nominal), harmonics "
                "(THD <5% per IEEE 519), power factor (target >0.95), and transients. "
                "Common solutions: install active harmonic filter at VFD input, add line "
                "reactor (3-5% impedance), use isolation transformer for sensitive CNC controls. "
                "If voltage sags exceed 5 events/month, consider installing UPS or dynamic "
                "voltage restorer. Log all power events in PQ-MON-001."
            ),
        },
        {
            "title": "Hydraulic Press Die Alignment Verification",
            "content": (
                "Misaligned dies cause uneven part thickness, premature die wear, and potential "
                "press damage. Verification procedure: 1) Clean die surfaces and press bed. "
                "2) Install alignment pins in lower die. 3) Slowly close press to check pin "
                "engagement — must be free with no lateral force. 4) Measure parallelism "
                "between ram face and bed with dial indicator — max 0.05 mm across full stroke. "
                "5) Check die height setting matches die specification sheet. 6) Perform test "
                "press with soft material (lead or modeling clay) to verify uniform impression. "
                "7) Torque all T-slot bolts to specification. Reference: DIE-ALIGN-001."
            ),
        },
        {
            "title": "Factory Air Quality and Fume Extraction",
            "content": (
                "Welding fumes, cutting fluid mist, and metalworking dust require proper "
                "extraction. Minimum requirements: local exhaust ventilation (LEV) at each "
                "welding station (capture velocity 0.5-1.0 m/s at source), mist collectors "
                "on CNC machines (HEPA or electrostatic), and general ventilation providing "
                "6-10 air changes per hour. Monitor: particulate levels with DustTrak monitor "
                "(limit: 5 mg/m³ TWA for respirable dust), CO/NO2 levels near welding "
                "(limit: 25 ppm CO, 3 ppm NO2). Inspect and replace filters quarterly. "
                "Annual ductwork inspection for buildup. Reference: EHS-AIR-001."
            ),
        },
    ]

    # Return exactly `count` entries, cycling if necessary
    manuals = []
    for i in range(count):
        entry = procedures[i % len(procedures)].copy()
        entry["manual_id"] = str(uuid.uuid4())
        entry["category"] = random.choice([
            "maintenance", "troubleshooting", "safety", "calibration", "inspection",
        ])
        entry["equipment_types"] = [DEVICE_TYPES[i % len(DEVICE_TYPES)]]
        entry["last_updated"] = fake.date_between(start_date="-1y", end_date="today").isoformat()
        manuals.append(entry)

    return json.dumps(manuals, indent=2)


# ---------------------------------------------------------------------------
#  Upload helpers
# ---------------------------------------------------------------------------
def upload_string(s3, bucket: str, key: str, body: str, content_type: str = "text/plain") -> None:
    s3.put_object(Bucket=bucket, Key=key, Body=body.encode("utf-8"), ContentType=content_type)
    logger.info("Uploaded s3://%s/%s  (%d bytes)", bucket, key, len(body.encode("utf-8")))


def upload_bytes(s3, bucket: str, key: str, body: bytes, content_type: str = "application/octet-stream") -> None:
    s3.put_object(Bucket=bucket, Key=key, Body=body, ContentType=content_type)
    logger.info("Uploaded s3://%s/%s  (%d bytes)", bucket, key, len(body))


# ---------------------------------------------------------------------------
#  Main
# ---------------------------------------------------------------------------
def main() -> None:
    logger.info("=== FactoryPulse Batch Reference Data Generator ===")

    s3 = get_s3_client()
    ensure_bucket(s3, MINIO_BUCKET)

    # 1. Device reference CSV
    logger.info("Generating device reference CSV (%d devices)...", DEVICE_COUNT)
    csv_data, devices = generate_devices_csv()
    upload_string(s3, MINIO_BUCKET, "reference/devices.csv", csv_data, "text/csv")

    # 2. Historical telemetry Parquet
    logger.info("Generating historical telemetry Parquet (%d rows)...", HISTORICAL_ROWS)
    parquet_bytes = generate_historical_telemetry(devices, HISTORICAL_ROWS)
    upload_bytes(
        s3, MINIO_BUCKET,
        "telemetry/historical/telemetry_historical.parquet",
        parquet_bytes,
        "application/octet-stream",
    )

    # 3. Incident manuals JSON
    logger.info("Generating incident manuals JSON (20 entries)...")
    manuals_json = generate_incident_manuals(count=20)
    upload_string(
        s3, MINIO_BUCKET,
        "reference/incident_manuals.json",
        manuals_json,
        "application/json",
    )

    logger.info("=== Batch reference data generation complete ===")


if __name__ == "__main__":
    main()
