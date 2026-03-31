import socket
import random
import time

domains = [
    "google.com", "youtube.com", "amazon.in", "facebook.com",
    "instagram.com", "netflix.com", "twitter.com", "reddit.com",
    "github.com", "stackoverflow.com"
]

def generate_real_dns_traffic(n=200):
    for _ in range(n):
        domain = random.choice(domains)

        try:
            socket.gethostbyname(domain)  # DNS query
            print("Resolved:", domain)
        except:
            pass

        time.sleep(random.uniform(0.1, 0.5))  # simulate user delay

generate_real_dns_traffic()