"""
提示词工具控制器模块

负责协调各个管理器类的工作，实现业务逻辑
"""
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from astrbot.api import logger

from .extractor import PromptExtractor
from .presets import PresetsManager
from .prompts import PromptsManager
from .groups import GroupsManager

class Controller:
    """提示词工具控制器类"""
    
    def __init__(self, presets_folder: Path, output_folder: Path):
        """
        初始化控制器
        
        Args:
            presets_folder: 预设JSON文件所在的文件夹路径
            output_folder: 提取的提示信息保存的文件夹路径
        """
        self.presets_folder = presets_folder
        self.output_folder = output_folder
        
        # 当前选中的预设名称
        self.current_preset_name = ""
        
        # 初始化各个管理器
        self.presets_manager = PresetsManager(self.presets_folder, self.output_folder)
        self.prompts_manager = PromptsManager(self.output_folder)
        self.groups_manager = GroupsManager(self.presets_folder)
        
        # 初始化
        self._initialize()
    
    def _initialize(self):
        """初始化控制器，提取提示词并加载第一个JSON文件"""
        logger.info("正在初始化提示词工具...")
        
        # 确保必要的文件夹存在
        self._ensure_directory_exists(self.presets_folder)
        self._ensure_directory_exists(self.output_folder)
        
        # 加载提示词数据
        self.presets_manager.load_presets()
        
        # 设置默认预设
        preset_list = self.presets_manager.get_preset_list()
        if preset_list:
            self.current_preset_name = preset_list[0]
            # 加载该预设的提示词组合配置
            self.groups_manager.load_prompt_groups(self.current_preset_name)
            logger.info(f"已设置默认预设: {self.current_preset_name}")
        else:
            logger.warning("没有找到可用的预设文件")
    
    def _ensure_directory_exists(self, directory: Path) -> None:
        """确保目录存在，如果不存在则创建"""
        if not directory.exists():
            directory.mkdir(parents=True)
            logger.info(f"创建目录: {directory}")
    
    # 预设相关方法
    
    def get_preset_list(self) -> List[str]:
        """获取所有可用预设的列表"""
        return self.presets_manager.get_preset_list()
    
    def get_current_preset_name(self) -> str:
        """获取当前选中的预设名称"""
        return self.current_preset_name
    
    def switch_preset(self, index: int) -> Tuple[bool, str]:
        """
        切换到指定索引的预设
        
        Args:
            index: 预设索引
        
        Returns:
            (成功标志, 消息)
        """
        presets = self.get_preset_list()
        
        if not presets:
            return False, "没有可用的预设"
        
        if 0 <= index < len(presets):
            # 清空当前激活的提示
            self.prompts_manager.clear_active_prompts()
            
            # 设置新的预设
            self.current_preset_name = presets[index]
            
            # 加载该预设的提示词组合配置
            self.groups_manager.load_prompt_groups(self.current_preset_name)
            
            return True, f"已切换至预设: {self.current_preset_name}"
        else:
            return False, f"无效的预设索引: {index}"
    
    def create_preset(self, name: str) -> Tuple[bool, str]:
        """
        创建新的预设文件夹
        
        Args:
            name: 预设名称
        
        Returns:
            (成功标志, 消息)
        """
        if not name:
            return False, "预设名称不能为空"
        
        # 创建预设
        if self.presets_manager.create_preset(name):
            # 切换到新预设
            self.current_preset_name = name
            # 清空当前激活的提示词
            self.prompts_manager.clear_active_prompts()
            # 清空组合配置
            self.groups_manager.prompt_groups = {}
            
            return True, f"已创建新预设: {name}"
        else:
            return False, f"创建预设 '{name}' 失败，预设可能已存在"
    
    def refresh_prompts(self) -> Tuple[bool, str, Dict[str, Any]]:
        """
        重新提取和加载所有提示词
        
        Returns:
            (成功标志, 消息, 统计信息)
        """
        # 提取提示词
        if self.presets_manager.extract_prompts():
            # 重新加载提示词
            self.presets_manager.load_presets()
            
            # 清空当前激活的提示词
            self.prompts_manager.clear_active_prompts()
            
            # 重置当前预设
            preset_list = self.get_preset_list()
            if preset_list:
                self.current_preset_name = preset_list[0]
                # 加载该预设的组合配置
                self.groups_manager.load_prompt_groups(self.current_preset_name)
            
            # 统计加载的预设数量和提示词总数
            preset_count = len(self.presets_manager.presets)
            prompt_count = sum(len(prompts) for prompts in self.presets_manager.presets.values())
            
            stats = {
                "preset_count": preset_count,
                "prompt_count": prompt_count
            }
            
            if preset_count > 0:
                return True, f"成功重新加载 {preset_count} 个预设，共 {prompt_count} 个提示词", stats
            else:
                return True, "没有找到可用的预设，请检查预设文件", stats
        else:
            return False, "提取提示词失败，请检查日志获取详细错误信息", {}
    
    # 提示词相关方法
    
    def get_current_prompts(self) -> List[Dict[str, Any]]:
        """获取当前选中预设的所有提示"""
        if not self.current_preset_name:
            return []
        return self.presets_manager.get_prompts(self.current_preset_name)
    
    def get_current_prefix(self) -> str:
        """获取当前预设的前缀提示内容"""
        if not self.current_preset_name:
            return ""
        return self.presets_manager.get_prefix(self.current_preset_name)
    
    def get_active_prompts(self) -> List[Dict[str, Any]]:
        """获取当前激活的提示词列表"""
        return self.prompts_manager.active_prompts
    
    def activate_prompt(self, index: int) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        激活单个提示词
        
        Args:
            index: 提示词索引
        
        Returns:
            (成功标志, 消息, 激活的提示词)
        """
        all_prompts = self.get_current_prompts()
        
        if not all_prompts:
            return False, "当前预设中没有可用的提示词", None
        
        if 0 <= index < len(all_prompts):
            prompt = all_prompts[index]
            
            # 检查提示是否已经激活
            if prompt in self.prompts_manager.active_prompts:
                return True, f"提示词 \"{prompt['name']}\" 已经激活", prompt
            
            newly_active = self.prompts_manager.activate_prompts(all_prompts, [index])
            if newly_active:
                return True, f"已激活提示词: {prompt['name']}", prompt
            else:
                return False, "激活提示词失败", None
        else:
            return False, f"无效的提示词索引: {index}", None
    
    def activate_prompt_group(self, group_name: str) -> Tuple[bool, str, List[Dict[str, Any]]]:
        """
        激活提示词组合
        
        Args:
            group_name: 组合名称
            
        Returns:
            (成功标志, 消息, 新激活的提示词列表)
        """
        all_prompts = self.get_current_prompts()
        
        if not all_prompts:
            return False, "当前预设中没有可用的提示词", []
        
        if not group_name:
            return False, "组合名称不能为空", []
        
        # 获取组合中的提示词索引
        indices = self.groups_manager.get_prompt_group(group_name)
        
        if not indices:
            return False, f"找不到组合 '{group_name}' 或组合为空", []
        
        # 激活组合中的所有提示词
        newly_active = self.prompts_manager.activate_prompts(all_prompts, indices)
        
        if newly_active:
            return True, f"已激活组合 '{group_name}' 中的 {len(newly_active)} 个提示词", newly_active
        else:
            return True, f"组合 '{group_name}' 中的提示词已全部激活", []
    
    def deactivate_prompt(self, index: int) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        关闭指定索引的激活提示词
        
        Args:
            index: 激活提示词索引
            
        Returns:
            (成功标志, 消息, 关闭的提示词)
        """
        if not self.prompts_manager.active_prompts:
            return False, "当前没有已激活的提示词", None
        
        if 0 <= index < len(self.prompts_manager.active_prompts):
            removed_prompt = self.prompts_manager.deactivate_prompt(index)
            if removed_prompt:
                return True, f"已关闭提示词: {removed_prompt['name']}", removed_prompt
            else:
                return False, "关闭提示词失败", None
        else:
            return False, f"无效的激活提示词索引: {index}", None
    
    def clear_active_prompts(self) -> Tuple[bool, str, int]:
        """
        清空当前激活的所有提示词
        
        Returns:
            (成功标志, 消息, 清空的提示词数量)
        """
        count = self.prompts_manager.clear_active_prompts()
        
        if count == 0:
            return True, "当前没有激活的提示词", 0
        else:
            return True, f"已清空 {count} 个激活的提示词", count
    
    def add_prompt(self, name: str, content: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        添加新的提示词到当前预设
        
        Args:
            name: 提示词名称
            content: 提示词内容
            
        Returns:
            (成功标志, 消息, 添加的提示词)
        """
        if not self.current_preset_name:
            return False, "当前未选择预设", None
        
        if not name:
            return False, "提示词名称不能为空", None
            
        if not content:
            return False, "提示词内容不能为空", None
        
        # 添加提示词
        prompt = self.prompts_manager.add_prompt_to_preset(name, content, self.current_preset_name, self.presets_manager.presets)
        
        if prompt:
            return True, f"成功添加提示词: {name}", prompt
        else:
            return False, "添加提示词失败", None
    
    def delete_prompt(self, index: int) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        删除指定索引的提示词
        
        Args:
            index: 提示词索引
            
        Returns:
            (成功标志, 消息, 删除的提示词)
        """
        if not self.current_preset_name:
            return False, "当前未选择预设", None
        
        all_prompts = self.get_current_prompts()
        
        if not all_prompts:
            return False, "当前预设中没有可用的提示词", None
        
        deleted_prompt = self.prompts_manager.delete_prompt(index, self.current_preset_name, all_prompts)
        
        if deleted_prompt:
            return True, f"已删除提示词: {deleted_prompt['name']}", deleted_prompt
        else:
            return False, "无效的提示词索引或提示词不是由用户创建的", None
    
    # 提示词组合相关方法
    
    def get_prompt_groups(self) -> Dict[str, List[int]]:
        """获取当前预设的所有提示词组合"""
        return self.groups_manager.get_all_groups()
    
    def get_prompt_group(self, name: str) -> List[int]:
        """
        获取指定名称的提示词组合
        
        Args:
            name: 组合名称
            
        Returns:
            提示词索引列表
        """
        return self.groups_manager.get_prompt_group(name)
    
    def create_prompt_group(self, name: str, indices: List[int]) -> Tuple[bool, str]:
        """
        创建提示词组合
        
        Args:
            name: 组合名称
            indices: 提示词索引列表
            
        Returns:
            (成功标志, 消息)
        """
        if not self.current_preset_name:
            return False, "当前未选择预设"
        
        # 检查组合名称
        if not name:
            return False, "组合名称不能为空"
        
        all_prompts = self.get_current_prompts()
        
        # 创建组合
        if self.groups_manager.create_prompt_group(name, indices, self.current_preset_name, all_prompts):
            return True, f"已创建提示词组合: {name}"
        else:
            return False, f"创建组合 '{name}' 失败，组名可能已存在或索引无效"
    
    def update_prompt_group(self, name: str, indices: List[int]) -> Tuple[bool, str]:
        """
        更新提示词组合
        
        Args:
            name: 组合名称
            indices: 提示词索引列表
            
        Returns:
            (成功标志, 消息)
        """
        if not self.current_preset_name:
            return False, "当前未选择预设"
        
        # 检查组合是否存在
        if name not in self.groups_manager.prompt_groups:
            return False, f"组合 '{name}' 不存在"
        
        all_prompts = self.get_current_prompts()
        
        # 更新组合
        if self.groups_manager.update_prompt_group(name, indices, self.current_preset_name, all_prompts):
            return True, f"已更新提示词组合: {name}"
        else:
            return False, f"更新组合 '{name}' 失败，请检查索引是否有效"
    
    def delete_prompt_group(self, name: str) -> Tuple[bool, str]:
        """
        删除提示词组合
        
        Args:
            name: 组合名称
            
        Returns:
            (成功标志, 消息)
        """
        if not self.current_preset_name:
            return False, "当前未选择预设"
        
        # 检查组合是否存在
        if name not in self.groups_manager.prompt_groups:
            return False, f"组合 '{name}' 不存在"
        
        # 删除组合
        if self.groups_manager.delete_prompt_group(name, self.current_preset_name):
            return True, f"已删除提示词组合: {name}"
        else:
            return False, f"删除组合 '{name}' 失败"
    
    # 辅助方法
    
    def process_llm_request(self, system_prompt: str, user_prompt: str) -> Tuple[str, str]:
        """
        处理LLM请求，添加前缀提示和激活的提示词
        
        Args:
            system_prompt: 系统提示词
            user_prompt: 用户提示词
            
        Returns:
            (修改后的系统提示词, 修改后的用户提示词)
        """
        active_prompts = self.get_active_prompts()
        current_prefix = self.get_current_prefix()
        
        modified_system = system_prompt
        modified_user = user_prompt
        
        # 添加前缀提示到system_prompt
        if current_prefix:
            if modified_system:
                # 将前缀提示添加到现有系统提示之前
                modified_system = f"{current_prefix}\n\n{modified_system}"
            else:
                modified_system = current_prefix
        
        # 添加激活的提示词到用户提示词前
        if active_prompts:
            # 构建激活的提示词内容
            active_content = ""
            for prompt in active_prompts:
                active_content += f"\n\n{prompt.get('content', '')}"
            
            # 将激活的提示词添加到用户提示词前
            modified_user = f"{active_content}\n\n{modified_user}"
        
        return modified_system, modified_user
    
    def terminate(self):
        """停用控制器，清理资源"""
        # 清空激活的提示词
        self.prompts_manager.clear_active_prompts()