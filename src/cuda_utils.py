import torch


class CudaUtils:
    """CUDA工具类"""

    def __init__(self, config=None):
        self.config = config
        self.cuda_available = torch.cuda.is_available()
        self.cuda_device_name = torch.cuda.get_device_name(0) if self.cuda_available else None
        self.should_use_cuda = False

        if self.cuda_available and config is not None:
            use_cuda = config.get_bool('model.use_cuda', True)
            self.should_use_cuda = use_cuda
        elif self.cuda_available:
            self.should_use_cuda = True

    def get_info(self):
        """获取CUDA信息"""
        return {
            'available': self.cuda_available,
            'device_name': self.cuda_device_name,
            'should_use': self.should_use_cuda
        }

    def print_info(self):
        """打印CUDA信息"""
        if self.cuda_available:
            print(f"GPU可用: {self.cuda_device_name}")
        else:
            print("CUDA不可用，将使用CPU")

    def get_device(self):
        """获取设备字符串"""
        return 'cuda' if self.should_use_cuda else 'cpu'
