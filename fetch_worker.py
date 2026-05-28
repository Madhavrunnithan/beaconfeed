# fetch_worker.py

from fetcher import get_updates

from database import cleanup_seen_links

import json
import time


PENDING_FILE = "pending_updates.json"


# =========================================================
# SAVE PENDING UPDATES
# =========================================================

def save_pending_updates(data):

    with open(PENDING_FILE, "w") as f:
        json.dump(data, f, indent=4)


# =========================================================
# MAIN LOOP
# =========================================================

while True:

    try:

        # Fetch latest updates
        updates = get_updates()

        # Save updates for bot sender loop
        save_pending_updates(
            updates
        )

        # Cleanup old seen links
        cleanup_seen_links(days=3)

        print(
            "[FETCH WORKER] Updates refreshed."
        )

    except Exception as e:

        print(
            "[FETCH WORKER ERROR]"
        )

        print(e)

    # Polling interval
    time.sleep(600)