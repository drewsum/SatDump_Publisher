import argparse


def main():
    parser = argparse.ArgumentParser(prog="satdump_publisher", description="SatDump Publisher - minimal CLI")
    parser.add_argument("--message", "-m", default="Hello from satdump_publisher", help="Message to publish")
    args = parser.parse_args()
    print(args.message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
