# runner.py

import multiprocessing
import subprocess
import sys

from database import initialize_database


# =========================================================
# BOT PROCESS
# =========================================================

def run_bot():

    subprocess.run(
        [sys.executable, "bot_handler.py"]
    )


# =========================================================
# FETCH WORKER PROCESS
# =========================================================

def run_fetch_worker():

    subprocess.run(
        [sys.executable, "fetch_worker.py"]
    )


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":

    # Initialize SQLite database
    initialize_database()

    # Create processes
    bot_process = multiprocessing.Process(
        target=run_bot
    )

    fetch_process = multiprocessing.Process(
        target=run_fetch_worker
    )

    # Start processes
    bot_process.start()

    fetch_process.start()

    print("[RUNNER] BeaconFeed started.")

    # Keep processes alive
    bot_process.join()

    fetch_process.join()