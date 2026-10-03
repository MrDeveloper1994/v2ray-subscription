import base64
import json
import urllib.request
from pathlib import Path


SOURCE_API = (
    "https://api.github.com/repos/"
    "V2RAYCONFIGSPOOL/V2RAY_SUB/git/trees/main?recursive=1"
)

SOURCE_RAW = (
    "https://raw.githubusercontent.com/"
    "V2RAYCONFIGSPOOL/V2RAY_SUB/main/"
)

OUTPUT_DIR = Path("subscriptions")

# Protocols that v2rayN can consume as URI links.
PROTOCOLS = (
    "vless://",
    "vmess://",
    "trojan://",
    "ss://",
    "ssr://",
    "socks://",
    "http://",
    "hysteria://",
    "hysteria2://",
    "hy2://",
    "tuic://",
)


def fetch(url: str) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "v2ray-subscription-updater",
            "Accept": "*/*",
        },
    )

    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def get_source_files() -> list[str]:
    data = json.loads(fetch(SOURCE_API).decode("utf-8"))

    files = []

    for item in data.get("tree", []):
        path = item.get("path", "")

        if item.get("type") != "blob":
            continue

        if not path.lower().endswith(".txt"):
            continue

        files.append(path)

    return sorted(files)


def extract_configs(text: str) -> list[str]:
    configs = []

    for raw_line in text.splitlines():
        line = raw_line.strip()

        if not line:
            continue

        # Keep the configuration exactly as supplied.
        # Only recognize supported URI schemes.
        if line.lower().startswith(PROTOCOLS):
            configs.append(line)

    return configs


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Getting source file list...")

    source_files = get_source_files()

    print(f"Found {len(source_files)} TXT files.")

    all_configs = []
    failed_files = []

    for path in source_files:
        url = SOURCE_RAW + path

        try:
            print(f"Downloading: {path}")

            content = fetch(url).decode(
                "utf-8",
                errors="ignore",
            )

            configs = extract_configs(content)

            print(f"  configs: {len(configs)}")

            all_configs.extend(configs)

        except Exception as exc:
            print(f"  FAILED: {exc}")
            failed_files.append(path)

    # Remove exact duplicates while preserving order.
    unique_configs = list(dict.fromkeys(all_configs))

    print()
    print(f"Total configs:  {len(all_configs)}")
    print(f"Unique configs: {len(unique_configs)}")

    if not unique_configs:
        raise RuntimeError(
            "No valid V2Ray configurations were found."
        )

    # ---------------------------------------------------------
    # Plain subscription
    # ---------------------------------------------------------

    plain = "\n".join(unique_configs) + "\n"

    plain_file = OUTPUT_DIR / "all.txt"

    plain_file.write_text(
        plain,
        encoding="utf-8",
    )

    # ---------------------------------------------------------
    # Base64 subscription
    # ---------------------------------------------------------

    encoded = base64.b64encode(
        plain.encode("utf-8")
    ).decode("ascii")

    base64_file = OUTPUT_DIR / "all-base64.txt"

    base64_file.write_text(
        encoded + "\n",
        encoding="utf-8",
    )

    # ---------------------------------------------------------
    # Statistics
    # ---------------------------------------------------------

    stats = {
        "source_files": len(source_files),
        "failed_files": failed_files,
        "total_configs": len(all_configs),
        "unique_configs": len(unique_configs),
    }

    stats_file = OUTPUT_DIR / "stats.json"

    stats_file.write_text(
        json.dumps(
            stats,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print()
    print("Subscription generated successfully.")
    print(f"Plain:  {plain_file}")
    print(f"Base64: {base64_file}")

    if failed_files:
        print()
        print("Failed files:")

        for file in failed_files:
            print(f" - {file}")


if __name__ == "__main__":
    main()
