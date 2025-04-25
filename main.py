import os
from pathlib import Path
from typing import List, Dict, Any, Optional

from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger

from .core import Controller

@register("prompt_tools", "LKarxa", "提示词管理与激活工具", "1.2.0", "https://github.com/LKarxa/prompt_tools")
class PromptToolsPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        
        # 定义关键路径
        self.presets_folder = Path("data/presets")
        # 将输出文件夹修改为presets_folder的子目录
        self.output_folder = self.presets_folder / "extracted"
        
        # 初始化控制器
        self.controller = Controller(self.presets_folder, self.output_folder)
    
    @filter.command_group("prompt")
    def prompt_command_group(self):
        """提示词管理命令组"""
        pass
    
    @prompt_command_group.command("list")
    async def list_prompts(self, event: AstrMessageEvent):
        """列出当前预设中的所有提示词"""
        all_prompts = self.controller.get_current_prompts()
        
        if not all_prompts:
            if not self.controller.get_current_preset_name():
                yield event.plain_result("⚠️ 当前未选择预设，请使用 `/prompt use <索引>` 选择一个预设")
            else:
                yield event.plain_result(f"⚠️ 当前预设 `{self.controller.get_current_preset_name()}` 中没有可用的提示词")
            return
        
        result = f"📝 当前预设: **{self.controller.get_current_preset_name()}**\n\n"
        result += "**可用提示词列表:**\n"
        
        active_prompts = self.controller.get_active_prompts()
        
        for idx, prompt in enumerate(all_prompts):
            name = prompt.get("name", "未命名")
            # 检查是否已激活
            is_active = prompt in active_prompts
            active_marker = "✅ " if is_active else ""
            result += f"{idx}. {active_marker}{name}\n"
        
        result += "\n使用 `/prompt activate <索引>` 来激活提示词，使用 `/prompt view <索引>` 来查看提示词内容"
        
        yield event.plain_result(result)
    
    @prompt_command_group.command("presets")
    async def list_presets(self, event: AstrMessageEvent):
        """列出所有可用的预设"""
        presets = self.controller.get_preset_list()
        
        if not presets:
            yield event.plain_result("⚠️ 没有可用的预设，请使用 `/refresh` 加载预设")
            return
        
        result = "**📁 可用预设列表:**\n"
        
        current_preset = self.controller.get_current_preset_name()
        
        for idx, preset in enumerate(presets):
            # 标记当前选中的预设
            current_marker = "✅ " if preset == current_preset else ""
            result += f"{idx}. {current_marker}{preset}\n"
        
        result += "\n使用 `/prompt use <索引>` 来切换预设"
        
        yield event.plain_result(result)
    
    @prompt_command_group.command("use")
    async def use_preset(self, event: AstrMessageEvent, index: int):
        """切换到指定索引的预设"""
        success, message = self.controller.switch_preset(index)
        
        if success:
            preset_name = self.controller.get_current_preset_name()
            prompts_count = len(self.controller.get_current_prompts())
            yield event.plain_result(f"✅ {message}\n\n"
                                   f"当前预设包含 {prompts_count} 个提示词\n"
                                   f"使用 `/prompt list` 查看所有提示词")
        else:
            yield event.plain_result(f"⚠️ {message}\n请使用 `/prompt presets` 查看可用的预设")
    
    @prompt_command_group.command("activate")
    async def activate_prompt(self, event: AstrMessageEvent, index_or_group: str):
        """
        激活提示词或提示词组合
        
        用法:
        - `/prompt activate <索引>` 激活单个提示词
        - `/prompt activate @<组合名>` 激活组合中的所有提示词
        """
        # 检查是否是组合名称
        if index_or_group.startswith('@'):
            group_name = index_or_group[1:]  # 去除@前缀
            
            if not group_name:
                yield event.plain_result("⚠️ 组合名称不能为空")
                return
            
            success, message, newly_active = self.controller.activate_prompt_group(group_name)
            
            if success:
                if newly_active:
                    prompt_names = [prompt.get('name', '未命名') for prompt in newly_active]
                    active_count = len(self.controller.get_active_prompts())
                    yield event.plain_result(f"✅ 已激活组合 '{group_name}' 中的 {len(newly_active)} 个提示词:\n"
                                          f"{', '.join(prompt_names)}\n\n"
                                          f"当前共激活 {active_count} 个提示词")
                else:
                    yield event.plain_result(f"ℹ️ 组合 '{group_name}' 中的提示词已全部激活")
            else:
                yield event.plain_result(f"⚠️ {message}")
            return
        
        # 否则按索引处理
        try:
            index = int(index_or_group)
            
            success, message, prompt = self.controller.activate_prompt(index)
            
            if success:
                if "已经激活" in message:
                    yield event.plain_result(f"ℹ️ {message}")
                else:
                    active_count = len(self.controller.get_active_prompts())
                    yield event.plain_result(f"✅ {message}\n\n"
                                          f"当前已激活 {active_count} 个提示词")
            else:
                yield event.plain_result(f"⚠️ {message}\n"
                                       f"请使用 `/prompt list` 查看可用的提示词")
        except ValueError:
            yield event.plain_result(f"⚠️ 无效的参数: {index_or_group}\n"
                                  f"请使用索引数字或 @组合名 格式")
    
    @prompt_command_group.command("deactivate")
    async def deactivate_prompt(self, event: AstrMessageEvent, index: int):
        """关闭指定索引的激活提示词"""
        success, message, prompt = self.controller.deactivate_prompt(index)
        
        if success:
            active_count = len(self.controller.get_active_prompts())
            yield event.plain_result(f"✅ {message}\n\n"
                                   f"当前已激活 {active_count} 个提示词")
        else:
            yield event.plain_result(f"⚠️ {message}\n请使用 `/prompts` 查看已激活的提示词")
    
    @prompt_command_group.command("view")
    async def view_prompt(self, event: AstrMessageEvent, index: int):
        """查看指定索引的提示词内容"""
        all_prompts = self.controller.get_current_prompts()
        
        if not all_prompts:
            yield event.plain_result("⚠️ 当前预设中没有可用的提示词")
            return
        
        if 0 <= index < len(all_prompts):
            prompt = all_prompts[index]
            name = prompt.get("name", "未命名")
            content = prompt.get("content", "")
            
            # 检查是否已激活
            is_active = prompt in self.controller.get_active_prompts()
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
        current_preset = self.controller.get_current_preset_name()
        if not current_preset:
            yield event.plain_result("⚠️ 当前未选择预设，请使用 `/prompt use <索引>` 选择一个预设")
            return
        
        prefix_content = self.controller.get_current_prefix()
        
        if not prefix_content:
            yield event.plain_result(f"ℹ️ 当前预设 `{current_preset}` 没有前缀提示")
            return
        
        result = f"**当前预设前缀提示:**\n\n"
        result += f"```\n{prefix_content}\n```"
        
        yield event.plain_result(result)
    
    @prompt_command_group.command("add")
    async def add_prompt(self, event: AstrMessageEvent, name: str, content: str = None):
        """
        添加新的提示词到当前预设
        
        用法: /prompt add <名称> <内容>
        如果内容为空，将从接下来的用户输入中获取
        """
        if not self.controller.get_current_preset_name():
            yield event.plain_result("⚠️ 当前未选择预设，请使用 `/prompt use <索引>` 选择一个预设")
            return
        
        if not name:
            yield event.plain_result("⚠️ 请提供提示词名称")
            return
        
        # 如果内容为空，提示用户输入
        if not content:
            yield event.plain_result(f"请输入提示词 **{name}** 的内容（直接输入，输入完成后会自动保存）:")
            
            # 等待用户下一条消息
            next_message = await event.wait_for_next_message()
            if not next_message:
                yield event.plain_result("❌ 等待输入超时，添加提示词失败")
                return
            
            content = next_message.content
            if not content:
                yield event.plain_result("❌ 提示词内容不能为空")
                return
        
        # 添加提示词
        success, message, prompt = self.controller.add_prompt(name, content)
        
        if success:
            yield event.plain_result(f"✅ {message}\n\n"
                                    f"可以使用 `/prompt list` 查看所有提示词，"
                                    f"使用 `/prompt view <索引>` 查看提示词内容")
        else:
            yield event.plain_result(f"❌ {message}")
    
    @prompt_command_group.command("create_preset")
    async def create_preset(self, event: AstrMessageEvent, name: str):
        """创建新的预设文件夹"""
        success, message = self.controller.create_preset(name)
        
        if success:
            yield event.plain_result(f"✅ {message}\n\n"
                                   f"当前已切换到此预设，使用 `/prompt add` 来添加提示词")
        else:
            yield event.plain_result(f"⚠️ {message}")
            
    @prompt_command_group.command("delete")
    async def delete_prompt(self, event: AstrMessageEvent, index: int):
        """删除指定索引的提示词"""
        success, message, prompt = self.controller.delete_prompt(index)
        
        if success:
            yield event.plain_result(f"✅ {message}")
        else:
            yield event.plain_result(f"⚠️ {message}\n请使用 `/prompt list` 查看可用的提示词")
    
    @filter.command("prompts")
    async def list_active_prompts(self, event: AstrMessageEvent):
        """查看当前激活的所有提示词"""
        active_prompts = self.controller.get_active_prompts()
        
        if not active_prompts:
            yield event.plain_result("ℹ️ 当前没有激活的提示词\n使用 `/prompt list` 查看可用的提示词，然后使用 `/prompt activate <索引>` 激活")
            return
        
        result = f"**当前激活的提示词 ({len(active_prompts)}):**\n\n"
        
        for idx, prompt in enumerate(active_prompts):
            name = prompt.get("name", "未命名")
            result += f"{idx}. {name}\n"
        
        result += "\n使用 `/prompt deactivate <索引>` 来关闭提示词，或使用 `/clear` 清空所有激活的提示词"
        
        yield event.plain_result(result)
    
    @filter.command("clear")
    async def clear_active_prompts(self, event: AstrMessageEvent):
        """清空当前激活的所有提示词"""
        success, message, count = self.controller.clear_active_prompts()
        yield event.plain_result(f"{'ℹ️' if count == 0 else '✅'} {message}")
    
    @filter.command("refresh")
    async def refresh_prompts(self, event: AstrMessageEvent):
        """重新提取和加载所有提示词"""
        yield event.plain_result("🔄 正在重新提取和加载提示词...")
        
        success, message, stats = self.controller.refresh_prompts()
        
        if success:
            preset_count = stats.get("preset_count", 0)
            if preset_count > 0:
                yield event.plain_result(f"✅ {message}\n\n"
                                      f"使用 `/prompt presets` 查看所有预设")
            else:
                yield event.plain_result(f"⚠️ {message}")
        else:
            yield event.plain_result(f"❌ {message}")
    
    @filter.on_llm_request()
    async def on_llm_request(self, event: AstrMessageEvent, req):
        """在发送LLM请求前，自动添加当前激活的提示词和前缀提示"""
        # 检查是否有激活的提示词或前缀提示
        if not self.controller.get_active_prompts() and not self.controller.get_current_prefix():
            # 没有激活的提示词和前缀提示，不需要修改请求
            return
        
        # 处理LLM请求
        modified_system, modified_user = self.controller.process_llm_request(
            req.system_prompt or "", req.prompt
        )
        
        # 更新请求
        req.system_prompt = modified_system
        req.prompt = modified_user
    
    @prompt_command_group.command("group_create")
    async def create_group(self, event: AstrMessageEvent, name: str, indices: str = None):
        """
        创建提示词组合
        
        用法: 
        - `/prompt group_create <组名> <索引1,索引2,...>` 直接创建组合
        - `/prompt group_create <组名>` 从下一条消息获取索引列表
        """
        if not self.controller.get_current_preset_name():
            yield event.plain_result("⚠️ 当前未选择预设，请使用 `/prompt use <索引>` 选择一个预设")
            return
        
        if not name:
            yield event.plain_result("⚠️ 请提供组合名称")
            return
        
        # 如果索引列表为空，等待用户输入
        if not indices:
            yield event.plain_result(f"请输入要添加到组合 **{name}** 的提示词索引列表（以逗号分隔，例如: 0,1,3）:")
            
            # 等待用户下一条消息
            next_message = await event.wait_for_next_message()
            if not next_message:
                yield event.plain_result("❌ 等待输入超时，创建组合失败")
                return
            
            indices = next_message.content
            if not indices:
                yield event.plain_result("❌ 索引列表不能为空")
                return
        
        # 解析索引列表
        try:
            index_list = [int(idx.strip()) for idx in indices.split(',') if idx.strip()]
            if not index_list:
                yield event.plain_result("⚠️ 请提供有效的索引列表")
                return
        except ValueError:
            yield event.plain_result("⚠️ 索引列表格式无效，请使用逗号分隔的数字")
            return
        
        # 创建组合
        success, message = self.controller.create_prompt_group(name, index_list)
        
        if success:
            # 获取组合中的提示词名称
            all_prompts = self.controller.get_current_prompts()
            group_indices = self.controller.get_prompt_group(name)
            
            prompt_names = []
            for idx in group_indices:
                if 0 <= idx < len(all_prompts):
                    prompt_names.append(all_prompts[idx].get('name', f'索引 {idx}'))
            
            yield event.plain_result(f"✅ {message}\n\n"
                                  f"包含提示词: {', '.join(prompt_names)}\n\n"
                                  f"使用 `/prompt activate @{name}` 激活组合中的所有提示词")
        else:
            yield event.plain_result(f"❌ {message}")
    
    @prompt_command_group.command("group_update")
    async def update_group(self, event: AstrMessageEvent, name: str, indices: str = None):
        """
        更新提示词组合
        
        用法: 
        - `/prompt group_update <组名> <索引1,索引2,...>` 直接更新组合
        - `/prompt group_update <组名>` 从下一条消息获取索引列表
        """
        if not self.controller.get_current_preset_name():
            yield event.plain_result("⚠️ 当前未选择预设，请使用 `/prompt use <索引>` 选择一个预设")
            return
        
        # 检查组合是否存在
        groups = self.controller.get_prompt_groups()
        if name not in groups:
            yield event.plain_result(f"⚠️ 组合 '{name}' 不存在，请使用 `/prompt groups` 查看所有组合")
            return
        
        # 如果索引列表为空，等待用户输入
        if not indices:
            yield event.plain_result(f"请输入要添加到组合 **{name}** 的新提示词索引列表（以逗号分隔，例如: 0,1,3）:")
            
            # 等待用户下一条消息
            next_message = await event.wait_for_next_message()
            if not next_message:
                yield event.plain_result("❌ 等待输入超时，更新组合失败")
                return
            
            indices = next_message.content
            if not indices:
                yield event.plain_result("❌ 索引列表不能为空")
                return
        
        # 解析索引列表
        try:
            index_list = [int(idx.strip()) for idx in indices.split(',') if idx.strip()]
            if not index_list:
                yield event.plain_result("⚠️ 请提供有效的索引列表")
                return
        except ValueError:
            yield event.plain_result("⚠️ 索引列表格式无效，请使用逗号分隔的数字")
            return
        
        # 更新组合
        success, message = self.controller.update_prompt_group(name, index_list)
        
        if success:
            # 获取组合中的提示词名称
            all_prompts = self.controller.get_current_prompts()
            group_indices = self.controller.get_prompt_group(name)
            
            prompt_names = []
            for idx in group_indices:
                if 0 <= idx < len(all_prompts):
                    prompt_names.append(all_prompts[idx].get('name', f'索引 {idx}'))
            
            yield event.plain_result(f"✅ {message}\n\n"
                                  f"新的提示词列表: {', '.join(prompt_names)}\n\n"
                                  f"使用 `/prompt activate @{name}` 激活组合中的所有提示词")
        else:
            yield event.plain_result(f"❌ {message}")
    
    @prompt_command_group.command("group_delete")
    async def delete_group(self, event: AstrMessageEvent, name: str):
        """
        删除提示词组合
        
        用法: `/prompt group_delete <组名>`
        """
        if not self.controller.get_current_preset_name():
            yield event.plain_result("⚠️ 当前未选择预设，请使用 `/prompt use <索引>` 选择一个预设")
            return
        
        # 检查组合是否存在
        groups = self.controller.get_prompt_groups()
        if name not in groups:
            yield event.plain_result(f"⚠️ 组合 '{name}' 不存在，请使用 `/prompt groups` 查看所有组合")
            return
        
        # 删除组合
        success, message = self.controller.delete_prompt_group(name)
        
        if success:
            yield event.plain_result(f"✅ {message}")
        else:
            yield event.plain_result(f"❌ {message}")
    
    @prompt_command_group.command("groups")
    async def list_groups(self, event: AstrMessageEvent):
        """
        列出当前预设的所有提示词组合
        
        用法: `/prompt groups`
        """
        current_preset = self.controller.get_current_preset_name()
        if not current_preset:
            yield event.plain_result("⚠️ 当前未选择预设，请使用 `/prompt use <索引>` 选择一个预设")
            return
        
        groups = self.controller.get_prompt_groups()
        
        if not groups:
            yield event.plain_result(f"ℹ️ 当前预设 '{current_preset}' 没有提示词组合\n\n"
                                  f"使用 `/prompt group_create <组名> <索引1,索引2,...>` 创建组合")
            return
        
        result = f"📝 当前预设 **{current_preset}** 的提示词组合:\n\n"
        
        all_prompts = self.controller.get_current_prompts()
        
        for group_name, indices in groups.items():
            prompt_names = []
            for idx in indices:
                if 0 <= idx < len(all_prompts):
                    prompt_names.append(all_prompts[idx].get('name', f'索引 {idx}'))
                else:
                    prompt_names.append(f"无效索引 {idx}")
            
            result += f"**{group_name}** (包含 {len(indices)} 个提示词):\n"
            result += f"  {', '.join(prompt_names)}\n\n"
        
        result += "使用 `/prompt activate @<组名>` 来激活组合中的所有提示词"
        
        yield event.plain_result(result)
    
    @prompt_command_group.command("group_view")
    async def view_group(self, event: AstrMessageEvent, name: str):
        """
        查看提示词组合详情
        
        用法: `/prompt group_view <组名>`
        """
        current_preset = self.controller.get_current_preset_name()
        if not current_preset:
            yield event.plain_result("⚠️ 当前未选择预设，请使用 `/prompt use <索引>` 选择一个预设")
            return
        
        # 检查组合是否存在
        groups = self.controller.get_prompt_groups()
        if name not in groups:
            yield event.plain_result(f"⚠️ 组合 '{name}' 不存在，请使用 `/prompt groups` 查看所有组合")
            return
        
        indices = self.controller.get_prompt_group(name)
        all_prompts = self.controller.get_current_prompts()
        active_prompts = self.controller.get_active_prompts()
        
        result = f"📌 提示词组合: **{name}**\n\n"
        result += f"包含 {len(indices)} 个提示词:\n\n"
        
        for i, idx in enumerate(indices):
            if 0 <= idx < len(all_prompts):
                prompt = all_prompts[idx]
                prompt_name = prompt.get('name', f'索引 {idx}')
                is_active = prompt in active_prompts
                active_marker = "✅ " if is_active else ""
                result += f"{i+1}. {active_marker}[{idx}] {prompt_name}\n"
            else:
                result += f"{i+1}. ⚠️ 无效索引 {idx}\n"
        
        result += f"\n使用 `/prompt activate @{name}` 激活组合中的所有提示词"
        
        yield event.plain_result(result)
    
    async def terminate(self):
        """在插件停用时清理资源"""
        self.controller.terminate()