"""
提示词组合管理模块
"""
import json
import traceback
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
        try:
            if not directory.exists():
                directory.mkdir(parents=True)
                logger.info(f"创建目录: {directory}")
        except OSError as e:
            logger.error(f"创建目录 {directory} 失败: {e}", exc_info=True)
            raise
    
    def load_prompt_groups(self, preset_name: str) -> bool:
        """
        加载指定预设的提示词组合配置
        
        Args:
            preset_name: 预设名称
            
        Returns:
            是否成功加载组合配置 (True even if file doesn't exist)
        """
        logger.info(f"尝试为预设 '{preset_name}' 加载组合配置...")
        groups_file = self.presets_folder / f"{preset_name}_groups.json"
        try:
            # 清空当前组合数据
            self.prompt_groups = {}
            
            if not groups_file.exists():
                logger.info(f"未找到预设 '{preset_name}' 的组合配置文件 ({groups_file})，将使用空组合")
                return True
            
            # 加载组合配置
            with open(groups_file, 'r', encoding='utf-8') as f:
                loaded_data = json.load(f)
                if not isinstance(loaded_data, dict):
                    logger.error(f"组合配置文件 {groups_file} 格式错误：顶层不是字典")
                    return False
                self.prompt_groups = loaded_data
            
            logger.info(f"已加载预设 '{preset_name}' 的提示词组合配置: {len(self.prompt_groups)} 个组合")
            return True
        except (IOError, json.JSONDecodeError) as e:
            logger.error(f"加载提示词组合配置 {groups_file} 时出错: {e}", exc_info=True)
            self.prompt_groups = {}
            return False
        except Exception as e:
            logger.error(f"加载组合配置 {groups_file} 时发生意外错误: {e}", exc_info=True)
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
        logger.debug(f"准备为预设 '{preset_name}' 保存组合配置...")
        groups_file = self.presets_folder / f"{preset_name}_groups.json"
        try:
            self.ensure_directory_exists(self.presets_folder)
            
            with open(groups_file, 'w', encoding='utf-8') as f:
                json.dump(self.prompt_groups, f, ensure_ascii=False, indent=4)
            
            logger.info(f"已保存预设 '{preset_name}' 的提示词组合配置 ({groups_file}): {len(self.prompt_groups)} 个组合")
            return True
        except (IOError, TypeError) as e:
            logger.error(f"保存提示词组合配置 {groups_file} 时出错: {e}", exc_info=True)
            return False
        except Exception as e:
            logger.error(f"保存组合配置 {groups_file} 时发生意外错误: {e}", exc_info=True)
            return False
    
    def create_prompt_group(self, group_name: str, indices: List[int], preset_name: str, preset_prompts: List[Dict[str, Any]]) -> bool:
        logger.info(f"请求为预设 '{preset_name}' 创建组合 '{group_name}'")
        
        if not group_name:
            logger.warning("组合名称不能为空")
            return False
            
        if group_name in self.prompt_groups:
            logger.warning(f"组合 '{group_name}' 在预设 '{preset_name}' 中已存在")
            return False
        
        valid_indices = []
        invalid_indices = []
        max_index = len(preset_prompts) - 1
        
        for idx in indices:
            if 0 <= idx <= max_index:
                valid_indices.append(idx)
            else:
                invalid_indices.append(idx)
        
        if invalid_indices:
            logger.warning(f"创建组合 '{group_name}' 时发现无效索引: {invalid_indices} (有效范围 0-{max_index})")
        
        if not valid_indices:
            logger.error(f"创建组合 '{group_name}' 失败：没有提供有效的提示词索引")
            return False
        
        unique_sorted_indices = sorted(list(set(valid_indices)))
        self.prompt_groups[group_name] = unique_sorted_indices
        logger.debug(f"组合 '{group_name}' (内存) 设置为: {unique_sorted_indices}")
        
        if self.save_prompt_groups(preset_name):
            logger.info(f"成功创建并保存组合 '{group_name}'")
            return True
        else:
            logger.error(f"创建组合 '{group_name}' 后保存失败，内存状态可能与文件不一致")
            return False
    
    def update_prompt_group(self, group_name: str, indices: List[int], preset_name: str, preset_prompts: List[Dict[str, Any]]) -> bool:
        logger.info(f"请求更新预设 '{preset_name}' 的组合 '{group_name}'")
        
        if group_name not in self.prompt_groups:
            logger.warning(f"尝试更新的组合 '{group_name}' 在预设 '{preset_name}' 中不存在")
            return False
        
        valid_indices = []
        invalid_indices = []
        max_index = len(preset_prompts) - 1
        
        for idx in indices:
            if 0 <= idx <= max_index:
                valid_indices.append(idx)
            else:
                invalid_indices.append(idx)
        
        if invalid_indices:
            logger.warning(f"更新组合 '{group_name}' 时发现无效索引: {invalid_indices} (有效范围 0-{max_index})")
        
        if not valid_indices:
            logger.warning(f"更新组合 '{group_name}' 失败：没有提供有效的提示词索引。组合将变为空。")
        
        unique_sorted_indices = sorted(list(set(valid_indices)))
        self.prompt_groups[group_name] = unique_sorted_indices
        logger.debug(f"组合 '{group_name}' (内存) 更新为: {unique_sorted_indices}")
        
        if self.save_prompt_groups(preset_name):
            logger.info(f"成功更新并保存组合 '{group_name}'")
            return True
        else:
            logger.error(f"更新组合 '{group_name}' 后保存失败")
            return False
    
    def delete_prompt_group(self, group_name: str, preset_name: str) -> bool:
        logger.info(f"请求删除预设 '{preset_name}' 的组合 '{group_name}'")
        
        if group_name not in self.prompt_groups:
            logger.warning(f"尝试删除的组合 '{group_name}' 在预设 '{preset_name}' 中不存在")
            return False
        
        del self.prompt_groups[group_name]
        logger.debug(f"组合 '{group_name}' 已从内存中删除")
        
        if self.save_prompt_groups(preset_name):
            logger.info(f"成功删除并保存组合 '{group_name}' 的更改")
            return True
        else:
            logger.error(f"删除组合 '{group_name}' 后保存失败")
            return False
    
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