import random
import matplotlib.pyplot as plt
from collections import OrderedDict, deque

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
    def __init__(self, cap=20):
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
# FIFO CACHE
# =========================
class FIFOCache:
    def __init__(self, cap=20):
        self.queue = deque()
        self.set = set()
        self.cap = cap
        self.hits = 0
        self.misses = 0
        self.hit_hist = []

    def get(self, key):
        if key in self.set:
            self.hits += 1
            return True
        self.misses += 1
        return False

    def put(self, key):
        if key not in self.set:
            if len(self.queue) >= self.cap:
                old = self.queue.popleft()
                self.set.remove(old)
            self.queue.append(key)
            self.set.add(key)

    def record(self):
        total = self.hits + self.misses
        hr = self.hits / total if total else 0
        self.hit_hist.append(hr)


# =========================
# LFU CACHE
# =========================
class LFUCache:
    def __init__(self, cap=20):
        self.cap = cap
        self.cache = {}
        self.freq = {}
        self.hits = 0
        self.misses = 0
        self.hit_hist = []

    def get(self, key):
        if key in self.cache:
            self.freq[key] += 1
            self.hits += 1
            return True
        self.misses += 1
        return False

    def put(self, key):
        if self.cap == 0:
            return

        if key in self.cache:
            self.freq[key] += 1
            return

        if len(self.cache) >= self.cap:
            lfu_key = min(self.freq, key=lambda k: self.freq[k])
            del self.cache[lfu_key]
            del self.freq[lfu_key]

        self.cache[key] = 1
        self.freq[key] = 1

    def record(self):
        total = self.hits + self.misses
        hr = self.hits / total if total else 0
        self.hit_hist.append(hr)


# =========================
# BELATEDLY (MAD-style) CACHE
# =========================
class BelatedMADCache:
    def __init__(self, cap=20, miss_latency=50):
        self.cap = cap
        self.cache = OrderedDict()

        self.fetching = {}
        self.pending = {}
        self.aggregate_delay = {}

        self.miss_latency = miss_latency

        self.hits = 0
        self.misses = 0
        self.hit_hist = []

    def get(self, key, t):

        if key in self.cache:
            self.cache.move_to_end(key)
            self.hits += 1
            return True

        if key in self.fetching:
            self.pending[key] += 1
            self.aggregate_delay[key] += self.miss_latency
            self.hits += 1
            return True

        self.misses += 1
        self.fetching[key] = t + self.miss_latency
        self.pending[key] = 1
        self.aggregate_delay[key] = self.miss_latency

        return False

    def update_fetches(self, t):
        completed = [k for k, end in self.fetching.items() if end <= t]

        for key in completed:
            self._insert(key)
            del self.fetching[key]
            del self.pending[key]
            del self.aggregate_delay[key]

    def _insert(self, key):
        if len(self.cache) >= self.cap:
            victim = min(self.cache.keys(),
                         key=lambda k: self.aggregate_delay.get(k, 0))
            del self.cache[victim]

        self.cache[key] = 1

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
    fifo = FIFOCache()
    lfu = LFUCache()
    belated = BelatedMADCache()

    lat_d, lat_f, lat_l = [], [], []
    lat_fifo, lat_lfu, lat_b = [], [], []

    for req, t in zip(requests, time_steps):

        # BELATED UPDATE
        belated.update_fetches(t)

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

        # FIFO
        if fifo.get(req):
            lat_fifo.append(5)
        else:
            lat_fifo.append(50)
            fifo.put(req)
        fifo.record()

        # LFU
        if lfu.get(req):
            lat_lfu.append(5)
        else:
            lat_lfu.append(50)
            lfu.put(req)
        lfu.record()

        # BELATED
        if belated.get(req, t):
            lat_b.append(5)
        else:
            lat_b.append(50)
        belated.record()

    return dttl, fttl, lru, fifo, lfu, belated, \
           lat_d, lat_f, lat_l, lat_fifo, lat_lfu, lat_b, mode


# =========================
# EVALUATION
# =========================
def evaluate(dttl, fttl, lru, fifo, lfu, belated,
             lat_d, lat_f, lat_l, lat_fifo, lat_lfu, lat_b, mode):

    def metrics(lat, hits, misses):
        hr = hits / (hits + misses)
        avg_lat = sum(lat) / len(lat)
        return hr, avg_lat

    print("\n--- PERFORMANCE ---")

    hr, lat = metrics(lat_d, dttl.hits, dttl.misses)
    print(f"d-TTL   -> HitRate: {hr:.3f}, Avg Latency: {lat:.2f}")

    hr, lat = metrics(lat_f, fttl.hits, fttl.misses)
    print(f"f-TTL   -> HitRate: {hr:.3f}, Avg Latency: {lat:.2f}")

    hr, lat = metrics(lat_l, lru.hits, lru.misses)
    print(f"LRU     -> HitRate: {hr:.3f}, Avg Latency: {lat:.2f}")

    hr, lat = metrics(lat_fifo, fifo.hits, fifo.misses)
    print(f"FIFO    -> HitRate: {hr:.3f}, Avg Latency: {lat:.2f}")

    hr, lat = metrics(lat_lfu, lfu.hits, lfu.misses)
    print(f"LFU     -> HitRate: {hr:.3f}, Avg Latency: {lat:.2f}")

    hr, lat = metrics(lat_b, belated.hits, belated.misses)
    print(f"Belated -> HitRate: {hr:.3f}, Avg Latency: {lat:.2f}")

def moving_avg(arr, window=500):
    res = []
    s = 0

    for i in range(len(arr)):
        s += arr[i]
        if i >= window:
            s -= arr[i - window]
        res.append(s / min(i + 1, window))

    return res

# =========================
# PLOTTING
# =========================
def plot(dttl, fttl, lru, fifo, lfu, belated,
         lat_d, lat_f, lat_l, lat_fifo, lat_lfu, lat_b):

    plt.figure(figsize=(12, 9))

    # Hit rate
    plt.subplot(3, 1, 1)
    plt.plot(dttl.hit_hist, label="d-TTL")
    plt.plot(fttl.hit_hist, label="f-TTL")
    plt.plot(lru.hit_hist, label="LRU")
    plt.plot(fifo.hit_hist, label="FIFO")
    plt.plot(lfu.hit_hist, label="LFU")
    plt.plot(belated.hit_hist, label="Belatedly")
    plt.legend()
    plt.title("Hit Rate Comparison")

    # d-TTL theta
    plt.subplot(3, 1, 2)
    plt.plot(dttl.theta_hist)
    plt.title("d-TTL Adaptation")

    # Latency
    plt.subplot(3, 1, 3)

    plt.plot(moving_avg(lat_d), label="d-TTL")
    plt.plot(moving_avg(lat_f), label="f-TTL")
    plt.plot(moving_avg(lat_l), label="LRU")
    plt.plot(moving_avg(lat_fifo), label="FIFO")
    plt.plot(moving_avg(lat_lfu), label="LFU")
    plt.plot(moving_avg(lat_b), label="Belated")
    plt.legend()
    plt.title("Latency Comparison (Smoothed)")

    plt.tight_layout()
    plt.show()


# =========================
# MAIN
# =========================
if __name__ == "__main__":
    dttl, fttl, lru, fifo, lfu, belated, \
    lat_d, lat_f, lat_l, lat_fifo, lat_lfu, lat_b, mode = simulate()

    evaluate(dttl, fttl, lru, fifo, lfu, belated,
             lat_d, lat_f, lat_l, lat_fifo, lat_lfu, lat_b, mode)

    plot(dttl, fttl, lru, fifo, lfu, belated,
         lat_d, lat_f, lat_l, lat_fifo, lat_lfu, lat_b) 