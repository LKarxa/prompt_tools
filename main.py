from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register, StarTools
from astrbot.api import logger
from pathlib import Path
from typing import Optional, List, Dict, Any

from .core.controller import Controller

@register("prompt_tools", "LKarxa", "提示词管理与激活工具", "1.3.0", "https://github.com/LKarxa/prompt_tools")
class PromptToolsPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        
        # 使用 StarTools.get_data_dir 获取标准数据目录
        plugin_data_dir = StarTools.get_data_dir("prompt_tools")
        
        # 定义关键路径
        self.presets_folder = plugin_data_dir / "presets"
        # 将输出文件夹修改为presets_folder的子目录
        self.output_folder = self.presets_folder / "extracted"
        
        # 确保目录存在
        self.presets_folder.mkdir(parents=True, exist_ok=True)
        self.output_folder.mkdir(parents=True, exist_ok=True)
        
        # 初始化控制器
        self.controller = Controller(self.presets_folder, self.output_folder)

    # --- 主命令组 ---
    @filter.command_group("prompt")
    def prompt_command_group(self):
        """提示词管理命令组"""
        pass

    # --- 预设管理 ---
    @prompt_command_group.command("presets")
    async def list_presets(self, event: AstrMessageEvent):
        """列出所有可用的预设"""
        presets = self.controller.get_preset_list()
        
        if not presets:
            yield event.plain_result("⚠️ 没有可用的预设，请使用 `/prompt refresh` 加载预设或 `/prompt create_preset <名称>` 创建新预设")
            return
        
        result = "**📁 可用预设列表:**\n"
        current_preset = self.controller.get_current_preset_name()
        
        for idx, preset in enumerate(presets):
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

    @prompt_command_group.command("create_preset")
    async def create_preset(self, event: AstrMessageEvent, name: str):
        """创建一个新的空白预设"""
        success, message = self.controller.create_preset(name)
        if success:
            yield event.plain_result(f"✅ {message}\n已自动切换到新创建的预设 '{name}'")
        else:
            yield event.plain_result(f"⚠️ {message}")

    @prompt_command_group.command("refresh")
    async def refresh_prompts_cmd(self, event: AstrMessageEvent):
        """重新提取和加载所有提示词"""
        success, message, stats = self.controller.refresh_prompts()
        if success:
            yield event.plain_result(f"✅ {message}")
        else:
            yield event.plain_result(f"⚠️ {message}")

    # --- 提示词列表与激活 ---
    @prompt_command_group.command("list")
    async def list_prompts(self, event: AstrMessageEvent):
        """列出当前预设中的所有提示词（并标记已激活）"""
        all_prompts = self.controller.get_current_prompts()
        
        if not self.controller.get_current_preset_name():
            yield event.plain_result("⚠️ 当前未选择预设，请使用 `/prompt use <索引>` 选择一个预设")
            return
            
        if not all_prompts:
            yield event.plain_result(f"⚠️ 当前预设 `{self.controller.get_current_preset_name()}` 中没有可用的提示词，可使用 `/prompt add <名称>` 添加")
            return
        
        result = f"📝 当前预设: **{self.controller.get_current_preset_name()}**\n\n"
        result += "**可用提示词列表:**\n"
        
        active_prompts = self.controller.get_active_prompts()
        
        for idx, prompt in enumerate(all_prompts):
            name = prompt.get("name", "未命名")
            is_active = prompt in active_prompts
            active_marker = "✅ " if is_active else ""
            result += f"{idx}. {active_marker}{name}\n"
        
        active_count = len(active_prompts)
        if active_count > 0:
            result += f"\n当前共激活 {active_count} 个提示词。"
        else:
            result += "\n当前没有激活的提示词。"
            
        result += "\n\n使用 `/prompt activate <索引|@组名>` 激活，`/prompt deactivate <索引|all>` 关闭，`/prompt view prompt <索引>` 查看内容"
        
        yield event.plain_result(result)

    @prompt_command_group.command("activate")
    async def activate_prompt(self, event: AstrMessageEvent, index_or_group: str):
        """
        激活提示词或提示词组合
        
        用法:
        - `/prompt activate <索引>` 激活单个提示词
        - `/prompt activate <索引1,索引2,...>` 激活多个提示词
        - `/prompt activate @<组合名>` 激活组合中的所有提示词
        """
        if index_or_group.startswith('@'):
            group_name = index_or_group[1:]
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
        else:
            # 检查是否包含逗号，如果有则表示要激活多个提示词
            if ',' in index_or_group:
                try:
                    # 分割并转换索引
                    indices = [int(i.strip()) for i in index_or_group.split(',')]
                    
                    success, message, newly_active = self.controller.activate_multiple_prompts(indices)
                    
                    if success:
                        if newly_active:
                            prompt_names = [prompt.get('name', '未命名') for prompt in newly_active]
                            active_count = len(self.controller.get_active_prompts())
                            yield event.plain_result(f"✅ 已批量激活 {len(newly_active)} 个提示词:\n"
                                                  f"{', '.join(prompt_names)}\n\n"
                                                  f"当前共激活 {active_count} 个提示词")
                        else:
                            yield event.plain_result(f"ℹ️ {message}")
                    else:
                        yield event.plain_result(f"⚠️ {message}")
                except ValueError:
                    yield event.plain_result(f"⚠️ 索引格式错误: {index_or_group}\n"
                                          f"请使用逗号分隔的数字，例如: 0,1,5")
            else:
                # 原有的单索引激活逻辑
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
                                          f"请使用索引数字、逗号分隔的多个索引或 @组合名 格式")

    @prompt_command_group.command("deactivate")
    async def deactivate_prompt(self, event: AstrMessageEvent, target: str):
        """
        关闭激活的提示词或组合
        
        用法:
        - `/prompt deactivate <激活索引>` 关闭指定索引的激活提示词
        - `/prompt deactivate <索引1,索引2,...>` 关闭多个激活提示词
        - `/prompt deactivate @<组名>` 关闭指定组合中的所有提示词
        - `/prompt deactivate all` 关闭所有激活的提示词
        """
        if not self.controller.get_current_preset_name():
            yield event.plain_result("⚠️ 当前未选择预设")
            return

        if target.lower() == "all":
            # 关闭所有
            success, message, count = self.controller.clear_active_prompts()
            if success:
                yield event.plain_result(f"✅ {message}")
            else:
                # 应该通常会成功，但仍处理可能的内部错误消息
                yield event.plain_result(f"⚠️ {message}")

        elif target.startswith('@'):
            # 关闭组合
            group_name = target[1:]
            if not group_name:
                 yield event.plain_result("⚠️ 请提供有效的组合名称 (例如: @myGroup)")
                 return
                 
            success, message, deactivated_prompts = self.controller.deactivate_prompt_group(group_name)
            active_count = len(self.controller.get_active_prompts()) # 获取停用后的激活数量
            if success:
                if deactivated_prompts:
                    names = [f'"{p.get("name", "未命名")}"' for p in deactivated_prompts]
                    yield event.plain_result(f"✅ {message}: {', '.join(names)}\n\n当前剩余 {active_count} 个激活提示词")
                else:
                    # 消息可能是 "组合为空" 或 "提示词未激活"
                    yield event.plain_result(f"✅ {message}\n\n当前剩余 {active_count} 个激活提示词")
            else:
                logger.warning(f"用户 {event.get_sender_id()} 关闭组合 '{group_name}' 失败: {message}")
                yield event.plain_result(f"⚠️ {message}\n\n当前剩余 {active_count} 个激活提示词")
        else:
            # 检查是否包含逗号，如果有则表示要关闭多个提示词
            if ',' in target:
                try:
                    # 分割并转换索引
                    indices = [int(i.strip()) for i in target.split(',')]
                    
                    success, message, deactivated_prompts = self.controller.deactivate_multiple_prompts(indices)
                    active_count_after = len(self.controller.get_active_prompts()) # 获取停用后的激活数量
                    
                    if success:
                        if deactivated_prompts:
                            prompt_names = [prompt.get('name', '未命名') for prompt in deactivated_prompts]
                            yield event.plain_result(f"✅ 已批量关闭 {len(deactivated_prompts)} 个提示词:\n"
                                                  f"{', '.join(prompt_names)}\n\n"
                                                  f"当前剩余 {active_count_after} 个激活提示词")
                        else:
                            yield event.plain_result(f"ℹ️ {message}\n\n当前剩余 {active_count_after} 个激活提示词")
                    else:
                        yield event.plain_result(f"⚠️ {message}\n\n当前剩余 {active_count_after} 个激活提示词")
                except ValueError:
                    yield event.plain_result(f"⚠️ 索引格式错误: {target}\n"
                                          f"请使用逗号分隔的数字，例如: 0,1,5")
            else:
                # 原有的单索引关闭逻辑
                try:
                    # 重要: 这里的索引指的是激活提示词列表中的索引，
                    # 而不是完整预设列表中的索引。
                    active_index = int(target)
                    
                    # 获取停用前的激活提示词列表以检查索引有效性
                    active_prompts_before = self.controller.get_active_prompts()
                    if not active_prompts_before:
                         yield event.plain_result("⚠️ 当前没有已激活的提示词")
                         return
                         
                    if not (0 <= active_index < len(active_prompts_before)):
                         yield event.plain_result(f"⚠️ 无效的激活索引: {active_index}。当前激活列表有 {len(active_prompts_before)} 个提示词。请使用 0 到 {len(active_prompts_before)-1} 之间的索引。")
                         return

                    # 使用激活列表索引调用控制器
                    success, message, prompt = self.controller.deactivate_prompt(active_index)
                    active_count_after = len(self.controller.get_active_prompts()) # 获取停用后的激活数量
                    
                    if success:
                        prompt_name = prompt.get('name', '未命名') if prompt else '未知提示词'
                        logger.info(f"用户 {event.get_sender_id()} 关闭激活索引 {active_index} ('{prompt_name}') 成功")
                        yield event.plain_result(f"✅ {message}\n\n当前剩余 {active_count_after} 个激活提示词")
                    else:
                        logger.warning(f"用户 {event.get_sender_id()} 关闭激活索引 {active_index} 失败: {message}")
                        yield event.plain_result(f"⚠️ {message}\n\n当前剩余 {active_count_after} 个激活提示词")
                except ValueError:
                    logger.warning(f"用户 {event.get_sender_id()} 尝试关闭无效目标: '{target}'")
                    yield event.plain_result(f"⚠️ 无效输入: 请输入激活提示词的索引 (数字)、以逗号分隔的多个索引、组合名称 (以 @ 开头) 或 'all'")
                except Exception as e:
                     logger.error(f"处理关闭目标 '{target}' 时发生意外错误: {e}", exc_info=True)
                     yield event.plain_result(f"❌ 处理关闭命令时发生内部错误，请查看日志")

    # --- 查看指令子组 ---
    @prompt_command_group.group("view")
    def view_command_group(self):
        """查看提示词、前缀或组合详情"""
        pass

    @view_command_group.command("prompt")
    async def view_prompt(self, event: AstrMessageEvent, index: int):
        """查看指定索引的提示词内容"""
        all_prompts = self.controller.get_current_prompts()
        
        if not all_prompts:
            yield event.plain_result("⚠️ 当前预设中没有可用的提示词")
            return
        
        if 0 <= index < len(all_prompts):
            prompt = all_prompts[index]
            name = prompt.get("name", "未命名")
            content = prompt.get("content", "无内容")
            is_active = prompt in self.controller.get_active_prompts()
            active_marker = "✅ (已激活)" if is_active else "❌ (未激活)"
            
            result = f"**🔍 提示词详情 (索引: {index})**\n\n"
            result += f"**名称:** {name} {active_marker}\n"
            result += f"**内容:**\n```\n{content}\n```"
            yield event.plain_result(result)
        else:
            yield event.plain_result(f"⚠️ 无效的提示词索引: {index}\n请使用 `/prompt list` 查看可用的索引")

    @view_command_group.command("prefix")
    async def view_prefix(self, event: AstrMessageEvent):
        """查看当前预设的前缀提示内容"""
        prefix_content = self.controller.get_current_prefix()
        preset_name = self.controller.get_current_preset_name()
        
        if not preset_name:
             yield event.plain_result("⚠️ 当前未选择预设")
             return
             
        if prefix_content:
            result = f"**🔒 当前预设 '{preset_name}' 的前缀提示:**\n\n"
            result += f"```\n{prefix_content}\n```"
            yield event.plain_result(result)
        else:
            yield event.plain_result(f"ℹ️ 当前预设 '{preset_name}' 没有设置前缀提示")

    @view_command_group.command("group")
    async def view_group(self, event: AstrMessageEvent, name: str):
        """查看指定名称的提示词组合详情"""
        if not self.controller.get_current_preset_name():
             yield event.plain_result("⚠️ 当前未选择预设")
             return
             
        groups = self.controller.get_prompt_groups()
        if name not in groups:
            yield event.plain_result(f"⚠️ 找不到名为 '{name}' 的提示词组合\n请使用 `/prompt group list` 查看所有组合")
            return
            
        indices = groups[name]
        all_prompts = self.controller.get_current_prompts()
        active_prompts = self.controller.get_active_prompts()
        
        result = f"**🧩 组合详情: {name}**\n\n"
        result += "**包含的提示词:**\n"
        
        if not indices:
            result += "  (此组合为空)\n"
        else:
            for idx in indices:
                if 0 <= idx < len(all_prompts):
                    prompt = all_prompts[idx]
                    prompt_name = prompt.get("name", "未命名")
                    is_active = prompt in active_prompts
                    active_marker = "✅" if is_active else "❌"
                    result += f"  {idx}. {active_marker} {prompt_name}\n"
                else:
                    result += f"  {idx}. (无效索引)\n"
                    
        result += "\n使用 `/prompt activate @{name}` 激活此组合"
        yield event.plain_result(result)

    # --- 自定义提示词 ---
    @prompt_command_group.command("add")
    async def add_prompt(self, event: AstrMessageEvent, name: str, *, content: Optional[str] = None):
        """
        添加自定义提示词到当前预设
        
        用法:
        - `/prompt add <名称> <内容>` 直接添加
        - `/prompt add <名称>` 然后在下一条消息发送内容
        """
        if not self.controller.get_current_preset_name():
            yield event.plain_result("⚠️ 当前未选择预设，无法添加提示词")
            return
            
        if content:
            # 直接添加
            success, message, prompt = self.controller.add_prompt(name, content)
            if success:
                logger.info(f"用户 {event.get_sender_id()} 添加提示词 '{name}' 成功")
                yield event.plain_result(f"✅ {message}")
            else:
                logger.warning(f"用户 {event.get_sender_id()} 添加提示词 '{name}' 失败: {message}")
                yield event.plain_result(f"⚠️ {message}")
        else:
            # 等待下一条消息
            try:
                # 发送等待提示
                yield event.plain_result(f"⏳ 请在 60 秒内输入提示词 **'{name}'** 的内容 (发送 '取消' 可中止)")
                
                # 等待用户回复
                next_event = await event.wait(timeout=60)
                
                # 获取回复内容
                new_content = next_event.get_plain_text().strip()
                
                if not new_content or new_content.lower() in ["取消", "cancel"]:
                    logger.info(f"用户 {event.get_sender_id()} 取消添加提示词 '{name}'")
                    yield event.plain_result(f"ℹ️ 已取消添加提示词 '{name}'")
                    return

                # 添加提示词
                success, message, prompt = self.controller.add_prompt(name, new_content)
                if success:
                    logger.info(f"用户 {event.get_sender_id()} 通过等待添加提示词 '{name}' 成功")
                    yield event.plain_result(f"✅ {message}")
                else:
                    logger.warning(f"用户 {event.get_sender_id()} 通过等待添加提示词 '{name}' 失败: {message}")
                    yield event.plain_result(f"⚠️ {message}")

            except TimeoutError:
                logger.warning(f"用户 {event.get_sender_id()} 添加提示词 '{name}' 超时")
                yield event.plain_result(f"⏰ 添加提示词 '{name}' 超时，已自动取消")
            except Exception as e:
                logger.error(f"处理添加提示词 '{name}' 时发生意外错误: {e}", exc_info=True)
                yield event.plain_result(f"❌ 处理添加提示词时发生内部错误，请查看日志")

    @prompt_command_group.command("delete")
    async def delete_prompt(self, event: AstrMessageEvent, index: int):
        """删除指定索引的用户自定义提示词"""
        success, message, prompt = self.controller.delete_prompt(index)
        if success:
            yield event.plain_result(f"✅ {message}")
        else:
            yield event.plain_result(f"⚠️ {message}")

    # --- 提示词组合管理子组 ---
    @prompt_command_group.group("group")
    def group_command_group(self):
        """提示词组合管理命令"""
        pass

    @group_command_group.command("list")
    async def list_groups(self, event: AstrMessageEvent):
        """列出当前预设的所有提示词组合"""
        if not self.controller.get_current_preset_name():
             yield event.plain_result("⚠️ 当前未选择预设")
             return
             
        groups = self.controller.get_prompt_groups()
        
        if not groups:
            yield event.plain_result("ℹ️ 当前预设没有定义任何提示词组合\n使用 `/prompt group create <组名> <索引列表>` 创建")
            return
            
        result = f"**🧩 当前预设 '{self.controller.get_current_preset_name()}' 的提示词组合:**\n\n"
        all_prompts = self.controller.get_current_prompts()
        
        for name, indices in groups.items():
            result += f"**@{name}**:\n"
            if not indices:
                result += "  (空组合)\n"
            else:
                prompt_names = []
                for idx in indices:
                    if 0 <= idx < len(all_prompts):
                        prompt_names.append(f"{idx}.{all_prompts[idx].get('name', '未命名')}")
                    else:
                        prompt_names.append(f"{idx}.(无效)")
                result += f"  包含: {', '.join(prompt_names)}\n"
            result += "\n"
            
        result += "使用 `/prompt activate @<组名>` 激活组合\n"
        result += "使用 `/prompt view group <组名>` 查看详情"
        yield event.plain_result(result)

    @group_command_group.command("create")
    async def create_group(self, event: AstrMessageEvent, name: str, indices_str: str):
        """
        创建提示词组合
        
        用法: /prompt group create <组名> <索引1,索引2,...>
        """
        try:
            indices = [int(i.strip()) for i in indices_str.split(',')]
        except ValueError:
            yield event.plain_result("⚠️ 索引列表格式错误，请使用逗号分隔的数字，例如: 0,1,5")
            return
            
        success, message = self.controller.create_prompt_group(name, indices)
        if success:
            yield event.plain_result(f"✅ {message}")
        else:
            yield event.plain_result(f"⚠️ {message}")

    @group_command_group.command("update")
    async def update_group(self, event: AstrMessageEvent, name: str, indices_str: str):
        """
        更新提示词组合
        
        用法: /prompt group update <组名> <索引1,索引2,...>
        """
        try:
            indices = [int(i.strip()) for i in indices_str.split(',')]
        except ValueError:
            yield event.plain_result("⚠️ 索引列表格式错误，请使用逗号分隔的数字，例如: 0,1,5")
            return
            
        success, message = self.controller.update_prompt_group(name, indices)
        if success:
            yield event.plain_result(f"✅ {message}")
        else:
            yield event.plain_result(f"⚠️ {message}")

    @group_command_group.command("delete")
    async def delete_group(self, event: AstrMessageEvent, name: str):
        """删除提示词组合"""
        success, message = self.controller.delete_prompt_group(name)
        if success:
            yield event.plain_result(f"✅ {message}")
        else:
            yield event.plain_result(f"⚠️ {message}")

    @filter.on_llm_request(priority=10)
    async def process_llm_request(self, event: AstrMessageEvent, *args, **kwargs):
        """在发送给LLM前处理请求，添加提示词"""
        logger.debug(f"process_llm_request 收到参数: args={args}, kwargs={kwargs}")

        req = None

        # 优先从 kwargs 里找
        for key in ("context", "request", "req", "provider_request"):
            if key in kwargs:
                req = kwargs[key]
                break

        # 再从位置参数里找
        if req is None:
            for arg in args:
                if isinstance(arg, dict) and (
                    "system_prompt" in arg or "user_prompt" in arg or "prompt" in arg
                ):
                    req = arg
                    break
                if hasattr(arg, "system_prompt") or hasattr(arg, "prompt"):
                    req = arg
                    break

        if req is None:
            logger.warning("process_llm_request: 未能识别 LLM 请求对象，跳过提示词处理")
            return

        # 统一取系统提示词和用户提示词
        if isinstance(req, dict):
            system_prompt = req.get("system_prompt", "") or ""
            user_prompt = req.get("user_prompt", "") or req.get("prompt", "") or ""
        else:
            system_prompt = getattr(req, "system_prompt", "") or ""
            user_prompt = getattr(req, "prompt", "") or getattr(req, "user_prompt", "") or ""

        modified_system, modified_user = self.controller.process_llm_request(system_prompt, user_prompt)

        # 回写
        if isinstance(req, dict):
            req["system_prompt"] = modified_system
            if "user_prompt" in req:
                req["user_prompt"] = modified_user
            else:
                req["prompt"] = modified_user
        else:
            req.system_prompt = modified_system
            if hasattr(req, "prompt"):
                req.prompt = modified_user
            elif hasattr(req, "user_prompt"):
                req.user_prompt = modified_user

        active_prompts = self.controller.get_active_prompts()
        prefix = self.controller.get_current_prefix()
        if active_prompts or prefix:
            logger.debug(f"已将前缀和 {len(active_prompts)} 个激活的提示词添加到LLM请求中")            
    @filter.on_astrbot_loaded()
    async def on_astrbot_loaded(self):
        """插件启动时执行"""
        logger.info("Prompt Tools 插件正在启动...")
        try:
            self.controller._initialize() # 确保控制器初始化
            logger.info("Prompt Tools 插件已成功启动")
            if not self.controller.get_preset_list():
                 data_dir = StarTools.get_data_dir("prompt_tools")
                 logger.warning(f"未找到任何预设，请添加预设JSON文件到 {data_dir / 'presets'} 目录并使用 /prompt refresh")
            elif not self.controller.get_current_preset_name():
                 logger.warning("未设置当前预设，请使用 /prompt use <索引> 选择一个预设")
        except Exception as e:
            logger.error(f"Prompt Tools 插件启动失败: {e}", exc_info=True)

    async def terminate(self):
        """插件停止时执行"""
        logger.info("Prompt Tools 插件已停止")
