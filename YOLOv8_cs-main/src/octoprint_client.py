import requests

class OctoPrintClient:
    def __init__(self, octoprint_url, api_key):
        self.octoprint_url = octoprint_url
        self.api_key = api_key
        self.headers = {
            'X-Api-Key': api_key,
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
