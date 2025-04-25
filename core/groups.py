"""
提示词组合管理模块
"""
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from astrbot.api import logger

class GroupsManager:
    """提示词组合管理器类"""
    
    def __init__(self, presets_folder: Path):
        """
        初始化提示词组合管理器
        
        Args:
            presets_folder: 预设JSON文件所在的文件夹路径
            注意：组合配置文件保存在 presets_folder 目录下，而不是 extracted 子目录，
            这样可以避免代码更新等问题造成组合丢失
        """
        self.presets_folder = presets_folder
        self.prompt_groups = {}  # 格式: {组名: [提示词索引列表]}
    
    def ensure_directory_exists(self, directory: Path) -> None:
        """确保目录存在，如果不存在则创建"""
        if not directory.exists():
            directory.mkdir(parents=True)
            logger.info(f"创建目录: {directory}")
    
    def load_prompt_groups(self, preset_name: str) -> bool:
        """
        加载指定预设的提示词组合配置
        
        Args:
            preset_name: 预设名称
            
        Returns:
            是否成功加载组合配置
        """
        try:
            # 清空当前组合数据
            self.prompt_groups = {}
            
            # 检查是否有组合配置文件
            groups_file = self.presets_folder / f"{preset_name}_groups.json"
            if not groups_file.exists():
                logger.info(f"未找到预设 '{preset_name}' 的组合配置文件")
                return False
            
            # 加载组合配置
            with open(groups_file, 'r', encoding='utf-8') as f:
                self.prompt_groups = json.load(f)
            
            logger.info(f"已加载预设 '{preset_name}' 的提示词组合配置: {len(self.prompt_groups)} 个组合")
            return True
        except Exception as e:
            logger.error(f"加载提示词组合配置时出错: {str(e)}")
            self.prompt_groups = {}
            return False
    
    def save_prompt_groups(self, preset_name: str) -> bool:
        """
        保存提示词组合配置
        
        Args:
            preset_name: 预设名称
            
        Returns:
            是否成功保存组合配置
        """
        try:
            # 确保目录存在
            self.ensure_directory_exists(self.presets_folder)
            
            # 保存组合配置
            groups_file = self.presets_folder / f"{preset_name}_groups.json"
            with open(groups_file, 'w', encoding='utf-8') as f:
                json.dump(self.prompt_groups, f, ensure_ascii=False, indent=4)
            
            logger.info(f"已保存预设 '{preset_name}' 的提示词组合配置: {len(self.prompt_groups)} 个组合")
            return True
        except Exception as e:
            logger.error(f"保存提示词组合配置时出错: {str(e)}")
            return False
    
    def create_prompt_group(self, group_name: str, indices: List[int], preset_name: str, preset_prompts: List[Dict[str, Any]]) -> bool:
        """
        创建提示词组合
        
        Args:
            group_name: 组合名称
            indices: 提示词索引列表
            preset_name: 预设名称
            preset_prompts: 预设中的所有提示
            
        Returns:
            是否成功创建组合
        """
        # 检查组合名称
        if not group_name:
            logger.warning("组合名称不能为空")
            return False
            
        # 检查组合名称是否已存在
        if group_name in self.prompt_groups:
            logger.warning(f"组合 '{group_name}' 已存在")
            return False
        
        # 验证索引有效性
        valid_indices = []
        
        for idx in indices:
            if 0 <= idx < len(preset_prompts):
                valid_indices.append(idx)
            else:
                logger.warning(f"无效的提示索引: {idx}")
        
        if not valid_indices:
            logger.warning("没有有效的提示词索引")
            return False
        
        # 保存组合
        self.prompt_groups[group_name] = valid_indices
        
        # 保存到文件
        result = self.save_prompt_groups(preset_name)
        
        return result
    
    def update_prompt_group(self, group_name: str, indices: List[int], preset_name: str, preset_prompts: List[Dict[str, Any]]) -> bool:
        """
        更新提示词组合
        
        Args:
            group_name: 组合名称
            indices: 提示词索引列表
            preset_name: 预设名称
            preset_prompts: 预设中的所有提示
            
        Returns:
            是否成功更新组合
        """
        # 检查组合是否存在
        if group_name not in self.prompt_groups:
            logger.warning(f"组合 '{group_name}' 不存在")
            return False
        
        # 验证索引有效性
        valid_indices = []
        
        for idx in indices:
            if 0 <= idx < len(preset_prompts):
                valid_indices.append(idx)
            else:
                logger.warning(f"无效的提示索引: {idx}")
        
        if not valid_indices:
            logger.warning("没有有效的提示词索引")
            return False
        
        # 更新组合
        self.prompt_groups[group_name] = valid_indices
        
        # 保存到文件
        result = self.save_prompt_groups(preset_name)
        
        return result
    
    def delete_prompt_group(self, group_name: str, preset_name: str) -> bool:
        """
        删除提示词组合
        
        Args:
            group_name: 组合名称
            preset_name: 预设名称
            
        Returns:
            是否成功删除组合
        """
        # 检查组合是否存在
        if group_name not in self.prompt_groups:
            logger.warning(f"组合 '{group_name}' 不存在")
            return False
        
        # 删除组合
        del self.prompt_groups[group_name]
        
        # 保存到文件
        result = self.save_prompt_groups(preset_name)
        
        return result
    
    def get_prompt_group(self, group_name: str) -> List[int]:
        """
        获取提示词组合
        
        Args:
            group_name: 组合名称
            
        Returns:
            提示词索引列表，如果组合不存在则返回空列表
        """
        return self.prompt_groups.get(group_name, [])
    
    def get_all_groups(self) -> Dict[str, List[int]]:
        """
        获取所有提示词组合
        
        Returns:
            提示词组合字典
        """
        return self.prompt_groups