import requests
from config_loader import config

class OctoPrintClient:
    def __init__(self, octoprint_url: str = "", api_key: str = ""):
        # 如果没有传入参数，使用配置文件中的默认值
        self.octoprint_url = octoprint_url if octoprint_url else config.get_str('octoprint.url', '')
        self.api_key = api_key if api_key else config.get_str('octoprint.api_key', '')
        
        # 检查必要的配置
        if not self.octoprint_url or not self.api_key:
            raise ValueError("OctoPrint URL 和 API Key 必须配置")
        
        self.headers = {
            'X-Api-Key': self.api_key,
            'Content-Type': 'application/json'
        }
    
    def get_printer_status(self):
        """获取打印机状态"""
        url = f"{self.octoprint_url}/api/printer"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def stop_print(self):
        """停止当前打印任务"""
        url = f"{self.octoprint_url}/api/job"
        data = {"command": "cancel"}
        response = requests.post(url, headers=self.headers, json=data)
        response.raise_for_status()
        return response.json()
    
    def pause_print(self):
        """暂停当前打印任务"""
        url = f"{self.octoprint_url}/api/job"
        data = {"command": "pause", "action": "pause"}
        response = requests.post(url, headers=self.headers, json=data)
        response.raise_for_status()
        return response.json()
    
    def resume_print(self):
        """恢复当前打印任务"""
        url = f"{self.octoprint_url}/api/job"
        data = {"command": "pause", "action": "resume"}
        response = requests.post(url, headers=self.headers, json=data)
        response.raise_for_status()
        return response.json()
    
    def get_job_status(self):
        """获取当前打印任务状态"""
        url = f"{self.octoprint_url}/api/job"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()
