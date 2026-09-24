import sys
import json
import csv
import os

CSV_FILE = "research_evaluation.csv"
CORRECT_COLUMN = "Correct"
DISCREPANCY_COLUMN = "Discrepancy Notes"


def log(msg):
    print(msg, file=sys.stderr, flush=True)


def build_discrepancy_note(predicted_os, actual_value, notes):
    parts = []
    if actual_value:
        parts.append(f"Predicted {predicted_os}, actual {actual_value}")
    if notes:
        parts.append(notes)
    return " | ".join(parts)


def record_feedback(mac, timestamp, is_correct, actual_value, notes):
    if not os.path.isfile(CSV_FILE):
        raise FileNotFoundError(f"{CSV_FILE} not found")

    with open(CSV_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames)
        rows = list(reader)

    if CORRECT_COLUMN not in fieldnames:
        fieldnames.append(CORRECT_COLUMN)
        for row in rows:
            row[CORRECT_COLUMN] = ""

    match = None
    for row in rows:
        if row.get("Timestamp") == timestamp and row.get("MAC Address") == mac:
            match = row
            break

    if match is None:
        raise LookupError(f"No scan record found for mac={mac} timestamp={timestamp}")

    predicted_os = match.get("Predicted OS", "Unknown")
    match[CORRECT_COLUMN] = "true" if is_correct else "false"
    match[DISCREPANCY_COLUMN] = (
        "Confirmed correct" if is_correct
        else build_discrepancy_note(predicted_os, actual_value, notes)
    )

    with open(CSV_FILE, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return match


def main():
    if len(sys.argv) != 2:
        print(json.dumps({"error": "Expected a single JSON argument"}))
        sys.exit(1)

    try:
        payload = json.loads(sys.argv[1])
        mac = payload["mac"]
        timestamp = payload["timestamp"]
        is_correct = bool(payload["is_correct"])
        actual_value = payload.get("actual_value", "") or ""
        notes = payload.get("notes", "") or ""

        updated_row = record_feedback(mac, timestamp, is_correct, actual_value, notes)
        print(json.dumps({"success": True, "updated_row": updated_row}))
    except (KeyError, ValueError) as e:
        log(f"Invalid payload: {e}")
        print(json.dumps({"error": f"Invalid payload: {e}"}))
        sys.exit(1)
    except (FileNotFoundError, LookupError) as e:
        log(str(e))
        print(json.dumps({"error": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
