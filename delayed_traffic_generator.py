import random

# -------------------------------
# OBJECT POOLS
# -------------------------------

objects = [f"obj_{i}" for i in range(500)]


# -------------------------------
# GENERATOR
# -------------------------------

def generate_delayed_traffic(n=20000):
    traffic = []
    time = 1

    for _ in range(n):

        obj = random.choice(objects)

        # -----------------------
        # PHASE 1: FIRST REQUEST
        # -----------------------
        traffic.append((time, obj))

        # -----------------------
        # PHASE 2: DELAY
        # -----------------------
        delay = random.randint(5, 50)
        future_time = time + delay

        # -----------------------
        # PHASE 3: REPEATED ACCESS (DELAYED HIT)
        # -----------------------
        repeat_count = random.randint(2, 8)

        for _ in range(repeat_count):
            traffic.append((future_time, obj))

            # small spacing inside burst
            future_time += random.randint(1, 3)

        # -----------------------
        # ADVANCE TIME
        # -----------------------
        time += random.randint(1, 3)

    return traffic


# -------------------------------
# SORT + SAVE
# -------------------------------

def save_traffic(data, file="delayed_traffic.txt"):
    # sort by time (important!)
    data.sort(key=lambda x: x[0])

    with open(file, "w") as f:
        for t, d in data:
            f.write(f"{t} {d}\n")


# -------------------------------
# RUN
# -------------------------------

traffic = generate_delayed_traffic()
save_traffic(traffic)

print("✅ Delayed-hit traffic generated in delayed_traffic.txt")