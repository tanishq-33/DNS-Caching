import random
import matplotlib.pyplot as plt
from collections import OrderedDict

# =========================
# LOAD DNS TRAFFIC FROM FILE
# =========================
def load_dns_traffic(file="dns_traffic.txt"):
    requests = []
    time_steps = []

    with open(file, "r") as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) != 2:
                continue
            t, domain = parts
            requests.append(domain)
            time_steps.append(int(t))

    print(f"\nLoaded {len(requests)} DNS queries from file")
    return requests, time_steps


# =========================
# d-TTL CACHE
# =========================
class DTTLCache:
    def __init__(self):
        self.store = {}
        self.expiry = {}

        self.theta = 20
        self.eta = 0.05
        self.target = 0.6

        self.hits = 0
        self.misses = 0

        self.theta_hist = []
        self.hit_hist = []

    def get(self, key, t):
        if key in self.store and self.expiry[key] > t:
            self.hits += 1
            self._update(1)
            return True
        else:
            self.misses += 1
            self._update(0)
            if key in self.store:
                del self.store[key]
                del self.expiry[key]
            return False

    def put(self, key, t):
        self.store[key] = 1
        self.expiry[key] = t + self.theta

    def _update(self, hit):
        self.theta += self.eta * (self.target - hit)
        self.theta = max(1, min(self.theta, 500))

    def record(self):
        total = self.hits + self.misses
        hr = self.hits / total if total else 0
        self.theta_hist.append(self.theta)
        self.hit_hist.append(hr)


# =========================
# f-TTL CACHE
# =========================
class FTTLCache:
    def __init__(self):
        self.shallow = {}
        self.deep = {}

        self.expiry_s = {}
        self.expiry_d = {}

        self.theta_s = 5
        self.theta_d = 100

        self.hits = 0
        self.misses = 0
        self.hit_hist = []

    def get(self, key, t):
        if key in self.deep and self.expiry_d[key] > t:
            self.hits += 1
            return True

        if key in self.shallow and self.expiry_s[key] > t:
            self.deep[key] = 1
            self.expiry_d[key] = t + self.theta_d
            self.hits += 1
            return True

        self.misses += 1
        return False

    def put(self, key, t):
        self.shallow[key] = 1
        self.expiry_s[key] = t + self.theta_s

    def record(self):
        total = self.hits + self.misses
        hr = self.hits / total if total else 0
        self.hit_hist.append(hr)


# =========================
# LRU CACHE
# =========================
class LRUCache:
    def __init__(self, cap=100):
        self.cache = OrderedDict()
        self.cap = cap
        self.hits = 0
        self.misses = 0
        self.hit_hist = []

    def get(self, key):
        if key in self.cache:
            self.cache.move_to_end(key)
            self.hits += 1
            return True
        self.misses += 1
        return False

    def put(self, key):
        self.cache[key] = 1
        if len(self.cache) > self.cap:
            self.cache.popitem(last=False)

    def record(self):
        total = self.hits + self.misses
        hr = self.hits / total if total else 0
        self.hit_hist.append(hr)


# =========================
# SIMULATION
# =========================
def simulate():
    requests, time_steps = load_dns_traffic()
    mode = "realistic"

    dttl = DTTLCache()
    fttl = FTTLCache()
    lru = LRUCache()

    lat_d, lat_f, lat_l = [], [], []

    for req, t in zip(requests, time_steps):

        # d-TTL
        if dttl.get(req, t):
            lat_d.append(5)
        else:
            lat_d.append(50)
            dttl.put(req, t)
        dttl.record()

        # f-TTL
        if fttl.get(req, t):
            lat_f.append(5)
        else:
            lat_f.append(50)
            fttl.put(req, t)
        fttl.record()

        # LRU
        if lru.get(req):
            lat_l.append(5)
        else:
            lat_l.append(50)
            lru.put(req)
        lru.record()

    return dttl, fttl, lru, lat_d, lat_f, lat_l, mode


# =========================
# EVALUATION
# =========================
def evaluate(dttl, fttl, lru, lat_d, lat_f, lat_l, mode):
    def metrics(lat, hits, misses):
        hr = hits / (hits + misses)
        avg_lat = sum(lat) / len(lat)
        return hr, avg_lat

    d_hr, d_lat = metrics(lat_d, dttl.hits, dttl.misses)
    f_hr, f_lat = metrics(lat_f, fttl.hits, fttl.misses)
    l_hr, l_lat = metrics(lat_l, lru.hits, lru.misses)

    print("\n--- PERFORMANCE ---")
    print(f"d-TTL  -> HitRate: {d_hr:.3f}, Latency: {d_lat:.2f}")
    print(f"f-TTL  -> HitRate: {f_hr:.3f}, Latency: {f_lat:.2f}")
    print(f"LRU    -> HitRate: {l_hr:.3f}, Latency: {l_lat:.2f}")

    print(f"\nTraffic Type: {mode}")


# =========================
# PLOTTING
# =========================
def plot(dttl, fttl, lru, lat_d, lat_f, lat_l):
    plt.figure(figsize=(12, 9))

    plt.subplot(3, 1, 1)
    plt.plot(dttl.hit_hist, label="d-TTL")
    plt.plot(fttl.hit_hist, label="f-TTL")
    plt.plot(lru.hit_hist, label="LRU")
    plt.legend()
    plt.title("Hit Rate Comparison")

    plt.subplot(3, 1, 2)
    plt.plot(dttl.theta_hist)
    plt.title("d-TTL Adaptation")

    plt.subplot(3, 1, 3)
    plt.plot(lat_d, label="d-TTL")
    plt.plot(lat_f, label="f-TTL")
    plt.plot(lat_l, label="LRU")
    plt.legend()
    plt.title("Latency Comparison")

    plt.tight_layout()
    plt.show()


# =========================
# MAIN
# =========================
if __name__ == "__main__":
    dttl, fttl, lru, lat_d, lat_f, lat_l, mode = simulate()
    evaluate(dttl, fttl, lru, lat_d, lat_f, lat_l, mode)
    plot(dttl, fttl, lru, lat_d, lat_f, lat_l)


# import random

# def generate_dns_file(filename="dns_traffic.txt", n=30000):
#     top_domains = [
#         "google.com", "youtube.com", "facebook.com", "amazon.com",
#         "instagram.com", "twitter.com", "netflix.com", "reddit.com"
#     ]

#     long_tail = [f"site{i}.com" for i in range(1, 1000)]
#     domains = top_domains + long_tail

#     weights = [1/(i+1) for i in range(len(domains))]
#     total = sum(weights)
#     probs = [w/total for w in weights]

#     with open(filename, "w") as f:
#         t = 1
#         for _ in range(n):
#             if random.random() < 0.1:  # burst
#                 d = random.choice(top_domains)
#                 for _ in range(random.randint(5, 15)):
#                     f.write(f"{t} {d}\n")
#                     t += 1
#             else:
#                 d = random.choices(domains, probs)[0]
#                 f.write(f"{t} {d}\n")
#                 t += 1

#     print("dns_traffic.txt generated!")

# generate_dns_file()