"""
提示词管理模块
"""
import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from astrbot.api import logger

class PromptsManager:
    """提示词管理器类"""
    
    def __init__(self, output_folder: Path):
        """
        初始化提示词管理器
        
        Args:
            output_folder: 提示词保存的文件夹路径
        """
        self.output_folder = output_folder
        self.active_prompts = []  # 当前激活的提示列表，按激活顺序排列
    
    def ensure_directory_exists(self, directory: Path) -> None:
        """确保目录存在，如果不存在则创建"""
        if not directory.exists():
            directory.mkdir(parents=True)
            logger.info(f"创建目录: {directory}")
    
    def activate_prompts(self, preset_prompts: List[Dict[str, Any]], indices: List[int]) -> List[Dict[str, Any]]:
        """
        激活指定索引的提示，累加到已激活的提示上而不是替换它们
        
        Args:
            preset_prompts: 当前预设中的所有提示
            indices: 要激活的提示索引列表
            
        Returns:
            新激活的提示列表
        """
        newly_active_prompts = []
        
        for idx in indices:
            if 0 <= idx < len(preset_prompts):
                prompt = preset_prompts[idx]
                # 检查提示是否已经激活，避免重复添加
                if prompt not in self.active_prompts:
                    self.active_prompts.append(prompt)
                    newly_active_prompts.append(prompt)
            else:
                logger.warning(f"无效的提示索引: {idx}")
        
        return newly_active_prompts
    
    def deactivate_prompt(self, index: int) -> Optional[Dict[str, Any]]:
        """
        关闭指定索引的激活提示
        
        Args:
            index: 激活提示的索引
            
        Returns:
            被关闭的提示信息，如果索引无效则返回None
        """
        if index < 0 or index >= len(self.active_prompts):
            return None
        
        # 移除并返回指定索引的激活提示
        return self.active_prompts.pop(index)
    
    def clear_active_prompts(self) -> int:
        """
        清空所有激活的提示
        
        Returns:
            清空的提示数量
        """
        count = len(self.active_prompts)
        self.active_prompts = []
        return count
    
    def save_prompt_to_file(self, prompt: Dict[str, Any], preset_name: str) -> bool:
        """
        将提示词保存到文件
        
        Args:
            prompt: 包含name和content的提示词信息
            preset_name: 预设名称
            
        Returns:
            是否保存成功
        """
        try:
            preset_folder = self.output_folder / preset_name
            self.ensure_directory_exists(preset_folder)
            
            # 创建安全的文件名（替换不安全字符）
            name = prompt.get("name", "未命名")
            safe_name = "".join(c if c.isalnum() or c in [' ', '_', '-'] else '_' for c in name)
            safe_name = safe_name.strip().replace(' ', '_')
            
            # 为用户自定义提示词添加特殊标识
            if not safe_name.startswith("user_"):
                safe_name = f"user_{safe_name}"
                
            file_path = preset_folder / f"{safe_name}.json"
            
            # 添加identifier标识符，使用名称的小写和下划线版本
            if "identifier" not in prompt:
                prompt["identifier"] = safe_name.lower()
            
            # 将提示保存为JSON格式
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(prompt, f, ensure_ascii=False, indent=4)
            
            logger.info(f"保存提示词到JSON文件: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"保存提示词到文件时出错: {str(e)}")
            return False
    
    def add_prompt_to_preset(self, name: str, content: str, preset_name: str, presets: Dict[str, List[Dict[str, Any]]]) -> Optional[Dict[str, Any]]:
        """
        添加新提示词到指定预设
        
        Args:
            name: 提示词名称
            content: 提示词内容
            preset_name: 预设名称
            presets: 所有预设的字典
            
        Returns:
            添加的提示词信息，如果添加失败则返回None
        """
        if not preset_name:
            logger.warning("未指定预设名称，无法添加提示词")
            return None
        
        if not name or not content:
            logger.warning("提示词名称和内容不能为空")
            return None
        
        # 创建提示词数据结构
        prompt = {
            "name": name,
            "content": content,
            "is_prefix": False,
            "identifier": f"user_{name.lower().replace(' ', '_')}",
            "user_created": True,  # 标记为用户创建
            "created_at": None  # 可以添加创建时间
        }
        
        # 保存到文件
        if not self.save_prompt_to_file(prompt, preset_name):
            return None
        
        # 添加到内存中的预设
        if preset_name in presets:
            presets[preset_name].append(prompt)
            logger.info(f"已添加提示词 '{name}' 到预设 '{preset_name}'")
        else:
            presets[preset_name] = [prompt]
            logger.info(f"已创建预设 '{preset_name}' 并添加提示词 '{name}'")
        
        return prompt
    
    def delete_prompt(self, index: int, preset_name: str, preset_prompts: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        删除指定预设中指定索引的提示词
        
        Args:
            index: 提示词索引
            preset_name: 预设名称
            preset_prompts: 预设中的所有提示
            
        Returns:
            被删除的提示词信息，如果删除失败则返回None
        """
        if not preset_name:
            logger.warning("未指定预设名称，无法删除提示词")
            return None
        
        if index < 0 or index >= len(preset_prompts):
            logger.warning(f"无效的提示词索引: {index}")
            return None
        
        prompt = preset_prompts[index]
        name = prompt.get("name", "未命名")
        
        # 检查是否为用户创建的提示词
        if not prompt.get("user_created", False):
            logger.warning(f"提示词 '{name}' 不是由用户创建的，无法删除")
            return None
        
        # 从激活列表中删除
        if prompt in self.active_prompts:
            self.active_prompts.remove(prompt)
        
        # 从预设中删除
        preset_prompts.remove(prompt)
        
        # 尝试删除文件
        try:
            identifier = prompt.get("identifier", "")
            if identifier:
                preset_folder = self.output_folder / preset_name
                
                # 尝试使用不同的文件名模式
                possible_filenames = [
                    f"user_{identifier}.json",
                    f"{identifier}.json",
                    f"user_{name.replace(' ', '_')}.json",
                    f"{name.replace(' ', '_')}.json"
                ]
                
                deleted = False
                for filename in possible_filenames:
                    file_path = preset_folder / filename
                    if file_path.exists():
                        os.remove(file_path)
                        deleted = True
                        logger.info(f"已删除文件: {file_path}")
                        break
                
                if not deleted:
                    logger.warning(f"未找到要删除的文件，提示词 '{name}' 已从内存中移除但文件可能仍存在")
        
        except Exception as e:
            logger.error(f"删除提示词文件时出错: {str(e)}")
        
        return prompt