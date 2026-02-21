"""
Klipper 控制模块
功能：通过 Moonraker API 直接控制 Klipper 打印机
"""
import requests
from config_loader import config


class KlipperClient:
    """Klipper Moonraker API 客户端"""

    def __init__(self, klipper_url: str = "", api_key: str = ""):
        self.klipper_url = klipper_url if klipper_url else config.get_str('klipper.url', '')
        self.api_key = api_key if api_key else config.get_str('klipper.api_key', '')
        
        if not self.klipper_url:
            raise ValueError("Klipper URL 必须配置")
        
        self.headers = {
            'Content-Type': 'application/json'
        }
        if self.api_key:
            self.headers['X-API-Key'] = self.api_key

    def _request(self, method: str, endpoint: str, data: dict = None):
        """发送 HTTP 请求"""
        url = f"{self.klipper_url}{endpoint}"
        try:
            if method.upper() == "POST":
                response = requests.post(url, headers=self.headers, json=data, timeout=10)
            else:
                response = requests.get(url, headers=self.headers, timeout=10)
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Klipper API 请求失败：{e}")
            return None

    def stop_print(self):
        """停止当前打印任务"""
        return self._request("POST", "/api/job/cancel")

    def pause_print(self):
        """暂停打印"""
        return self._request("POST", "/api/job/pause")

    def resume_print(self):
        """恢复打印"""
        return self._request("POST", "/api/job/resume")

    def get_job_status(self):
        """获取打印任务状态"""
        return self._request("GET", "/api/job")

    def get_printer_status(self):
        """获取打印机状态"""
        return self._request("GET", "/apiPrinterStatus")


if __name__ == "__main__":
    client = KlipperClient()
    print("Klipper 客户端测试")
    print("停止打印...")
    client.stop_print()
