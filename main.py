import os
import sys
import csv
import time
import threading
import traci
from traci.exceptions import FatalTraCIError, TraCIException

if "SUMO_HOME" not in os.environ:
    print("ERROR: SUMO_HOME not set.")
    sys.exit(1)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CFG = os.path.join(BASE_DIR, "city.sumocfg")
OUT_DIR = os.path.join(BASE_DIR, "output")
os.makedirs(OUT_DIR, exist_ok=True)

SUMO_CMD = [
    "sumo-gui",
    "-c", CFG,
    "--start",
    "--quit-on-end", "true",
    "--delay", "4000"
]
tls_update_sem = threading.Semaphore(1)
traci_lock = threading.Lock()
stop_event = threading.Event()
metrics_lock = threading.Lock()

metrics = {}
arrived_total = set()
MAX_STEPS = 2000

def safe_min_expected():
    with traci_lock:
        try:
            return traci.simulation.getMinExpectedNumber()
        except Exception:
            return 0

def split_incoming_edges_for_tls(tls_id):
    with traci_lock:
        links = traci.trafficlight.getControlledLinks(tls_id)
    edges = []
    for link_group in links:
        for ln in link_group:
            if ln and len(ln) > 0:
                in_lane = ln[0]
                edges.append(in_lane.rsplit("_", 1)[0])
    uniq = list(dict.fromkeys(edges))
    if not uniq:
        return set(), set()
    gA = set(uniq[::2])
    gB = set(uniq[1::2]) if len(uniq) > 1 else set(uniq)
    return gA, gB

def queue_len_for_edges(edges, active_ids):
    q = 0
    for vid in active_ids:
        try:
            with traci_lock:
                e = traci.vehicle.getRoadID(vid)
                s = traci.vehicle.getSpeed(vid)
            if e in edges and s < 0.1:
                q += 1
        except (TraCIException, FatalTraCIError):
            continue
        except Exception:
            continue
    return q

def tls_worker(tls_id):
    try:
        with traci_lock:
            logics = traci.trafficlight.getAllProgramLogics(tls_id)
        if not logics or not logics[0].phases:
            return
        phase_count = len(logics[0].phases)
    except Exception:
        return

    phase_a = 0
    phase_b = 2 if phase_count > 2 else max(0, phase_count - 1)
    edges_a, edges_b = split_incoming_edges_for_tls(tls_id)

    with metrics_lock:
        metrics[tls_id] = {"qA": 0, "qB": 0, "switches": 0}

    while not stop_event.is_set():
        try:
            with traci_lock:
                active_ids = list(traci.vehicle.getIDList())

            qA = queue_len_for_edges(edges_a, active_ids)
            qB = queue_len_for_edges(edges_b, active_ids)

            with metrics_lock:
                metrics[tls_id]["qA"] = qA
                metrics[tls_id]["qB"] = qB

            desired = phase_a if qA >= qB else phase_b
            duration = min(8 + max(qA, qB), 20)

            if tls_update_sem.acquire(timeout=0.05):
                try:
                    with traci_lock:
                        cur = traci.trafficlight.getPhase(tls_id)
                        if cur != desired:
                            traci.trafficlight.setPhase(tls_id, desired)
                            with metrics_lock:
                                metrics[tls_id]["switches"] += 1
                        traci.trafficlight.setPhaseDuration(tls_id, duration)
                finally:
                    tls_update_sem.release()

        except (FatalTraCIError, OSError):
            stop_event.set()
            return
        except Exception:
            pass

        time.sleep(0.2)

def run():
    csv_path = os.path.join(OUT_DIR, "multi_tls_log.csv")

    with traci_lock:
        traci.start(SUMO_CMD)
        tls_ids = list(traci.trafficlight.getIDList())

    if not tls_ids:
        print("No traffic lights found.")
        with traci_lock:
            traci.close()
        return

    print(f"Found {len(tls_ids)} TLS controllers.")

    for tls in tls_ids:
        threading.Thread(target=tls_worker, args=(tls,), daemon=True).start()

    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["step", "activeVeh", "minExpected", "arrivedTotal", "tlsCount", "sum_qA", "sum_qB", "sum_switches"])

        step = 0
        empty_ticks = 0

        while not stop_event.is_set():
            try:
                with traci_lock:
                    traci.simulationStep()
                    active_ids = list(traci.vehicle.getIDList())
                    arrived_now = list(traci.simulation.getArrivedIDList())
            except FatalTraCIError:
                stop_event.set()
                break

            step += 1
            if step >= 60:
                stop_event.set()
            for vid in arrived_now:
                arrived_total.add(vid)

            with metrics_lock:
                sum_qA = sum(v["qA"] for v in metrics.values())
                sum_qB = sum(v["qB"] for v in metrics.values())
                sum_sw = sum(v["switches"] for v in metrics.values())

            me = safe_min_expected()

            if step % 25 == 0:
                print(f"step={step} active={len(active_ids)} exp={me} arrived={len(arrived_total)} tls={len(tls_ids)} qA={sum_qA} qB={sum_qB} sw={sum_sw}")

            w.writerow([step, len(active_ids), me, len(arrived_total), len(tls_ids), sum_qA, sum_qB, sum_sw])

            if me <= 0 and len(active_ids) == 0:
                empty_ticks += 1
            else:
                empty_ticks = 0

            if empty_ticks >= 20 or step >= MAX_STEPS:
                stop_event.set()

    with traci_lock:
        try:
            traci.close()
        except Exception:
            pass

    print("Done. Log:", csv_path)

if __name__ == "__main__":
    run()