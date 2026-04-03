import random

# -------------------------------
# OBJECT POOLS
# -------------------------------

# Popular content (hot objects)
hot_objects = [f"obj_hot_{i}" for i in range(10)]

# Medium popularity
warm_objects = [f"obj_warm_{i}" for i in range(50)]

# Rare objects
cold_objects = [f"obj_cold_{i}" for i in range(1000)]


# -------------------------------
# TRAFFIC GENERATOR
# -------------------------------

def generate_cdn_traffic(n=20000):
    traffic = []
    time = 1

    for _ in range(n):
        r = random.random()

        # Zipf-like popularity
        if r < 0.6:
            obj = random.choice(hot_objects)
        elif r < 0.85:
            obj = random.choice(warm_objects)
        else:
            obj = random.choice(cold_objects)

        # 🔥 Burst (simulate concurrent requests)
        if random.random() < 0.3:
            burst_size = random.randint(3, 10)

            for _ in range(burst_size):
                traffic.append((time, obj))
        else:
            traffic.append((time, obj))
            time += 1

    return traffic


# -------------------------------
# SAVE TO FILE
# -------------------------------

def save_traffic(data, file="dns_traffic.txt"):
    with open(file, "w") as f:
        for t, d in data:
            f.write(f"{t} {d}\n")


# -------------------------------
# RUN
# -------------------------------

traffic = generate_cdn_traffic()
save_traffic(traffic)

print("✅ CDN-like traffic generated")