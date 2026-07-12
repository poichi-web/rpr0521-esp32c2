import network, time, sys, socket
import wifi_secrets

wlan = network.WLAN(network.STA_IF)
wlan.active(True)
if not wlan.isconnected():
    wlan.connect(wifi_secrets.SSID, wifi_secrets.PASSWORD)
    t0 = time.ticks_ms()
    while not wlan.isconnected():
        if time.ticks_diff(time.ticks_ms(), t0) > 15000:
            sys.stdout.write("WiFi connect TIMEOUT\r\n")
            raise SystemExit
        time.sleep_ms(200)

sys.stdout.write("WiFi connected: {}\r\n".format(wlan.ifconfig()))

# DNS resolution test
for host in ["pool.ntp.org", "ntp.nict.jp", "time.google.com"]:
    try:
        addr = socket.getaddrinfo(host, 123)[0][-1]
        sys.stdout.write("DNS {} -> {}\r\n".format(host, addr))
    except Exception as e:
        sys.stdout.write("DNS {} FAILED: {}\r\n".format(host, e))

import ntptime
sys.stdout.write("ntptime.host = {}\r\n".format(getattr(ntptime, "host", "?")))
try:
    ntptime.timeout = 5
except Exception:
    pass

for host in ["pool.ntp.org", "ntp.nict.jp", "time.google.com"]:
    try:
        ntptime.host = host
        ntptime.settime()
        sys.stdout.write("NTP OK via {} -> RTC UTC now: {}\r\n".format(host, time.localtime()))
        break
    except Exception as e:
        sys.stdout.write("NTP {} FAILED: {}\r\n".format(host, e))
