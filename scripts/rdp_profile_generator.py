from pathlib import Path
import argparse

TEMPLATE = """full address:s:{host}:{port}
username:s:{username}
screen mode id:i:2
use multimon:i:0
session bpp:i:32
prompt for credentials:i:0
redirectclipboard:i:1
audiocapturemode:i:0
redirectprinters:i:0
redirectcomports:i:0
redirectsmartcards:i:0
redirectposdevices:i:0
autoreconnection enabled:i:1
authentication level:i:2
negotiate security layer:i:1
remoteapplicationmode:i:0
alternate shell:s:
shell working directory:s:
gatewayhostname:s:{gateway}
gatewayusagemethod:i:{gw_method}
gatewaycredentialssource:i:4
drivestoredirect:s:
"""


def main():
    ap = argparse.ArgumentParser(description="Generate a one-tap .rdp profile")
    ap.add_argument("--host", required=True, help="RDP host or IP")
    ap.add_argument("--port", default="3389")
    ap.add_argument("--username", default="")
    ap.add_argument("--gateway", default="")
    ap.add_argument("--gw-method", default="1")  # 1=Detect, 2=Always, 0=Never
    ap.add_argument("--out", default="public/rdp/desktop.rdp")
    args = ap.parse_args()

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    content = TEMPLATE.format(
        host=args.host, port=args.port, username=args.username,
        gateway=args.gateway, gw_method=args.gw_method
    )
    Path(args.out).write_text(content, encoding="utf-8")
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()

