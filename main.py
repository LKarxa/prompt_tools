import os
import json
from typing import List, Dict, Any, Optional
from pathlib import Path

from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger

from .prompt_extractor import PromptExtractor

@register("prompt_tools", "LKarxa", "提示词管理与激活工具", "1.0.1", "https://github.com/LKarxa/prompt_tools")
class PromptToolsPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        
        # 定义关键路径
        self.presets_folder = Path("data/presets")
        # 将输出文件夹修改为presets_folder的子目录
        self.output_folder = self.presets_folder / "extracted"
        
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
            return True
        except Exception as e:
            logger.error(f"提取提示词时出错: {str(e)}")
            return False
    
    def _load_presets(self) -> None:
        """加载所有已提取的预设文件"""
        try:
            # 清空当前数据
            self.presets = {}
            self.prefix_prompts = {}
            self.active_prompts = []
            
            if not self.output_folder.exists():
                logger.warning(f"输出文件夹不存在: {self.output_folder}")
                # 尝试提取预设
                if not self._extract_prompts():
                    logger.warning("未能提取预设，请检查预设文件")
                return
            
            # 获取所有预设文件夹
            preset_folders = [f for f in self.output_folder.iterdir() if f.is_dir()]
            
            if not preset_folders:
                logger.warning(f"在 {self.output_folder} 中没有找到预设文件夹")
                # 尝试提取预设
                if not self._extract_prompts():
                    logger.warning("未能提取预设，请检查预设文件")
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
                            self.prefix_prompts[preset_name] = prefix_data.get("content", "")
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
                    self.active_prompts.append(prompt)
                    newly_active_prompts.append(prompt)
            else:
                logger.warning(f"无效的提示索引: {idx}")
        
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
        """列出当前预设中的所有提示词"""
        all_prompts = self._get_current_prompts()
        
        if not all_prompts:
            if not self.current_preset_name:
                yield event.plain_result("⚠️ 当前未选择预设，请使用 `/prompt use <索引>` 选择一个预设")
            else:
                yield event.plain_result(f"⚠️ 当前预设 `{self.current_preset_name}` 中没有可用的提示词")
            return
        
        result = f"📝 当前预设: **{self.current_preset_name}**\n\n"
        result += "**可用提示词列表:**\n"
        
        for idx, prompt in enumerate(all_prompts):
            name = prompt.get("name", "未命名")
            # 检查是否已激活
            is_active = prompt in self.active_prompts
            active_marker = "✅ " if is_active else ""
            result += f"{idx}. {active_marker}{name}\n"
        
        result += "\n使用 `/prompt activate <索引>` 来激活提示词，使用 `/prompt view <索引>` 来查看提示词内容"
        
        yield event.plain_result(result)
    
    @prompt_command_group.command("presets")
    async def list_presets(self, event: AstrMessageEvent):
        """列出所有可用的预设"""
        presets = self._get_preset_list()
        
        if not presets:
            yield event.plain_result("⚠️ 没有可用的预设，请使用 `/refresh` 加载预设")
            return
        
        result = "**📁 可用预设列表:**\n"
        
        for idx, preset in enumerate(presets):
            # 标记当前选中的预设
            current_marker = "✅ " if preset == self.current_preset_name else ""
            result += f"{idx}. {current_marker}{preset}\n"
        
        result += "\n使用 `/prompt use <索引>` 来切换预设"
        
        yield event.plain_result(result)
    
    @prompt_command_group.command("use")
    async def use_preset(self, event: AstrMessageEvent, index: int):
        """切换到指定索引的预设"""
        presets = self._get_preset_list()
        
        if not presets:
            yield event.plain_result("⚠️ 没有可用的预设，请使用 `/refresh` 加载预设")
            return
        
        if 0 <= index < len(presets):
            # 清空当前激活的提示
            self.active_prompts = []
            
            # 设置新的预设
            self.current_preset_name = presets[index]
            
            yield event.plain_result(f"✅ 已切换至预设: **{self.current_preset_name}**\n\n"
                                   f"当前预设包含 {len(self._get_current_prompts())} 个提示词\n"
                                   f"使用 `/prompt list` 查看所有提示词")
        else:
            yield event.plain_result(f"⚠️ 无效的预设索引: {index}\n请使用 `/prompt presets` 查看可用的预设")
    
    @prompt_command_group.command("activate")
    async def activate_prompt(self, event: AstrMessageEvent, index: int):
        """激活指定索引的提示词"""
        all_prompts = self._get_current_prompts()
        
        if not all_prompts:
            yield event.plain_result("⚠️ 当前预设中没有可用的提示词")
            return
        
        if 0 <= index < len(all_prompts):
            prompt = all_prompts[index]
            
            # 检查提示是否已经激活
            if prompt in self.active_prompts:
                yield event.plain_result(f"ℹ️ 提示词 \"{prompt['name']}\" 已经激活")
                return
            
            newly_active = self._activate_prompts([index])
            if newly_active:
                yield event.plain_result(f"✅ 已激活提示词: **{prompt['name']}**\n\n"
                                       f"当前已激活 {len(self.active_prompts)} 个提示词")
            else:
                yield event.plain_result(f"⚠️ 激活提示词失败")
        else:
            yield event.plain_result(f"⚠️ 无效的提示词索引: {index}\n请使用 `/prompt list` 查看可用的提示词")
    
    @prompt_command_group.command("deactivate")
    async def deactivate_prompt(self, event: AstrMessageEvent, index: int):
        """关闭指定索引的激活提示词"""
        if not self.active_prompts:
            yield event.plain_result("ℹ️ 当前没有已激活的提示词")
            return
        
        if 0 <= index < len(self.active_prompts):
            removed_prompt = self._deactivate_prompt(index)
            if removed_prompt:
                yield event.plain_result(f"✅ 已关闭提示词: **{removed_prompt['name']}**\n\n"
                                       f"当前已激活 {len(self.active_prompts)} 个提示词")
            else:
                yield event.plain_result(f"⚠️ 关闭提示词失败")
        else:
            yield event.plain_result(f"⚠️ 无效的激活提示词索引: {index}\n请使用 `/prompts` 查看已激活的提示词")
    
    @prompt_command_group.command("view")
    async def view_prompt(self, event: AstrMessageEvent, index: int):
        """查看指定索引的提示词内容"""
        all_prompts = self._get_current_prompts()
        
        if not all_prompts:
            yield event.plain_result("⚠️ 当前预设中没有可用的提示词")
            return
        
        if 0 <= index < len(all_prompts):
            prompt = all_prompts[index]
            name = prompt.get("name", "未命名")
            content = prompt.get("content", "")
            
            # 检查是否已激活
            is_active = prompt in self.active_prompts
            active_status = "已激活 ✅" if is_active else "未激活 ❌"
            
            result = f"**提示词详情 ({active_status}):**\n\n"
            result += f"📌 **名称:** {name}\n\n"
            result += f"📄 **内容:**\n```\n{content}\n```"
            
            yield event.plain_result(result)
        else:
            yield event.plain_result(f"⚠️ 无效的提示词索引: {index}\n请使用 `/prompt list` 查看可用的提示词")
    
    @prompt_command_group.command("prefix")
    async def view_prefix(self, event: AstrMessageEvent):
        """查看当前预设的前缀提示内容"""
        if not self.current_preset_name:
            yield event.plain_result("⚠️ 当前未选择预设，请使用 `/prompt use <索引>` 选择一个预设")
            return
        
        prefix_content = self._get_current_prefix()
        
        if not prefix_content:
            yield event.plain_result(f"ℹ️ 当前预设 `{self.current_preset_name}` 没有前缀提示")
            return
        
        result = f"**当前预设前缀提示:**\n\n"
        result += f"```\n{prefix_content}\n```"
        
        yield event.plain_result(result)
    
    @filter.command("prompts")
    async def list_active_prompts(self, event: AstrMessageEvent):
        """查看当前激活的所有提示词"""
        if not self.active_prompts:
            yield event.plain_result("ℹ️ 当前没有激活的提示词\n使用 `/prompt list` 查看可用的提示词，然后使用 `/prompt activate <索引>` 激活")
            return
        
        result = f"**当前激活的提示词 ({len(self.active_prompts)}):**\n\n"
        
        for idx, prompt in enumerate(self.active_prompts):
            name = prompt.get("name", "未命名")
            result += f"{idx}. {name}\n"
        
        result += "\n使用 `/prompt deactivate <索引>` 来关闭提示词，或使用 `/clear` 清空所有激活的提示词"
        
        yield event.plain_result(result)
    
    @filter.command("clear")
    async def clear_active_prompts(self, event: AstrMessageEvent):
        """清空当前激活的所有提示词"""
        count = len(self.active_prompts)
        
        if count == 0:
            yield event.plain_result("ℹ️ 当前没有激活的提示词")
            return
        
        self.active_prompts = []
        yield event.plain_result(f"✅ 已清空 {count} 个激活的提示词")
    
    @filter.command("refresh")
    async def refresh_prompts(self, event: AstrMessageEvent):
        """重新提取和加载所有提示词"""
        yield event.plain_result("🔄 正在重新提取和加载提示词...")
        
        # 提取提示词
        if self._extract_prompts():
            # 重新加载提示词
            self._load_presets()
            
            # 清空当前激活的提示词
            self.active_prompts = []
            
            # 统计加载的预设数量和提示词总数
            preset_count = len(self.presets)
            prompt_count = sum(len(prompts) for prompts in self.presets.values())
            
            if preset_count > 0:
                yield event.plain_result(f"✅ 成功重新加载 {preset_count} 个预设，共 {prompt_count} 个提示词\n\n"
                                      f"使用 `/prompt presets` 查看所有预设")
            else:
                yield event.plain_result("⚠️ 没有找到可用的预设，请检查预设文件")
        else:
            yield event.plain_result("❌ 提取提示词失败，请检查日志获取详细错误信息")
    
    @filter.on_llm_request()
    async def on_llm_request(self, event: AstrMessageEvent, req):
        """在发送LLM请求前，自动添加当前激活的提示词和前缀提示"""
        if not self.active_prompts and not self._get_current_prefix():
            # 没有激活的提示词和前缀提示，不需要修改请求
            return
        
        # 添加前缀提示到system_prompt
        prefix = self._get_current_prefix()
        if prefix:
            if req.system_prompt:
                # 将前缀提示添加到现有系统提示之前
                req.system_prompt = f"{prefix}\n\n{req.system_prompt}"
            else:
                req.system_prompt = prefix
        
        # 添加激活的提示词到用户提示词前
        if self.active_prompts:
            # 构建激活的提示词内容
            active_content = ""
            for prompt in self.active_prompts:
                active_content += f"\n\n{prompt.get('content', '')}"
            
            # 将激活的提示词添加到用户提示词前
            req.prompt = f"{active_content}\n\n{req.prompt}"
    
    async def terminate(self):
        """在插件停用时清理资源"""
        # 清空激活的提示词
        self.active_prompts = []

# 测试代码（仅在直接运行时执行）
if __name__ == "__main__":
    print("这是提示词工具插件的主文件")