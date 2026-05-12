import network, time, socket, struct, urequests
NTP_HOST = 'pool.ntp.org'

WEEKDAYS = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday"
]

MONTHS = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December"
]

class WiFi:
    def __init__(self):
        self.wlan = network.WLAN(network.STA_IF)
        self.wlan.active(True)


    def connect(self, ssid: str, password: str, timeout: int = 10):
        if self.wlan.isconnected():
            print("Already connected.")
            print(f"IP address: {self.wlan.ifconfig()[0]}")
            return self.wlan.ifconfig()

        print(f"Connecting to {ssid}...")
        self.wlan.active(True)
        self.wlan.connect(ssid, password)

        start = time.ticks_ms()
        while not self.wlan.isconnected():
            if time.ticks_diff(time.ticks_ms(), start) > (timeout * 1000):
                raise RuntimeError("Wi-Fi connection timed out.")
            time.sleep(0.5)

        print("Connected!")
        print("IP address:", self.wlan.ifconfig()[0])
        return self.wlan.ifconfig()

    def disconnect(self):
        if self.wlan.isconnected():
            self.wlan.disconnect()
            print("Disconnected from Wi-Fi.")

    def is_connected(self):
        return self.wlan.isconnected()

    def ip(self):
        return self.wlan.ifconfig()[0] if self.is_connected() else None
    
    def scan(self):
        nets = self.wlan.scan()
        return [(ssid.decode(), rssi) for ssid, bssid, ch, rssi, authmode, hidden in nets]

    
    def get_time(self, gmt=5, formatted=False):
        NTP_DELTA = 2208988800
        NTP_QUERY = bytearray(48)
        NTP_QUERY[0] = 0x1B
        gmt_offset = gmt * 3600
        addr = socket.getaddrinfo(NTP_HOST, 123)[0][-1]
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.settimeout(1)
            res = s.sendto(NTP_QUERY, addr)
            msg = s.recv(48)
        finally:
            s.close()
        ntp_time = struct.unpack("!I", msg[40:44])[0]
        result = time.gmtime(ntp_time - NTP_DELTA + gmt_offset)
        if formatted:
            return f"{MONTHS[result[1]-1]} {result[2]}, {result[0]} {WEEKDAYS[result[6]]} {result[3]:02}:{result[4]:02}:{result[5]:02}"
        else:
            return result 

    def get_currency(self, from_currency="USD", to_currency="KZT"):
        """
        Convert an amount from one currency to another using live exchange rates.

        Args:
            from_currency (str): Source currency code (e.g., "USD").
            to_currency (str): Target currency code (e.g., "KZT").

        Returns:
            float: Converted amount in target currency, or None if request fails.
        """
        try:
            url = f"https://open.er-api.com/v6/latest/{from_currency}"
            r = urequests.get(url)
            data = r.json()
            r.close()
            return float(data["rates"][to_currency])
        except Exception as e:
            print("Error converting currency:", e)
            return None

    def get_temperature(self, city="Astana"):
        """
        Fetch current weather data for the given city.
        Defaults to Astana.

        Args:
            city (str): City name (default: "Astana")

        Returns:
            dict: Weather data including temperature, description, humidity.
        """
        try:
            # Open-Meteo is free and doesn’t require an API key
            url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=en&format=json"
            r = urequests.get(url)
            geo = r.json()
            r.close()
            lat = geo["results"][0]["latitude"]
            lon = geo["results"][0]["longitude"]

            url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
            r = urequests.get(url)
            data = r.json()
            r.close()

            temp = data["current_weather"]["temperature"]
            return f"{temp} C"
        except Exception as e:
            print("Error fetching weather:", e)
            return None

    def get_ip_info(self):
        """
        Fetch public IP address and location info.

        Returns:
            dict: Dictionary with IP, city, region, country.
        """
        try:
            url = "http://ip-api.com/json"
            r = urequests.get(url)
            data = r.json()
            r.close()
            return data
        except Exception as e:
            print("Error fetching IP info:", e)
            return None
    
    def status(self):
        return {
            "connected": self.is_connected(),
            "ip": self.ip(),
            "ssid": self.wlan.config('ssid') if self.is_connected() else None,
            "rssi": self.wlan.status('rssi') if self.is_connected() else None,
            "time": self.get_time(formatted=True)
        }
   

