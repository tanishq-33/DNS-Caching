import random
import time
import threading
import dns.resolver

# -------------------------------
# CUSTOM RESOLVER (BYPASS OS CACHE)
# -------------------------------
resolver = dns.resolver.Resolver()
resolver.nameservers = ["8.8.8.8"]  # Google DNS


def dns_query(domain):
    try:
        resolver.resolve(domain)
    except:
        pass


# -------------------------------
# DOMAIN POOLS
# -------------------------------
hot_domains = [
    "google.com", "youtube.com", "facebook.com", "instagram.com",
    "twitter.com", "reddit.com", "amazon.com", "netflix.com"
]

warm_domains = [
    "wikipedia.org", "github.com", "stackoverflow.com",
    "linkedin.com", "bing.com", "yahoo.com", "zoom.us"
]

cold_domains = [
    "medium.com", "dev.to", "coursera.org", "udemy.com",
    "archive.org", "arxiv.org", "unsplash.com"
]


# -------------------------------
# WORKER
# -------------------------------
def worker(n):
    for _ in range(n):

        r = random.random()

        # Zipf distribution
        if r < 0.6:
            domain = random.choice(hot_domains)
        elif r < 0.85:
            domain = random.choice(warm_domains)
        else:
            domain = random.choice(cold_domains)

        # BURST
        if random.random() < 0.3:
            for _ in range(random.randint(3, 8)):
                dns_query(domain)
        else:
            dns_query(domain)

        # DELAYED HIT (MAD)
        if random.random() < 0.2:
            def delayed(d=domain):
                time.sleep(random.uniform(0.5, 2))
                for _ in range(random.randint(2, 5)):
                    dns_query(d)

            threading.Thread(target=delayed).start()

        time.sleep(random.uniform(0.001, 0.01))


# -------------------------------
# MAIN
# -------------------------------
def generate(total=6000, threads=20):
    per_thread = total // threads
    ts = []

    for _ in range(threads):
        t = threading.Thread(target=worker, args=(per_thread,))
        t.start()
        ts.append(t)

    for t in ts:
        t.join()

    print("✅ DNS traffic generated")


generate()