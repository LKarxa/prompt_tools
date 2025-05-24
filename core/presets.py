"""
预设管理模块
"""
import json
import os
import traceback
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
        try:
            if not directory.exists():
                directory.mkdir(parents=True)
                logger.info(f"创建目录: {directory}")
        except OSError as e:
            logger.error(f"创建目录 {directory} 失败: {e}", exc_info=True)
            raise
    
    def extract_prompts(self) -> bool:
        """
        调用PromptExtractor提取提示词
        
        Returns:
            是否成功提取提示词
        """
        logger.info(f"开始从 {self.presets_folder} 提取提示词到 {self.output_folder}")
        try:
            # 检查presets文件夹中是否有JSON文件
            json_files = list(self.presets_folder.glob("*.json"))
            if not json_files:
                logger.warning(f"在 {self.presets_folder} 中没有找到支持的预设文件 (e.g., .json)，提取中止")
                return True

            extractor = PromptExtractor(
                presets_folder=str(self.presets_folder),
                output_folder=str(self.output_folder)
            )
            extracted_prompts = extractor.extract_all_prompts()
            total_extracted = sum(len(prompts) for prompts in extracted_prompts.values())
            logger.info(f"成功提取提示词，共 {total_extracted} 个")
            return True
        except Exception as e:
            logger.error(f"提取提示词时出错: {e}\n{traceback.format_exc()}")
            return False
    
    def load_presets(self) -> bool:
        """
        加载所有已提取的预设文件
        
        Returns:
            是否成功加载预设
        """
        logger.info(f"开始从 {self.output_folder} 加载预设...")
        try:
            # 清空当前数据
            self.presets = {}
            self.prefix_prompts = {}
            
            if not self.output_folder.exists():
                logger.warning(f"输出文件夹不存在: {self.output_folder}，无法加载预设")
                return False

            # 获取所有预设文件夹
            preset_folders = [f for f in self.output_folder.iterdir() if f.is_dir()]
            
            if not preset_folders:
                logger.warning(f"在 {self.output_folder} 中没有找到预设文件夹，加载中止")
                return False

            # 加载每个预设文件夹中的JSON文件
            loaded_count = 0
            for preset_folder in preset_folders:
                preset_name = preset_folder.name
                json_files = list(preset_folder.glob("*.json"))
                
                if not json_files:
                    logger.warning(f"在预设文件夹 {preset_folder} 中没有找到JSON文件，跳过")
                    continue
                
                # 加载普通提示
                prompts = []
                preset_prefix = ""
                for json_file in json_files:
                    try:
                        with open(json_file, 'r', encoding='utf-8') as f:
                            prompt_data = json.load(f)
                            
                            # 检查是否是列表格式的数据
                            if isinstance(prompt_data, list):
                                # 如果是列表，遍历每个元素
                                for item in prompt_data:
                                    if isinstance(item, dict):
                                        # Check if it's a prefix prompt
                                        if item.get("is_prefix", False) or json_file.name == "prompt_prefix.json":
                                            content = item.get("content", "")
                                            if not isinstance(content, str):
                                                content = str(content)
                                            if preset_prefix:
                                                logger.warning(f"预设 '{preset_name}' 发现多个前缀提示，将使用 '{json_file.name}' 的内容")
                                            preset_prefix = content
                                            continue

                                        # Add regular prompts
                                        content = item.get("content", "")
                                        if isinstance(content, str) and content.strip():
                                            prompts.append(item)
                                        elif not isinstance(content, str):
                                            logger.debug(f"提示词 '{item.get('name', '未命名')}' 在 '{preset_name}' 中的内容不是字符串，已转换为: '{str(content)}'")
                                            item["content"] = str(content)
                                            prompts.append(item)
                            elif isinstance(prompt_data, dict):
                                # 原有的字典格式处理逻辑
                                # Check if it's a prefix prompt
                                if prompt_data.get("is_prefix", False) or json_file.name == "prompt_prefix.json":
                                    content = prompt_data.get("content", "")
                                    if not isinstance(content, str):
                                        content = str(content)
                                    if preset_prefix:
                                         logger.warning(f"预设 '{preset_name}' 发现多个前缀提示，将使用 '{json_file.name}' 的内容")
                                    preset_prefix = content
                                    continue

                                # Add regular prompts
                                content = prompt_data.get("content", "")
                                if isinstance(content, str) and content.strip():
                                    prompts.append(prompt_data)
                                elif not isinstance(content, str):
                                    logger.debug(f"提示词 '{prompt_data.get('name', '未命名')}' 在 '{preset_name}' 中的内容不是字符串，已转换为: '{str(content)}'")
                                    prompt_data["content"] = str(content)
                                    prompts.append(prompt_data)
                            else:
                                logger.warning(f"文件 {json_file} 中的数据格式不支持，跳过处理 (期望字典或列表格式)")

                    except (IOError, json.JSONDecodeError) as e:
                        logger.error(f"读取或解析 {json_file} 时出错: {e}", exc_info=True)
                    except Exception as e:
                         logger.error(f"处理 {json_file} 时发生意外错误: {e}", exc_info=True)

                # 按名称排序
                prompts.sort(key=lambda p: p.get('name', ''))
                self.presets[preset_name] = prompts
                self.prefix_prompts[preset_name] = preset_prefix
                loaded_count += 1
                logger.info(f"已加载预设 '{preset_name}'，包含 {len(prompts)} 个提示和{''.join('一个' if preset_prefix else '')}前缀")
            
            logger.info(f"预设加载完成，共加载 {loaded_count} 个预设")
            return loaded_count > 0
        
        except Exception as e:
            logger.error(f"加载预设时发生严重错误: {e}\n{traceback.format_exc()}")
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
        logger.info(f"请求创建新预设: '{name}'")
        try:
            preset_folder = self.output_folder / name
            
            # 检查是否已存在
            if preset_folder.exists():
                logger.warning(f"预设 '{name}' 已经存在于 {preset_folder}")
                return False
            
            # 创建文件夹
            self.ensure_directory_exists(preset_folder)
            
            # 初始化空预设
            self.presets[name] = []
            self.prefix_prompts[name] = ""
            
            logger.info(f"已成功创建新预设文件夹: {preset_folder}")
            return True
            
        except Exception as e:
            logger.error(f"创建预设 '{name}' 时出错: {e}", exc_info=True)
            return False