"""
配置管理模块

功能：加载并管理YAML配置文件，提供类型安全的配置读取接口，
      支持路径自动计算、配置验证和目录创建。
"""

import os
import yaml
from pathlib import Path


class Config:
    """
    YAML配置文件加载器
    
    使用示例：
        config = Config()
        interval = config.get_float('monitoring.interval_sec', 1)
        use_cuda = config.get_bool('model.use_cuda', True)
    """
    
    def __init__(self):
        """
        初始化：读取配置文件并处理路径
        """
        # 项目根目录 = 配置文件所在目录的父目录
        base_dir = Path(__file__).parent.parent
        config_path = base_dir / "config.yaml"
        
        # 读取YAML配置
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f) or {}
        except FileNotFoundError:
            raise FileNotFoundError(f"配置文件不存在: {config_path}")
        except yaml.YAMLError as e:
            raise ValueError(f"YAML 格式错误: {e}")
        
        # 处理相对路径，计算绝对路径
        self._process_paths()
    
    def _process_paths(self):
        """
        处理配置文件中的路径，将相对路径转换为绝对路径
        
        涉及：
        - predicted_dir: 预测图片保存目录
        - captured_dir: 原始图片保存目录
        - model_path: YOLO模型文件路径
        """
        base_dir = Path(__file__).parent
        
        # 项目根目录（相对于配置文件所在目录）
        project_root = Path(self.config.get('directories', {}).get('project_root', '..'))
        if not project_root.is_absolute():
            project_root = base_dir / project_root
        
        # 计算图片保存目录的绝对路径
        dirs = self.config.get('directories', {})
        self.config['predicted_dir_abs'] = str(project_root / dirs.get('predicted_dir', 'images/predicted'))
        self.config['captured_dir_abs'] = str(project_root / dirs.get('captured_dir', 'images/captured'))
        
        # 计算模型文件的绝对路径
        model_config = self.config.get('model', {})
        model_path = Path(model_config.get('path', 'yolov8n.pt'))
        if not model_path.is_absolute():
            model_path = project_root / model_path
        self.config['model_path_abs'] = str(model_path)
    
    def get_str(self, path, default=""):
        """
        获取字符串配置值
        
        Args:
            path: 配置路径，使用点号分隔，如 'email.smtp.server'
            default: 默认值
            
        Returns:
            str: 配置值或默认值
        """
        value = self.get(path, default)
        return str(value) if value is not None else default
    
    def get_int(self, path, default=0):
        """
        获取整数配置值
        
        Args:
            path: 配置路径
            default: 默认值
             
        Returns:
            int: 配置值或默认值（转换失败时返回默认值）
        """
        value = self.get(path, default)
        try:
            return int(value) if value is not None else default
        except (ValueError, TypeError):
            return default
    
    def get_float(self, path, default=0.0):
        """
        获取浮点数配置值
        
        Args:
            path: 配置路径
            default: 默认值
             
        Returns:
            float: 配置值或默认值（转换失败时返回默认值）
        """
        value = self.get(path, default)
        try:
            return float(value) if value is not None else default
        except (ValueError, TypeError):
            return default
    
    def get_bool(self, path, default=False):
        """
        获取布尔配置值
        
        Args:
            path: 配置路径
            default: 默认值
             
        Returns:
            bool: 配置值或默认值
        """
        value = self.get(path, default)
        return bool(value) if value is not None else default
    
    def get(self, path, default=None):
        """
        获取配置值，支持点号分隔的嵌套路径
        
        Args:
            path: 配置路径，如 'model.conf_threshold'
            default: 默认值
            
        Returns:
            配置值或默认值
        """
        keys = path.split('.')
        value = self.config
        
        try:
            for key in keys:
                if isinstance(value, dict):
                    value = value.get(key, default)
                else:
                    return default
            return value
        except (KeyError, TypeError):
            return default
    
    def validate(self):
        """
        验证配置合法性
        
        检查项：
        - 模型文件是否存在
        - 邮件配置是否完整（如果启用邮件）
        - 目录是否存在
        
        Returns:
            list: 错误信息列表，空列表表示验证通过
        """
        errors = []
        
        # 检查模型文件
        model_path = self.get_str('model_path_abs')
        if model_path and not os.path.exists(str(model_path)):
            errors.append(f"模型文件不存在: {model_path}")
        
        # 检查邮件配置（如果启用）
        if self.get_bool('email.enabled'):
            if not all([self.get_str('email.to'), self.get_str('email.from'), self.get_str('email.password')]):
                errors.append("启用邮件报警但邮箱配置不完整")
        
        # 检查目录是否存在
        predicted_dir = self.get_str('predicted_dir_abs')
        captured_dir = self.get_str('captured_dir_abs')
        for d in [predicted_dir, captured_dir]:
            if d and not os.path.exists(d):
                errors.append(f"目录不存在: {d}")
        
        return errors
    
    def ensure_directories(self):
        """
        确保必要的目录存在，不存在则自动创建
        
        涉及目录：
        - predicted_dir_abs: 预测图片保存目录
        - captured_dir_abs: 原始图片保存目录
        """
        for key in ['predicted_dir_abs', 'captured_dir_abs']:
            d = self.get_str(key)
            if d:
                os.makedirs(d, exist_ok=True)


# 全局配置实例，整个程序共享一份配置
config = Config()