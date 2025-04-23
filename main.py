import os
import json
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.api.event import filter

from .prompt_extractor import PromptExtractor

@register("prompt_tools", "LKarxa", "兼容酒馆预设以及管理工具", "1.0.0", "https://github.com/LKarxa/prompt_tools")
class PromptToolsPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        
        # 定义关键路径
        self.presets_folder = Path("data/presets")
        self.output_folder = Path("prompts")
        
        # 提示数据存储
        self.presets = {}  # 所有预设文件列表
        self.current_preset_name = ""  # 当前选中的预设名称
        self.active_prompts = []  # 当前激活的提示列表，按激活顺序排列
        self.prefix_prompts = {}  # 每个预设对应的前缀提示 {preset_name: prefix_content}
        
        # 初始化
        self._initialize_plugin()
    
    def _initialize_plugin(self):
        """初始化插件，提取提示词并加载第一个JSON文件"""
        logger.info("正在初始化提示词工具插件...")
        
        # 确保必要的文件夹存在
        self._ensure_directory_exists(self.presets_folder)
        self._ensure_directory_exists(self.output_folder)
        
        # 提取提示词
        self._extract_prompts()
        
        # 加载提示词数据
        self._load_presets()
        
        # 设置默认预设
        if self.presets:
            self.current_preset_name = list(self.presets.keys())[0]
            logger.info(f"已设置默认预设: {self.current_preset_name}")
        else:
            logger.warning("没有找到可用的预设文件")
    
    def _ensure_directory_exists(self, directory: Path) -> None:
        """确保目录存在，如果不存在则创建"""
        if not directory.exists():
            directory.mkdir(parents=True)
            logger.info(f"创建目录: {directory}")
    
    def _extract_prompts(self) -> None:
        """调用prompt_extractor.py提取提示词"""
        try:
            # 检查presets文件夹中是否有JSON文件
            json_files = list(self.presets_folder.glob("*.json"))
            if not json_files:
                logger.warning(f"在 {self.presets_folder} 中没有找到JSON文件，请先添加预设文件")
                return
                
            extractor = PromptExtractor(
                presets_folder=str(self.presets_folder), 
                output_folder=str(self.output_folder)
            )
            extracted_prompts = extractor.extract_all_prompts()
            logger.info(f"成功提取提示词，共 {sum(len(prompts) for prompts in extracted_prompts.values())} 个")
        except Exception as e:
            logger.error(f"提取提示词时出错: {str(e)}")
    
    def _load_presets(self) -> None:
        """加载所有已提取的预设文件"""
        try:
            if not self.output_folder.exists():
                logger.warning(f"输出文件夹不存在: {self.output_folder}")
                return
            
            # 获取所有预设文件夹
            preset_folders = [f for f in self.output_folder.iterdir() if f.is_dir()]
            
            if not preset_folders:
                logger.warning(f"在 {self.output_folder} 中没有找到预设文件夹")
                return
            
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
                            if not prompt_data.get("is_prefix", False) and prompt_data.get("content", "").strip():
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
                            if prefix_data and prefix_data.get("content", "").strip():
                                self.prefix_prompts[preset_name] = prefix_data.get("content", "")
                                logger.info(f"已加载预设 {preset_name} 的前缀提示")
                    except Exception as e:
                        logger.error(f"读取前缀提示文件 {prefix_file} 时出错: {str(e)}")
                
                logger.info(f"已加载预设 {preset_name}，包含 {len(prompts)} 个提示")
        
        except Exception as e:
            logger.error(f"加载预设时出错: {str(e)}")
    
    def _get_current_prompts(self) -> List[Dict[str, str]]:
        """获取当前选中预设的所有提示"""
        if not self.current_preset_name or self.current_preset_name not in self.presets:
            return []
        return self.presets[self.current_preset_name]
    
    def _get_current_prefix(self) -> str:
        """获取当前预设的前缀提示内容"""
        if not self.current_preset_name or self.current_preset_name not in self.prefix_prompts:
            return ""
        return self.prefix_prompts[self.current_preset_name]
    
    def _get_preset_list(self) -> List[str]:
        """获取所有可用预设的列表"""
        return list(self.presets.keys())
    
    def _activate_prompts(self, indices: List[int]) -> List[Dict[str, str]]:
        """激活指定索引的提示，累加到已激活的提示上而不是替换它们"""
        all_prompts = self._get_current_prompts()
        newly_active_prompts = []
        
        for idx in indices:
            if 0 <= idx < len(all_prompts):
                prompt = all_prompts[idx]
                # 检查提示是否已经激活，避免重复添加
                if prompt not in self.active_prompts:
                    newly_active_prompts.append(prompt)
                    self.active_prompts.append(prompt)
            else:
                logger.warning(f"索引 {idx} 超出范围")
        
        return newly_active_prompts
    
    def _deactivate_prompt(self, index: int) -> Optional[Dict[str, str]]:
        """关闭指定索引的激活提示"""
        if index < 0 or index >= len(self.active_prompts):
            return None
        
        # 移除并返回指定索引的激活提示
        return self.active_prompts.pop(index)
    
    @filter.command_group("prompt")
    def prompt_command_group(self):
        """提示词管理命令组"""
        pass
    
    @prompt_command_group.command("list")
    async def list_prompts(self, event: AstrMessageEvent):
        """列出当前预设中的所有提示"""
        prompts = self._get_current_prompts()
        
        if not prompts:
            yield event.plain_result(f"当前没有可用的提示。请先加载预设。")
            return
            
        result = f"当前预设: {self.current_preset_name}\n\n提示列表:\n"
        for i, prompt in enumerate(prompts):
            name = prompt.get("name", "未命名")
            # 检查是否激活
            is_active = prompt in self.active_prompts
            active_mark = "✅" if is_active else "❌"
            result += f"{i}. {active_mark} {name}\n"
            
        # 显示前缀提示状态
        prefix_content = self._get_current_prefix()
        if prefix_content:
            result += "\n[系统] 当前预设包含前缀提示，将自动添加到系统提示中"
            
        yield event.plain_result(result)
    
    @prompt_command_group.command("presets")
    async def list_presets(self, event: AstrMessageEvent):
        """列出所有可用的预设"""
        presets = self._get_preset_list()
        
        if not presets:
            yield event.plain_result("没有可用的预设。请先提取提示词。")
            return
            
        result = "可用预设列表:\n"
        for i, preset in enumerate(presets):
            # 标记当前选中的预设
            current_mark = "✅" if preset == self.current_preset_name else "❌"
            # 标记是否包含前缀提示
            has_prefix = "🔒" if preset in self.prefix_prompts else ""
            result += f"{i}. {current_mark} {preset} {has_prefix}\n"
            
        if any(preset in self.prefix_prompts for preset in presets):
            result += "\n🔒 表示该预设包含自动前缀提示"
            
        yield event.plain_result(result)
    
    @prompt_command_group.command("use")
    async def use_preset(self, event: AstrMessageEvent, index: int):
        """使用指定索引的预设"""
        presets = self._get_preset_list()
        
        if not presets:
            yield event.plain_result("没有可用的预设。请先提取提示词。")
            return
            
        if 0 <= index < len(presets):
            self.current_preset_name = presets[index]
            # 切换预设时清空已激活的提示
            self.active_prompts = []
            
            # 检查是否有前缀提示
            has_prefix = self.current_preset_name in self.prefix_prompts
            prefix_msg = "，包含自动前缀提示" if has_prefix else ""
            
            yield event.plain_result(f"已切换到预设: {self.current_preset_name}{prefix_msg}")
        else:
            yield event.plain_result(f"索引 {index} 超出范围。可用的预设索引范围: 0-{len(presets)-1}")
    
    @prompt_command_group.command("view")
    async def view_prompt(self, event: AstrMessageEvent, index: int):
        """查看指定索引的提示内容"""
        prompts = self._get_current_prompts()
        
        if not prompts:
            yield event.plain_result("当前没有可用的提示。请先加载预设。")
            return
            
        if 0 <= index < len(prompts):
            prompt = prompts[index]
            name = prompt.get("name", "未命名")
            content = prompt.get("content", "")
            
            result = f"提示名称: {name}\n\n内容:\n{content}"
            yield event.plain_result(result)
        else:
            yield event.plain_result(f"索引 {index} 超出范围。可用的提示索引范围: 0-{len(prompts)-1}")
    
    @prompt_command_group.command("activate")
    async def activate_prompts(self, event: AstrMessageEvent, index: Any = None):
        """激活指定索引的提示"""
        # 检查是否提供了参数
        if index is None:
            yield event.plain_result("请指定要激活的提示索引。例如: /prompt activate 0 1 2")
            return
        
        # 处理单个整数或列表的情况
        if isinstance(index, int):
            index_list = [index]
        elif isinstance(index, list):
            index_list = index
        else:
            # 尝试将参数转换为整数
            try:
                index_list = [int(index)]
            except (ValueError, TypeError):
                yield event.plain_result("提供的索引无效，请使用整数索引。例如: /prompt activate 0")
                return
        
        # 激活提示
        newly_active_prompts = self._activate_prompts(index_list)
        
        if not newly_active_prompts:
            yield event.plain_result("未能激活任何提示。请检查索引是否有效。")
            return
            
        result = f"已激活 {len(newly_active_prompts)} 个提示:\n"
        for i, prompt in enumerate(newly_active_prompts):
            name = prompt.get("name", "未命名")
            result += f"{i}. {name}\n"
        
        # 显示当前所有激活的提示总数
        result += f"\n当前已激活 {len(self.active_prompts)} 个提示（共计）"
        
        # 提示前缀状态
        prefix_content = self._get_current_prefix()
        if prefix_content:
            result += "\n[系统] 当前预设的前缀提示将自动应用"
            
        yield event.plain_result(result)
    
    @prompt_command_group.command("deactivate")
    async def deactivate_prompt(self, event: AstrMessageEvent, index: int = None):
        """关闭指定索引的激活提示"""
        if index is None:
            yield event.plain_result("请指定要关闭的激活提示索引。例如: /prompt deactivate 0")
            return
        
        # 确保index是整数
        try:
            index = int(index)
        except (ValueError, TypeError):
            yield event.plain_result("提供的索引无效，请使用整数索引。例如: /prompt deactivate 0")
            return
        
        if not self.active_prompts:
            yield event.plain_result("当前没有激活的提示。")
            return
        
        if index < 0 or index >= len(self.active_prompts):
            yield event.plain_result(f"索引 {index} 超出范围。有效范围: 0-{len(self.active_prompts)-1}")
            return
        
        # 关闭指定索引的提示
        removed_prompt = self._deactivate_prompt(index)
        if removed_prompt:
            name = removed_prompt.get("name", "未命名")
            yield event.plain_result(f"已关闭激活提示: {name}")
            
            # 显示当前剩余的激活提示
            if self.active_prompts:
                result = f"当前仍有 {len(self.active_prompts)} 个激活的提示:\n"
                for i, prompt in enumerate(self.active_prompts):
                    name = prompt.get("name", "未命名")
                    result += f"{i}. {name}\n"
                yield event.plain_result(result)
        else:
            yield event.plain_result(f"关闭提示失败。")
    
    @filter.command("prompts")
    async def show_active_prompts(self, event: AstrMessageEvent):
        """查看当前激活的所有提示"""
        if not self.active_prompts:
            prefix_content = self._get_current_prefix()
            if prefix_content:
                yield event.plain_result("当前没有手动激活的提示，但有自动前缀提示已启用。使用 /prompt activate 命令激活其他提示。")
            else:
                yield event.plain_result("当前没有激活的提示。使用 /prompt activate 命令激活提示。")
            return
            
        result = f"当前激活的提示 ({len(self.active_prompts)}):\n"
        for i, prompt in enumerate(self.active_prompts):
            name = prompt.get("name", "未命名")
            content_preview = prompt.get("content", "")
            if len(content_preview) > 50:
                content_preview = content_preview[:50] + "..."
            result += f"{i}. {name}: {content_preview}\n"
            
        # 提示前缀状态
        prefix_content = self._get_current_prefix()
        if prefix_content:
            preview = prefix_content[:50] + "..." if len(prefix_content) > 50 else prefix_content
            result += f"\n[系统] 自动前缀提示: {preview}"
            
        # 添加使用说明
        result += "\n\n提示按激活顺序排列。使用 /prompt deactivate <索引> 关闭单个提示。"
            
        yield event.plain_result(result)
    
    @filter.command("clear")
    async def clear_active_prompts(self, event: AstrMessageEvent):
        """清空当前激活的所有提示"""
        count = len(self.active_prompts)
        self.active_prompts = []
        
        prefix_content = self._get_current_prefix()
        if prefix_content:
            yield event.plain_result(f"已清空 {count} 个手动激活的提示。前缀提示仍将自动应用。")
        else:
            yield event.plain_result(f"已清空 {count} 个激活的提示。")
    
    @filter.on_llm_request()
    async def add_prompts_to_system(self, event: AstrMessageEvent, req):
        """在LLM请求前添加激活的提示和前缀提示到系统提示中"""
        # 首先处理前缀提示，它应该放在最前面
        prefix_content = self._get_current_prefix()
        
        # 合并所有激活提示的内容，按激活顺序
        user_prompts = ""
        for prompt in self.active_prompts:
            content = prompt.get("content", "").strip()
            if content:
                user_prompts += content + "\n\n"
        
        # 组合前缀提示和用户激活的提示
        combined_prompt = ""
        
        if prefix_content:
            combined_prompt += prefix_content + "\n\n"
            logger.info("已添加前缀提示到系统提示中")
            
        if user_prompts:
            combined_prompt += user_prompts
            logger.info(f"已添加 {len(self.active_prompts)} 个激活的提示到系统提示中")
        
        # 添加到系统提示
        if combined_prompt:
            if req.system_prompt:
                req.system_prompt = combined_prompt.strip() + "\n\n" + req.system_prompt
            else:
                req.system_prompt = combined_prompt.strip()
    
    @filter.command("refresh")
    async def refresh_prompts(self, event: AstrMessageEvent):
        """重新提取和加载提示词"""
        try:
            # 重新提取
            self._extract_prompts()
            # 重新加载
            old_preset_name = self.current_preset_name
            self.presets = {}
            self.prefix_prompts = {}
            self._load_presets()
            
            # 尝试恢复之前的预设选择
            if old_preset_name in self.presets:
                self.current_preset_name = old_preset_name
            elif self.presets:
                self.current_preset_name = list(self.presets.keys())[0]
            
            # 清空激活的提示
            self.active_prompts = []
            
            # 统计前缀提示
            prefix_count = len(self.prefix_prompts)
            prefix_msg = f"，包含 {prefix_count} 个预设的前缀提示" if prefix_count > 0 else ""
            
            yield event.plain_result(f"已刷新提示词库。当前可用预设: {len(self.presets)}{prefix_msg}。")
        except Exception as e:
            logger.error(f"刷新提示词时出错: {str(e)}")
            yield event.plain_result(f"刷新提示词时出错: {str(e)}")
    
    @prompt_command_group.command("prefix")
    async def show_prefix(self, event: AstrMessageEvent):
        """查看当前预设的前缀提示内容"""
        prefix_content = self._get_current_prefix()
        if not prefix_content:
            yield event.plain_result(f"当前预设 {self.current_preset_name} 没有前缀提示。")
            return
            
        result = f"当前预设 {self.current_preset_name} 的前缀提示内容:\n\n{prefix_content}"
        yield event.plain_result(result)
    
    async def terminate(self):
        """插件被卸载/停用时调用"""
        logger.info("提示词工具插件已终止")

# 测试代码（仅在直接运行时执行）
if __name__ == "__main__":
    print("这是提示词工具插件的主文件")
