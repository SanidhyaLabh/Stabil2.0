import socket

target_ip = "10.185.236.109"
common_ports = [8080, 8081, 4747, 80, 8000, 5555]

print(f"Scanning {target_ip} for open camera ports...")

found = False
for port in common_ports:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1)
    result = s.connect_ex((target_ip, port))
    if result == 0:
        print(f"✅ FOUND OPEN PORT: {port}")
        found = True
    else:
        print(f"❌ Port {port} is closed")
    s.close()

if not found:
    print("\n⚠️ No common camera ports found. Please double check the IP and Port on the phone screen.")
else:
    print("\n✅ Try updating the URL with the open port found above.")
