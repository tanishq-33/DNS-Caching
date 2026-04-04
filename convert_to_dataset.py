# convert_to_dataset.py

data = []

with open("raw_dns.txt") as f:
    for line in f:
        parts = line.strip().split()
        if len(parts) < 2:
            continue

        t = float(parts[0])
        domain = parts[1]
        data.append((t, domain))

# -------------------------------
# SORT BY TIME
# -------------------------------
data.sort(key=lambda x: x[0])

# -------------------------------
# NORMALIZE + DISCRETIZE TIME
# -------------------------------
start = data[0][0]

processed = []
current_time = 0
prev_t = start

for t, d in data:
    # convert real time gap into discrete steps
    gap = t - prev_t

    if gap > 0:
        current_time += int(gap * 10) + 1   # scale factor

    processed.append((current_time, d))
    prev_t = t

# -------------------------------
# SAVE
# -------------------------------
with open("dns_traffic.txt", "w") as f:
    for t, d in processed:
        f.write(f"{t} {d}\n")

print("✅ Fixed dataset with proper time progression")