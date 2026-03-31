import csv

input_file = "Traffic.txt"
output_file = "dns_traffic.txt"

time_counter = 1

with open(input_file, "r", encoding="utf-8") as f, open(output_file, "w") as out:
    reader = csv.DictReader(f)

    for row in reader:
        info = row["Info"]

        # Look for DNS query
        if "Standard query" in info:
            parts = info.split()

            for p in parts:
                if "." in p and not p.endswith("."):
                    domain = p.strip()

                    # remove unwanted reverse DNS
                    if "arpa" in domain:
                        continue

                    out.write(f"{time_counter} {domain}\n")
                    time_counter += 1
                    break

print("✅ Converted to clean dns_traffic.txt")