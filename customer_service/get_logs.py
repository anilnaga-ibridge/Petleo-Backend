import sys
import psutil

if len(sys.argv) < 2:
    print("Usage: python get_logs.py <pid>")
    sys.exit(1)

pid = int(sys.argv[1])
try:
    p = psutil.Process(pid)
    print(f"Process {pid} name: {p.name()}")
    print("Use terminal output reader if supported, or check django app logs.")
except psutil.NoSuchProcess:
    print(f"No process found with pid {pid}")

