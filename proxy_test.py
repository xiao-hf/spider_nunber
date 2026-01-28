import requests

targetURL = "https://test.ipw.cn"

api_url = "https://share.proxy.qg.net/get?key=90YNBP3V"
resp = requests.get(api_url, timeout=10)
resp.raise_for_status()
payload = resp.json()
proxyAddr = None
data = payload.get("data") or []
if isinstance(data, list):
    for item in data:
        if isinstance(item, dict) and item.get("server"):
            proxyAddr = item["server"]
            break
        if isinstance(item, dict) and isinstance(item.get("ips"), list):
            for ip_item in item["ips"]:
                if isinstance(ip_item, dict) and ip_item.get("server"):
                    proxyAddr = ip_item["server"]
                    break
        if proxyAddr:
            break
elif isinstance(data, dict):
    if isinstance(data.get("ips"), list):
        for ip_item in data["ips"]:
            if isinstance(ip_item, dict) and ip_item.get("server"):
                proxyAddr = ip_item["server"]
                break
    if proxyAddr is None and isinstance(data.get("tasks"), list):
        for task in data["tasks"]:
            if not isinstance(task, dict) or not isinstance(task.get("ips"), list):
                continue
            for ip_item in task["ips"]:
                if isinstance(ip_item, dict) and ip_item.get("server"):
                    proxyAddr = ip_item["server"]
                    break
            if proxyAddr:
                break
if proxyAddr is None:
    raise ValueError("proxyAddr not found in API response")

authKey = "90YNBP3V"
password = "53B4C93E166A"

proxyUrl = "http://%(user)s:%(password)s@%(server)s" % {
    "user": authKey,
    "password": password,
    "server": proxyAddr,
}
proxies = {
    "http": proxyUrl,
    "https": proxyUrl,
}
resp = requests.get(targetURL, proxies=proxies)
print(resp.text)
