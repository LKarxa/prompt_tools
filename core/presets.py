"""
预设管理模块
"""
import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from astrbot.api import logger

from .extractor import PromptExtractor

class PresetsManager:
    """预设管理器类"""
    
    def __init__(self, presets_folder: Path, output_folder: Path):
        """
        初始化预设管理器
        
        Args:
            presets_folder: 预设JSON文件所在的文件夹路径
            output_folder: 提取的预设信息保存的文件夹路径
        """
        self.presets_folder = presets_folder
        self.output_folder = output_folder
        self.presets = {}  # 所有预设文件列表 {preset_name: [prompts]}
        self.prefix_prompts = {}  # 每个预设对应的前缀提示 {preset_name: prefix_content}
        
    def ensure_directory_exists(self, directory: Path) -> None:
        """确保目录存在，如果不存在则创建"""
        if not directory.exists():
            directory.mkdir(parents=True)
            logger.info(f"创建目录: {directory}")
    
    def extract_prompts(self) -> bool:
        """
        调用PromptExtractor提取提示词
        
        Returns:
            是否成功提取提示词
        """
        try:
            # 检查presets文件夹中是否有JSON文件
            json_files = list(self.presets_folder.glob("*.json"))
            if not json_files:
                logger.warning(f"在 {self.presets_folder} 中没有找到JSON文件，请先添加预设文件")
                return False
                
            extractor = PromptExtractor(
                presets_folder=str(self.presets_folder), 
                output_folder=str(self.output_folder)
            )
            extracted_prompts = extractor.extract_all_prompts()
            logger.info(f"成功提取提示词，共 {sum(len(prompts) for prompts in extracted_prompts.values())} 个")
            return True
        except Exception as e:
            logger.error(f"提取提示词时出错: {str(e)}")
            return False
    
    def load_presets(self) -> bool:
        """
        加载所有已提取的预设文件
        
        Returns:
            是否成功加载预设
        """
        try:
            # 清空当前数据
            self.presets = {}
            self.prefix_prompts = {}
            
            if not self.output_folder.exists():
                logger.warning(f"输出文件夹不存在: {self.output_folder}")
                # 尝试提取预设
                if not self.extract_prompts():
                    logger.warning("未能提取预设，请检查预设文件")
                return False
            
            # 获取所有预设文件夹
            preset_folders = [f for f in self.output_folder.iterdir() if f.is_dir()]
            
            if not preset_folders:
                logger.warning(f"在 {self.output_folder} 中没有找到预设文件夹")
                # 尝试提取预设
                if not self.extract_prompts():
                    logger.warning("未能提取预设，请检查预设文件")
                return False
            
            # 加载每个预设文件夹中的JSON文件
            for preset_folder in preset_folders:
                preset_name = preset_folder.name
                json_files = list(preset_folder.glob("*.json"))
                
                if not json_files:
                    logger.warning(f"在 {preset_folder} 中没有找到JSON文件")
                    continue
                
                # 加载普通提示
                prompts = []
                for json_file in json_files:
                    # 跳过前缀提示文件，我们会单独处理它
                    if json_file.name == "prompt_prefix.json":
                        continue
                        
                    try:
                        with open(json_file, 'r', encoding='utf-8') as f:
                            prompt_data = json.load(f)
                            # 过滤掉前缀提示和内容为空的提示
                            # 修复: 添加类型检查，确保content是字符串
                            content = prompt_data.get("content", "")
                            if not prompt_data.get("is_prefix", False):
                                if isinstance(content, str) and content.strip():
                                    prompts.append(prompt_data)
                                elif not isinstance(content, str):
                                    # 将非字符串转换为字符串并添加
                                    prompt_data["content"] = str(content)
                                    prompts.append(prompt_data)
                    except Exception as e:
                        logger.error(f"读取 {json_file} 时出错: {str(e)}")
                
                # 将加载的提示按文件名排序
                self.presets[preset_name] = prompts
                
                # 加载前缀提示
                prefix_file = preset_folder / "prompt_prefix.json"
                if prefix_file.exists():
                    try:
                        with open(prefix_file, 'r', encoding='utf-8') as f:
                            prefix_data = json.load(f)
                            prefix_content = prefix_data.get("content", "")
                            # 修复: 添加类型检查，确保content是字符串
                            if not isinstance(prefix_content, str):
                                prefix_content = str(prefix_content)
                            self.prefix_prompts[preset_name] = prefix_content
                    except Exception as e:
                        logger.error(f"读取前缀提示文件 {prefix_file} 时出错: {str(e)}")
                
                logger.info(f"已加载预设 {preset_name}，包含 {len(prompts)} 个提示")
            
            return len(self.presets) > 0
        
        except Exception as e:
            logger.error(f"加载预设时出错: {str(e)}")
            return False
    
    def get_preset_list(self) -> List[str]:
        """获取所有可用预设的列表"""
        return list(self.presets.keys())
    
    def get_prompts(self, preset_name: str) -> List[Dict[str, Any]]:
        """
        获取指定预设的所有提示
        
        Args:
            preset_name: 预设名称
            
        Returns:
            提示列表，如果预设不存在则返回空列表
        """
        return self.presets.get(preset_name, [])
    
    def get_prefix(self, preset_name: str) -> str:
        """
        获取指定预设的前缀提示内容
        
        Args:
            preset_name: 预设名称
            
        Returns:
            前缀提示内容，如果不存在则返回空字符串
        """
        return self.prefix_prompts.get(preset_name, "")
    
    def create_preset(self, name: str) -> bool:
        """
        创建新的预设文件夹
        
        Args:
            name: 预设名称
            
        Returns:
            是否成功创建预设
        """
        try:
            preset_folder = self.output_folder / name
            
            # 检查是否已存在
            if preset_folder.exists():
                logger.warning(f"预设 '{name}' 已经存在")
                return False
            
            # 创建文件夹
            self.ensure_directory_exists(preset_folder)
            
            # 初始化空预设
            self.presets[name] = []
            
            logger.info(f"已创建新预设: {name}")
            return True
            
        except Exception as e:
            logger.error(f"创建预设时出错: {str(e)}")
            return False