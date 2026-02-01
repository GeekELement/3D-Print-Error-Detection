# config_loader.py - 简化版 YAML 配置加载器
import os
import yaml
from pathlib import Path

class Config:
    """YAML 配置文件加载器"""
    
    def __init__(self):
        config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f) or {}
        except FileNotFoundError:
            raise FileNotFoundError(f"配置文件不存在: {config_path}")
        except yaml.YAMLError as e:
            raise ValueError(f"YAML 格式错误: {e}")
        
        self._process_paths()
    
    def _process_paths(self):
        """处理路径，计算绝对路径"""
        base_dir = Path(__file__).parent
        
        # 项目根目录
        project_root = Path(self.config.get('directories', {}).get('project_root', '..'))
        if not project_root.is_absolute():
            project_root = base_dir / project_root
        
        # 计算完整路径
        dirs = self.config.get('directories', {})
        self.config['predicted_dir_abs'] = str(project_root / dirs.get('predicted_dir', 'images/predicted_pictures'))
        self.config['captured_dir_abs'] = str(project_root / dirs.get('captured_dir', 'images/saved_pictures'))
        
        # 模型文件完整路径
        model_config = self.config.get('model', {})
        model_path = Path(model_config.get('path', 'yolov8n.pt'))
        if not model_path.is_absolute():
            model_path = project_root / model_path
        self.config['model_path_abs'] = str(model_path)
    
    def get_str(self, path, default=""):
        """获取字符串配置值"""
        value = self.get(path, default)
        return str(value) if value is not None else default
    
    def get_int(self, path, default=0):
        """获取整数配置值"""
        value = self.get(path, default)
        try:
            return int(value) if value is not None else default
        except (ValueError, TypeError):
            return default
    
    def get_float(self, path, default=0.0):
        """获取浮点数配置值"""
        value = self.get(path, default)
        try:
            return float(value) if value is not None else default
        except (ValueError, TypeError):
            return default
    
    def get_bool(self, path, default=False):
        """获取布尔配置值"""
        value = self.get(path, default)
        return bool(value) if value is not None else default
    
    def get(self, path, default=None):
        """获取配置值，支持点号分隔的路径，如 'model.conf_threshold'"""
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
        """验证配置"""
        errors = []
        
        # 检查模型文件
        model_path = self.get_str('model_path_abs')
        if model_path and not os.path.exists(str(model_path)):
            errors.append(f"模型文件不存在: {model_path}")
        
        # 检查邮件配置
        if self.get_bool('email.enabled'):
            if not all([self.get_str('email.to'), self.get_str('email.from'), self.get_str('email.password')]):
                errors.append("启用邮件报警但邮箱配置不完整")
        
        # 确保目录存在
        try:
            predicted_dir = self.get_str('predicted_dir_abs')
            captured_dir = self.get_str('captured_dir_abs')
            if predicted_dir:
                os.makedirs(predicted_dir, exist_ok=True)
            if captured_dir:
                os.makedirs(captured_dir, exist_ok=True)
        except Exception as e:
            errors.append(f"创建目录失败: {e}")
        
        return errors

# 全局配置实例
config = Config()