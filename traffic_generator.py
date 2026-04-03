"""
dns_traffic_generator.py
========================
Generates a realistic synthetic DNS traffic trace and writes it to
dns_traffic.txt (format: "<timestamp_int> <domain>", one query per line).

Design goals
------------
1. Realistic domain popularity  — Zipf / power-law distribution (a small
   set of domains gets the vast majority of queries, like real traffic).
2. Diurnal (time-of-day) pattern — query rate peaks during daytime hours
   and drops at night, matching measured ISP traces.
3. Burst / flash-crowd events   — short spikes where one domain suddenly
   gets hammered (news event, viral content, etc.).
4. Repeated queries within the TTL window — essential for exercising both
   the MAD delayed-hit path and the TTL-based caches.
5. Cold-start period            — early queries are all misses so caches
   can warm up naturally.
6. Configurable size            — default 5 000 queries (enough for
   statistically stable hit-rate curves).

Output format
-------------
Each line: "<integer_timestamp> <domain>"
Timestamps start at 0 and increase monotonically (millisecond resolution
converted to integer seconds so TTL arithmetic stays simple).

Usage
-----
    python dns_traffic_generator.py            # writes dns_traffic.txt
    python dns_traffic_generator.py --n 10000  # 10 000 queries
"""

import random
import math
import argparse
from collections import defaultdict

# ---------------------------------------------------------------------------
# Domain universe
# ---------------------------------------------------------------------------
# Tier 1 — ultra-popular (top ~10 globally)
TIER1 = [
    "google.com", "youtube.com", "facebook.com", "instagram.com",
    "twitter.com", "amazon.com", "netflix.com", "wikipedia.org",
    "reddit.com", "tiktok.com",
]

# Tier 2 — popular (top 11-60)
TIER2 = [
    "github.com", "stackoverflow.com", "linkedin.com", "whatsapp.com",
    "microsoft.com", "apple.com", "yahoo.com", "bing.com",
    "twitch.tv",   "discord.com",   "spotify.com",  "dropbox.com",
    "zoom.us",     "slack.com",     "notion.so",    "figma.com",
    "cloudflare.com", "akamai.com", "fastly.com",   "shopify.com",
    "wordpress.com", "medium.com",  "quora.com",    "pinterest.com",
    "tumblr.com",  "flickr.com",   "vimeo.com",    "dailymotion.com",
    "soundcloud.com", "bandcamp.com",
    "amazon.in",   "flipkart.com", "paytm.com",    "zomato.com",
    "swiggy.com",  "ola.com",      "meesho.com",   "myntra.com",
    "hotstar.com", "jio.com",
]

# Tier 3 — long-tail (hundreds of less-visited domains)
TIER3 = [f"site{i}.example.com" for i in range(1, 201)] + \
        [f"cdn{i}.akamaized.net"  for i in range(1,  51)] + \
        [f"api{i}.service.io"     for i in range(1,  51)] + \
        [f"news{i}.portal.net"    for i in range(1,  51)]

ALL_DOMAINS = TIER1 + TIER2 + TIER3
N_DOMAINS   = len(ALL_DOMAINS)


# ---------------------------------------------------------------------------
# Zipf weight generator
# ---------------------------------------------------------------------------
def zipf_weights(n, alpha=1.2):
    """Return normalised Zipf weights for n items with exponent alpha."""
    raw = [1.0 / (i ** alpha) for i in range(1, n + 1)]
    total = sum(raw)
    return [w / total for w in raw]


# ---------------------------------------------------------------------------
# Diurnal rate multiplier
#   Peaks around hour 13 (1 pm), troughs around hour 3 (3 am).
#   Returns a float in [0.1, 1.0].
# ---------------------------------------------------------------------------
def diurnal_rate(hour_of_day):
    # Smooth cosine curve: peak at 13 h, trough at 1 h
    angle = 2 * math.pi * (hour_of_day - 13) / 24
    rate  = 0.55 + 0.45 * math.cos(angle)   # range [0.10, 1.00]
    return max(0.1, rate)


# ---------------------------------------------------------------------------
# Traffic generator
# ---------------------------------------------------------------------------
def generate(
    n_queries    = 5000,
    alpha        = 1.1,    # Zipf exponent (higher = more skewed)
    base_gap_ms  = 200,    # median inter-query gap (ms) at peak hour
    burst_prob   = 0.002,  # probability of a burst event per query
    burst_size   = (20, 80),   # (min, max) extra queries in a burst
    burst_repeat_prob = 0.85,  # prob that burst queries hit the same domain
    repeat_window_ms  = 3000,  # window in which a domain may be re-queried
    repeat_prob       = 0.30,  # prob of re-querying a recent domain
    seed         = 42,
    outfile      = "dns_traffic.txt",
    start_hour   = 8,      # simulation starts at 8 am
):
    random.seed(seed)

    weights = zipf_weights(N_DOMAINS, alpha)

    # We'll build a list of (timestamp_ms, domain)
    trace = []

    current_ms   = 0
    hour_of_day  = start_hour
    recent_queue = []           # domains queried in the last repeat_window_ms

    i = 0
    while i < n_queries:
        # ---- Advance time ----
        hour_of_day = (start_hour + current_ms // 3_600_000) % 24
        rate_mult   = diurnal_rate(hour_of_day)
        # Inter-arrival: exponential with mean scaled by diurnal rate
        gap = random.expovariate(1.0 / (base_gap_ms / rate_mult))
        current_ms += int(gap)

        # ---- Choose domain ----
        # With some probability, re-query a recently seen domain
        # (simulates TTL-range re-lookups, browser prefetch, etc.)
        if recent_queue and random.random() < repeat_prob:
            # pick from recent domains, biased towards most recent
            cutoff = current_ms - repeat_window_ms
            recent_queue = [(t, d) for t, d in recent_queue if t >= cutoff]
            if recent_queue:
                domain = random.choice(recent_queue)[1]
            else:
                domain = random.choices(ALL_DOMAINS, weights=weights, k=1)[0]
        else:
            domain = random.choices(ALL_DOMAINS, weights=weights, k=1)[0]

        trace.append((current_ms, domain))
        recent_queue.append((current_ms, domain))
        i += 1

        # ---- Burst event ----
        if random.random() < burst_prob and i < n_queries:
            burst_n      = random.randint(*burst_size)
            burst_domain = domain   # burst centres on current domain
            for _ in range(min(burst_n, n_queries - i)):
                current_ms += random.randint(10, 150)   # very rapid fire
                if random.random() < burst_repeat_prob:
                    bd = burst_domain
                else:
                    bd = random.choices(ALL_DOMAINS, weights=weights, k=1)[0]
                trace.append((current_ms, bd))
                recent_queue.append((current_ms, bd))
                i += 1

    # ---- Convert ms timestamps to integer seconds ----
    # (keeps TTL arithmetic readable while preserving relative spacing)
    t0 = trace[0][0]
    trace_sec = [(int((t - t0) / 1000), d) for t, d in trace]

    # ---- Write output ----
    with open(outfile, "w") as f:
        for t, d in trace_sec:
            f.write(f"{t} {d}\n")

    # ---- Statistics ----
    domain_counts = defaultdict(int)
    for _, d in trace_sec:
        domain_counts[d] += 1

    total     = len(trace_sec)
    top5      = sorted(domain_counts.items(), key=lambda x: -x[1])[:5]
    unique    = len(domain_counts)
    duration  = trace_sec[-1][0] - trace_sec[0][0]

    print(f"\n=== DNS Traffic Generator ===")
    print(f"  Total queries  : {total}")
    print(f"  Unique domains : {unique}")
    print(f"  Duration       : {duration} s  (~{duration/3600:.2f} hours)")
    print(f"  Top-5 domains  :")
    for dom, cnt in top5:
        print(f"    {dom:40s}  {cnt:5d}  ({100*cnt/total:.1f}%)")
    print(f"\n  Written to: {outfile}")

    return trace_sec


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Realistic DNS traffic generator")
    parser.add_argument("--n",     type=int,   default=5000,
                        help="Number of DNS queries to generate (default: 5000)")
    parser.add_argument("--alpha", type=float, default=1.1,
                        help="Zipf exponent — higher = more skewed (default: 1.1)")
    parser.add_argument("--seed",  type=int,   default=42,
                        help="Random seed for reproducibility (default: 42)")
    parser.add_argument("--out",   type=str,   default="dns_traffic.txt",
                        help="Output file path (default: dns_traffic.txt)")
    args = parser.parse_args()

    generate(
        n_queries = args.n,
        alpha     = args.alpha,
        seed      = args.seed,
        outfile   = args.out,
    )