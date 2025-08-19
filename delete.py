import socket

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("0.0.0.0", 11123))

print("Listening for GPS data on port 11123...")
while True:
    data, addr = sock.recvfrom(1024)
    print("From phone:", data.decode().strip())
