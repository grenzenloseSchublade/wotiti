import sqlite3
import os
import logging
import polars as pl
from datetime import datetime, timedelta
import random
import math

from db_helper import create_connection, create_main_table, check_user, create_events_table, check_project
import json
from utils import save_to_csv, PATH_TO_DATA

logger = logging.getLogger(__name__)

TIMESTAMP_FORMAT = "%d-%m-%Y %H:%M:%S"
DEFAULT_NUM_DAYS = 90
DEFAULT_NUM_USERS = 10

# ─── User Archetypes ────────────────────────────────────────────────────────
# Each archetype defines a distinct work style so that clustering, ANOVA, and
# regression analyses produce meaningful, distinguishable results.

ARCHETYPES = {
    "fruehaufsteher": {
        "label": "Frühaufsteher",
        "window_start": (6, 0),    # 06:00
        "window_end":   (14, 0),   # 14:00
        "daily_hours":  (6.5, 8.0),
        "block_min":    40,
        "block_max":    180,
        "switch_rate":  0.15,      # low — focused, few project switches
        "project_count": 2,
        "lunch_hour":   11,
    },
    "kernzeit": {
        "label": "Kernzeit-Arbeiter",
        "window_start": (9, 0),
        "window_end":   (17, 0),
        "daily_hours":  (7.0, 8.5),
        "block_min":    30,
        "block_max":    150,
        "switch_rate":  0.30,
        "project_count": 3,
        "lunch_hour":   12,
    },
    "spaetarbeiter": {
        "label": "Spätarbeiter",
        "window_start": (11, 0),
        "window_end":   (19, 30),
        "daily_hours":  (7.0, 9.0),
        "block_min":    20,
        "block_max":    90,
        "switch_rate":  0.50,      # high — many short blocks, frequent switches
        "project_count": 4,
        "lunch_hour":   14,
    },
    "teilzeit": {
        "label": "Teilzeit",
        "window_start": (8, 0),
        "window_end":   (13, 0),
        "daily_hours":  (3.5, 5.5),
        "block_min":    30,
        "block_max":    120,
        "switch_rate":  0.10,
        "project_count": 2,
        "lunch_hour":   None,      # no lunch — too short
    },
    "flexibel": {
        "label": "Flexibler Arbeiter",
        "window_start": (7, 0),    # varies ±90min per day
        "window_end":   (18, 0),
        "daily_hours":  (6.0, 9.0),
        "block_min":    15,
        "block_max":    100,
        "switch_rate":  0.60,      # very high — context switcher
        "project_count": 5,
        "lunch_hour":   12,
        "start_jitter_min": 90,    # unique: random start offset ±90min
    },
}


def _build_user_params(num_users=DEFAULT_NUM_USERS):
    """Build user parameters from archetypes with slight per-user variation."""
    archetype_keys = list(ARCHETYPES.keys())
    params = {}
    for i in range(num_users):
        arch_key = archetype_keys[i % len(archetype_keys)]
        arch = ARCHETYPES[arch_key]
        user_name = f"user_{i + 1}"
        jitter_h = random.uniform(-0.3, 0.3)
        params[user_name] = {
            "archetype": arch_key,
            "window_start": arch["window_start"],
            "window_end": arch["window_end"],
            "daily_hours_min": round(arch["daily_hours"][0] + jitter_h, 1),
            "daily_hours_max": round(arch["daily_hours"][1] + jitter_h, 1),
            "block_min": arch["block_min"] + random.randint(-5, 5),
            "block_max": arch["block_max"] + random.randint(-10, 10),
            "switch_rate": round(min(0.9, max(0.05, arch["switch_rate"] + random.uniform(-0.05, 0.05))), 2),
            "project_count": arch["project_count"],
            "lunch_hour": arch["lunch_hour"],
            "start_jitter_min": arch.get("start_jitter_min", 20),
            "primary_project": f"projekt_{random.randint(1, arch['project_count'])}",
            "primary_weight": random.uniform(0.55, 0.70),
        }
    return params


def _pick_project(config):
    """Pick a project weighted toward the user's primary project."""
    if random.random() < config["primary_weight"]:
        return config["primary_project"]
    return f"projekt_{random.randint(1, config['project_count'])}"


def _is_workday(date):
    """Returns True for Mon-Fri, False for Sat/Sun."""
    return date.weekday() < 5


def _day_factor(date, start_date, num_days, trend_strength=0.15):
    """
    Returns a multiplier (~0.85 – 1.15) representing a slow trend over the
    generation period (simulates onboarding ramp-up or seasonal changes).
    """
    progress = (date - start_date).days / max(num_days, 1)
    return 1.0 + trend_strength * math.sin(progress * math.pi)


def _weekday_factor(date):
    """
    Monday morning = slightly less productive, Friday = slightly shorter.
    Mid-week = peak productivity.
    """
    factors = {0: 0.92, 1: 1.00, 2: 1.03, 3: 1.00, 4: 0.90}
    return factors.get(date.weekday(), 0.5)


def _fatigue_factor(hours_worked, target_hours):
    """
    Session lengths decrease as the day progresses.
    Returns multiplier: 1.0 at start, ~0.6 near end of target.
    """
    if target_hours <= 0:
        return 1.0
    progress = min(hours_worked / target_hours, 1.0)
    return max(0.5, 1.0 - 0.4 * progress)


def _is_outlier_day():
    """~7% of workdays are outliers (overtime or half-day)."""
    return random.random() < 0.07


def _is_sick_day():
    """~3% of workdays are sick days (no work)."""
    return random.random() < 0.03


def _generate_day_events(date, user_id, config, day_mult):
    """Generate all start/stop events for one user on one day."""
    date_str = date.strftime("%Y-%m-%d")
    events = []

    base_min = config["daily_hours_min"] * 60
    base_max = config["daily_hours_max"] * 60
    target_minutes = int(random.uniform(base_min, base_max) * day_mult)

    # Outlier: overtime (+30-60%) or half-day (-40-60%)
    if _is_outlier_day():
        if random.random() < 0.5:
            target_minutes = int(target_minutes * random.uniform(1.3, 1.6))
        else:
            target_minutes = int(target_minutes * random.uniform(0.4, 0.6))

    ws_h, ws_m = config["window_start"]
    jitter = random.randint(-config["start_jitter_min"], config["start_jitter_min"])
    current_time = date.replace(hour=ws_h, minute=ws_m) + timedelta(minutes=jitter)

    we_h, we_m = config["window_end"]
    hard_stop = date.replace(hour=we_h, minute=we_m) + timedelta(minutes=30)

    total_worked = 0
    block_min = max(10, config["block_min"])
    block_max = max(block_min + 10, config["block_max"])
    lunch_hour = config.get("lunch_hour")
    had_lunch = lunch_hour is None

    while total_worked < target_minutes and current_time < hard_stop:
        # Lunch break
        if not had_lunch and current_time.hour >= lunch_hour:
            lunch_duration = random.randint(30, 60)
            current_time += timedelta(minutes=lunch_duration)
            had_lunch = True
            if current_time >= hard_stop:
                break

        project = _pick_project(config)

        fatigue = _fatigue_factor(total_worked / 60, target_minutes / 60)
        effective_max = int(block_max * fatigue)
        effective_max = max(block_min, min(effective_max, block_max))

        remaining = target_minutes - total_worked
        time_left = (hard_stop - current_time).seconds // 60
        max_possible = min(effective_max, time_left, remaining)

        if max_possible < block_min:
            if remaining >= block_min and time_left >= block_min:
                max_possible = block_min
            else:
                break

        duration = random.randint(block_min, max(block_min, max_possible))
        stop_time = current_time + timedelta(minutes=duration)

        if stop_time > hard_stop:
            stop_time = hard_stop
            duration = (stop_time - current_time).seconds // 60
            if duration < block_min:
                break

        events.append((user_id, project, "start", current_time.strftime(TIMESTAMP_FORMAT), date_str))
        events.append((user_id, project, "stop", stop_time.strftime(TIMESTAMP_FORMAT), date_str))

        total_worked += duration
        gap = random.randint(5, 15)
        current_time = stop_time + timedelta(minutes=gap)

    return events


# ─── Public API ──────────────────────────────────────────────────────────────

def generate_random_sample_data():
    """Generate sample data with archetype-based user profiles (90 days, 10 users)."""
    storage_type = "both"
    start_date = datetime(2025, 1, 1)
    end_date = start_date + timedelta(days=DEFAULT_NUM_DAYS - 1)
    start_date_str = start_date.strftime("%Y-%m-%d")
    end_date_str = end_date.strftime("%Y-%m-%d")

    user_params = _build_user_params(DEFAULT_NUM_USERS)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    directory = os.path.join(PATH_TO_DATA, timestamp)
    os.makedirs(directory, exist_ok=True)
    logger.info("Verzeichnis '%s' erstellt.", directory)

    generate_sample_data(
        storage_type=storage_type,
        start_date=start_date_str,
        end_date=end_date_str,
        path_to_save=directory,
        user_params=user_params,
    )

    # JSON-serializable params (tuples → lists)
    serializable = {}
    for uname, uconf in user_params.items():
        serializable[uname] = {
            k: list(v) if isinstance(v, tuple) else v
            for k, v in uconf.items()
        }

    params = {
        "num_users": len(user_params),
        "storage_type": storage_type,
        "start_date": start_date_str,
        "end_date": end_date_str,
        "num_days": DEFAULT_NUM_DAYS,
        "user_specific_params": serializable,
        "path_to_save": directory,
    }
    json_path = os.path.join(directory, f"parameter_{timestamp}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(params, f, indent=4)


def generate_sample_data(storage_type, start_date, end_date, path_to_save=PATH_TO_DATA, user_params=None):
    """
    Generate realistic synthetic time-tracking data.

    Features:
    - User archetypes (Frühaufsteher, Kernzeit, Spätarbeiter, Teilzeit, Flexibel)
    - Weekend skipping (Mon-Fri only)
    - Weekday effects (Monday/Friday shorter)
    - Temporal trends (sine wave over period)
    - Outlier days (~7%: overtime or half-day)
    - Sick days (~3%: no events)
    - Fatigue curves (block length decreases through day)
    - Lunch breaks (30-60 min)
    - Project specialization (primary project gets 60-70%)

    Parameters:
    - storage_type: 'csv', 'db', or 'both'
    - start_date: 'YYYY-MM-DD'
    - end_date: 'YYYY-MM-DD'
    - path_to_save: Output directory
    - user_params: Dict of user configs (from _build_user_params or custom)
    """
    if storage_type not in ["csv", "db", "both"]:
        raise ValueError("storage_type muss 'csv', 'db' oder 'both' sein")
    if not user_params:
        raise ValueError("user_params ist erforderlich und darf nicht leer sein")
    if not os.path.exists(path_to_save):
        raise ValueError(f"Pfad existiert nicht: {path_to_save}")

    database_path = os.path.join(path_to_save, "beispieldaten.db")
    csv_path = os.path.join(path_to_save, "beispieldaten.csv")
    all_events = []
    conn = None

    try:
        conn = create_connection(database_path)
        if not conn:
            raise sqlite3.Error("Keine Datenbankverbindung möglich")

        create_main_table(conn)
        create_events_table(conn)

        start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
        end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")
        num_days = (end_date_obj - start_date_obj).days + 1

        logger.info("Starte Datengenerierung: %d User, %d Tage (%s – %s)",
                     len(user_params), num_days, start_date, end_date)

        # Pre-create users and projects
        user_ids = {}
        all_projects = set()
        for user_name, config in user_params.items():
            user_ids[user_name] = check_user(conn, user_name)
            for p in range(1, config["project_count"] + 1):
                all_projects.add(f"projekt_{p}")
        for proj in all_projects:
            check_project(conn, proj)

        # Generate events
        for user_name, config in user_params.items():
            user_id = user_ids[user_name]
            user_event_count = 0
            arch_label = ARCHETYPES.get(config.get("archetype", ""), {}).get("label", config.get("archetype", "?"))

            for day_offset in range(num_days):
                date = start_date_obj + timedelta(days=day_offset)

                if not _is_workday(date):
                    continue
                if _is_sick_day():
                    continue

                day_mult = _weekday_factor(date) * _day_factor(date, start_date_obj, num_days)
                day_events = _generate_day_events(date, user_id, config, day_mult)
                all_events.extend(day_events)
                user_event_count += len(day_events)

            logger.info("  %s (%s): %d Events", user_name, arch_label, user_event_count)

        # Batch insert
        cursor = conn.cursor()
        cursor.executemany(
            "INSERT INTO events (user_id, project, event_type, timestamp, date) VALUES (?, ?, ?, ?, ?)",
            all_events,
        )
        conn.commit()
        cursor.close()
        logger.info("Batch-Insert: %d Events in Datenbank geschrieben", len(all_events))

        # CSV export
        if storage_type in ["csv", "both"]:
            id_to_name = {uid: name for name, uid in user_ids.items()}
            csv_rows = [
                {"user": id_to_name[row[0]], "project": row[1],
                 "event_type": row[2], "timestamp": row[3], "date": row[4]}
                for row in all_events
            ]
            df = pl.DataFrame(csv_rows)
            save_to_csv(df, csv_path)
            logger.info("Daten in CSV gespeichert: %s", csv_path)

        logger.info("Datengenerierung abgeschlossen! (%d Events)", len(all_events))

    except sqlite3.Error as e:
        logger.error("Datenbankfehler: %s", e)
    except (OSError, ValueError, TypeError) as e:
        logger.error("Fehler bei der Datengenerierung: %s", e)
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    generate_random_sample_data()
