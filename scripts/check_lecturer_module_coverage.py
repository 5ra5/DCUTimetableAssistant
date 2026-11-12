#!/usr/bin/env python3

import csv
import json
import time
import urllib.parse
import urllib.request

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SEED_DIR = ROOT / "data" / "seed"
RAW_DIR = ROOT / "data" / "raw" / "module_events"

API_BASE = "https://timetable.redbrick.dcu.ie/api/v3"

SEMESTER_START = "2026-09-01"
SEMESTER_END = "2026-12-20"


def load_csv(filename):
    path = SEED_DIR / filename

    with path.open(
        newline="",
        encoding="utf-8",
    ) as file:
        return list(csv.DictReader(file))


def fetch_module_events(module_uuid):
    parameters = urllib.parse.urlencode(
        {
            "start": SEMESTER_START,
            "end": SEMESTER_END,
        }
    )

    url = (
        f"{API_BASE}/timetable/category/module/items/"
        f"{module_uuid}/events?{parameters}"
    )

    request = urllib.request.Request(
        url,
        headers={
            "media-type": "application/json",
            "User-Agent": "DCU-Timetable-Assistant/1.0",
        },
    )

    with urllib.request.urlopen(
        request,
        timeout=30,
    ) as response:
        events = json.load(response)

    if not isinstance(events, list):
        raise ValueError(
            "Expected a JSON array of module events."
        )

    return events


def main():
    RAW_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    links = load_csv("lecturer_modules.csv")
    room_events = load_csv("timetable_events.csv")

    known_event_uuids = {
        row["redbrick_uuid"]
        for row in room_events
    }

    module_uuids = sorted({
        row["module_uuid"]
        for row in links
    })

    print("=== LECTURER MODULE COVERAGE ===")
    print("Lecturer-module relationships:", len(links))
    print("Distinct modules:", len(module_uuids))
    print("Room events already stored:", len(known_event_uuids))

    missing_event_uuids = set()
    failures = []

    for index, module_uuid in enumerate(
        module_uuids,
        start=1,
    ):
        print(
            f"[{index}/{len(module_uuids)}] "
            f"Checking {module_uuid}..."
        )

        cache_file = RAW_DIR / f"{module_uuid}.json"

        try:
            if cache_file.exists():
                with cache_file.open(
                    encoding="utf-8",
                ) as file:
                    events = json.load(file)

                print(
                    f"  Loaded {len(events)} events from cache"
                )

            else:
                events = fetch_module_events(
                    module_uuid
                )

                with cache_file.open(
                    "w",
                    encoding="utf-8",
                ) as file:
                    json.dump(
                        events,
                        file,
                        indent=2,
                        ensure_ascii=False,
                    )

                print(
                    f"  Downloaded {len(events)} events"
                )

                time.sleep(0.2)

            new_count = 0

            for event in events:
                event_uuid = event.get("identity")

                if (
                    event_uuid
                    and event_uuid not in known_event_uuids
                ):
                    missing_event_uuids.add(event_uuid)
                    new_count += 1

            print(
                f"  Events not in room dataset: {new_count}"
            )

        except Exception as error:
            failures.append(
                (module_uuid, str(error))
            )

            print(
                f"  FAILED: {error}"
            )

    print("\n=== COVERAGE SUMMARY ===")

    print("Modules checked:", len(module_uuids))
    print("Failed module requests:", len(failures))
    print(
        "Unique events missing from room snapshot:",
        len(missing_event_uuids),
    )

    if failures:
        print("\nFailed modules:")
        for module_uuid, error in failures:
            print(f"  {module_uuid}: {error}")


if __name__ == "__main__":
    main()