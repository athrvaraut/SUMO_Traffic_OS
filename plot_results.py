import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv("output/traffic_log.csv")

fig, ax = plt.subplots(3, 1, figsize=(10, 10), sharex=True)

ax[0].plot(df["step"], df["ns_queue"], label="NS Queue")
ax[0].plot(df["step"], df["ew_queue"], label="EW Queue")
ax[0].set_ylabel("Queue Length")
ax[0].legend()
ax[0].grid(True)

ax[1].plot(df["step"], df["throughput"], color="green")
ax[1].set_ylabel("Throughput")
ax[1].grid(True)

ax[2].plot(df["step"], df["avg_wait"], color="red")
ax[2].set_ylabel("Avg Wait (s)")
ax[2].set_xlabel("Simulation Step")
ax[2].grid(True)

plt.tight_layout()
plt.savefig("output/traffic_results.png", dpi=200)
plt.show()