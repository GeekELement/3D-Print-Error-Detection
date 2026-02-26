"""
设备管理模块

功能：检测和管理计算设备（GPU/CPU），支持CUDA加速
"""

import torch


class CudaUtils:
    """
    CUDA设备管理器
    
    自动检测GPU可用性，并根据配置决定是否使用CUDA加速
    
    使用示例：
        cuda_utils = CudaUtils(config)
        device = cuda_utils.get_device()  # 返回 'cuda' 或 'cpu'
        model.to(device)  # 将模型移到指定设备
    """
    
    def __init__(self, config=None):
        """
        初始化：检测CUDA可用性
        
        Args:
            config: 配置对象，用于读取 model.use_cuda 配置
        """
        self.config = config
        
        # 检测CUDA是否可用
        self.cuda_available = torch.cuda.is_available()
        # 获取GPU名称
        self.cuda_device_name = torch.cuda.get_device_name(0) if self.cuda_available else None
        self.should_use_cuda = False

        # 根据配置决定是否使用CUDA
        if self.cuda_available and config is not None:
            use_cuda = config.get_bool('model.use_cuda', True)
            self.should_use_cuda = use_cuda
        elif self.cuda_available:
            # 无配置时，默认使用CUDA（如果可用）
            self.should_use_cuda = True
    
    def get_info(self):
        """
        获取设备信息
        
        Returns:
            dict: 包含 available, device_name, should_use 的字典
        """
        return {
            'available': self.cuda_available,
            'device_name': self.cuda_device_name,
            'should_use': self.should_use_cuda
        }
    
    def print_info(self):
        """
        打印设备信息到控制台
        
        输出格式：
        - GPU可用：显示GPU名称
        - CUDA不可用：提示将使用CPU
        """
        if self.cuda_available:
            print(f"GPU可用: {self.cuda_device_name}")
        else:
            print("CUDA不可用，将使用CPU")
    
    def get_device(self):
        """
        获取设备字符串
        
        Returns:
            str: 'cuda' 或 'cpu'
        """
        return 'cuda' if self.should_use_cuda else 'cpu'