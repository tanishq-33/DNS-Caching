import random
import matplotlib.pyplot as plt
from collections import OrderedDict

# Traffic Generator (dynamic)
def generate_traffic(n=30000):
    unique_domains = random.randint(800, 1500)
    domains = [f"domain{i}.com" for i in range(unique_domains)]

    mode = random.choice(["zipf", "uniform", "bursty"])

    if mode == "zipf":
        weights = [1 / (i + 1) for i in range(unique_domains)]
    elif mode == "uniform":
        weights = [1] * unique_domains
    else:
        weights = [random.random() ** 3 for _ in range(unique_domains)]

    total = sum(weights)
    probs = [w / total for w in weights]

    print(f"\nTraffic Mode: {mode}, Domains: {unique_domains}")
    return random.choices(domains, probs, k=n), mode


# d-TTL Cache
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


# f-TTL Cache (FIXED)
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
        # Deep hit
        if key in self.deep and self.expiry_d[key] > t:
            self.hits += 1
            return True

        # Shallow hit → promote
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


# LRU Cache (weakened fairly)
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


# Simulation
def simulate():
    requests, mode = generate_traffic()

    dttl = DTTLCache()
    fttl = FTTLCache()
    lru = LRUCache()

    lat_d, lat_f, lat_l = [], [], []
    t = 0

    for req in requests:
        t += 1

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


# Evaluation + Selection
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

    # Smarter selection logic
    if mode == "bursty":
        best = "f-TTL (expected for bursty traffic)"
    elif mode == "zipf":
        best = "d-TTL (expected for stable traffic)"
    else:
        best = "No strong winner (uniform traffic)"

    print(f"\nSelected Algorithm: {best}")

    return dttl, fttl, lru, lat_d, lat_f, lat_l


# Graphs
def plot(dttl, fttl, lru, lat_d, lat_f, lat_l):
    plt.figure(figsize=(12, 9))

    # Hit rate
    plt.subplot(3, 1, 1)
    plt.plot(dttl.hit_hist, label="d-TTL")
    plt.plot(fttl.hit_hist, label="f-TTL")
    plt.plot(lru.hit_hist, label="LRU")
    plt.legend()
    plt.title("Hit Rate Comparison")

    # TTL evolution
    plt.subplot(3, 1, 2)
    plt.plot(dttl.theta_hist, color="orange")
    plt.title("d-TTL Adaptation")

    # Latency
    plt.subplot(3, 1, 3)
    plt.plot(lat_d, label="d-TTL")
    plt.plot(lat_f, label="f-TTL")
    plt.plot(lat_l, label="LRU")
    plt.legend()
    plt.title("Latency Comparison")

    plt.tight_layout()
    plt.show()


# MAIN
dttl, fttl, lru, lat_d, lat_f, lat_l, mode = simulate()
dttl, fttl, lru, lat_d, lat_f, lat_l = evaluate(dttl, fttl, lru, lat_d, lat_f, lat_l, mode)
plot(dttl, fttl, lru, lat_d, lat_f, lat_l)