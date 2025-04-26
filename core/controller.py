"""
提示词工具控制器模块

负责协调各个管理器类的工作，实现业务逻辑
"""
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from astrbot.api import logger
import traceback

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
        try:
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
                # 加载预设的激活状态
                current_prompts = self.get_current_prompts()
                self.prompts_manager.load_activation_state(self.current_preset_name, current_prompts)
                logger.info(f"已设置默认预设: {self.current_preset_name}")
            else:
                logger.warning("没有找到可用的预设文件")
        except Exception as e:
            logger.error(f"控制器初始化失败: {e}\n{traceback.format_exc()}")
            raise
    
    def _ensure_directory_exists(self, directory: Path) -> None:
        """确保目录存在，如果不存在则创建"""
        try:
            if not directory.exists():
                directory.mkdir(parents=True)
                logger.info(f"创建目录: {directory}")
        except OSError as e:
            logger.error(f"创建目录 {directory} 失败: {e}", exc_info=True)
    
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
        try:
            presets = self.get_preset_list()
            
            if not presets:
                logger.warning("尝试切换预设，但列表为空")
                return False, "没有可用的预设"
            
            if 0 <= index < len(presets):
                old_preset = self.current_preset_name
                # 清空当前激活的提示
                self.prompts_manager.clear_active_prompts()
                
                # 设置新的预设
                self.current_preset_name = presets[index]
                
                # 加载该预设的提示词组合配置
                self.groups_manager.load_prompt_groups(self.current_preset_name)
                
                # 加载该预设的激活状态
                current_prompts = self.get_current_prompts()
                self.prompts_manager.load_activation_state(self.current_preset_name, current_prompts)
                
                logger.info(f"预设已从 '{old_preset}' 切换至 '{self.current_preset_name}'")
                return True, f"已切换至预设: {self.current_preset_name}"
            else:
                logger.warning(f"尝试切换到无效的预设索引: {index}")
                return False, f"无效的预设索引: {index}"
        except Exception as e:
            logger.error(f"切换预设时发生错误: {e}", exc_info=True)
            return False, "切换预设时发生内部错误"
    
    def create_preset(self, name: str) -> Tuple[bool, str]:
        """
        创建新的预设文件夹
        
        Args:
            name: 预设名称
        
        Returns:
            (成功标志, 消息)
        """
        try:
            if not name:
                logger.warning("尝试创建预设但名称为空")
                return False, "预设名称不能为空"
            
            # 创建预设
            if self.presets_manager.create_preset(name):
                # 切换到新预设
                self.current_preset_name = name
                # 清空当前激活的提示词
                self.prompts_manager.clear_active_prompts()
                # 清空组合配置
                self.groups_manager.prompt_groups = {}
                logger.info(f"已创建并切换到新预设: {name}")
                return True, f"已创建新预设: {name}"
            else:
                return False, f"创建预设 '{name}' 失败，预设可能已存在"
        except Exception as e:
            logger.error(f"创建预设 '{name}' 时发生错误: {e}", exc_info=True)
            return False, f"创建预设 '{name}' 时发生内部错误"
    
    def refresh_prompts(self) -> Tuple[bool, str, Dict[str, Any]]:
        """
        重新提取和加载所有提示词
        
        Returns:
            (成功标志, 消息, 统计信息)
        """
        logger.info("开始刷新提示词...")
        try:
            # 提取提示词
            if self.presets_manager.extract_prompts():
                # 重新加载提示词
                self.presets_manager.load_presets()
                
                # 清空当前激活的提示词
                self.prompts_manager.clear_active_prompts()
                
                # 重置当前预设
                preset_list = self.get_preset_list()
                old_preset = self.current_preset_name
                if preset_list:
                    self.current_preset_name = preset_list[0]
                    # 加载该预设的组合配置
                    self.groups_manager.load_prompt_groups(self.current_preset_name)
                    logger.info(f"刷新后，当前预设设置为: {self.current_preset_name}")
                else:
                    self.current_preset_name = ""
                    logger.warning("刷新后未找到可用预设")

                # 统计加载的预设数量和提示词总数
                preset_count = len(self.presets_manager.presets)
                prompt_count = sum(len(prompts) for prompts in self.presets_manager.presets.values())
                
                stats = {
                    "preset_count": preset_count,
                    "prompt_count": prompt_count
                }
                logger.info(f"提示词刷新完成。加载了 {stats['preset_count']} 个预设，共 {stats['prompt_count']} 个提示词。")
                if stats['preset_count'] > 0:
                    return True, f"成功重新加载 {stats['preset_count']} 个预设，共 {stats['prompt_count']} 个提示词", stats
                else:
                    return True, "没有找到可用的预设，请检查预设文件", stats
            else:
                logger.error("刷新提示词失败：提取步骤出错")
                return False, "提取提示词失败，请检查日志获取详细错误信息", {}
        except Exception as e:
            logger.error(f"刷新提示词时发生严重错误: {e}", exc_info=True)
            return False, "刷新提示词时发生内部错误", {}
    
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
        try:
            all_prompts = self.get_current_prompts()
            
            if not all_prompts:
                logger.warning(f"尝试激活索引 {index}，但当前预设 '{self.current_preset_name}' 无提示词")
                return False, "当前预设中没有可用的提示词", None
            
            if 0 <= index < len(all_prompts):
                prompt = all_prompts[index]
                prompt_name = prompt.get('name', '未命名')
                
                # 检查提示是否已经激活
                if prompt in self.prompts_manager.active_prompts:
                    logger.debug(f"提示词 '{prompt_name}' (索引 {index}) 已激活")
                    return True, f"提示词 \"{prompt_name}\" 已经激活", prompt
                
                newly_active = self.prompts_manager.activate_prompts(all_prompts, [index])
                if newly_active:
                    # 保存激活状态
                    self.prompts_manager.save_activation_state(self.current_preset_name, all_prompts)
                    logger.info(f"已激活提示词: '{prompt_name}' (索引 {index})")
                    return True, f"已激活提示词: {prompt_name}", prompt
                else:
                    logger.error(f"尝试激活提示词 '{prompt_name}' (索引 {index}) 失败，但它并未被报告为已激活")
                    return False, "激活提示词失败 (内部逻辑错误)", None
            else:
                logger.warning(f"尝试激活无效索引 {index} (共 {len(all_prompts)} 个提示词)")
                return False, f"无效的提示词索引: {index}", None
        except Exception as e:
            logger.error(f"激活提示词索引 {index} 时发生错误: {e}", exc_info=True)
            return False, "激活提示词时发生内部错误", None
    
    def activate_multiple_prompts(self, indices: List[int]) -> Tuple[bool, str, List[Dict[str, Any]]]:
        """
        激活多个提示词索引
        
        Args:
            indices: 提示词索引列表
            
        Returns:
            (成功标志, 消息, 新激活的提示词列表)
        """
        try:
            if not indices:
                logger.warning("尝试激活空的索引列表")
                return False, "提示词索引列表不能为空", []
                
            all_prompts = self.get_current_prompts()
            
            if not all_prompts:
                logger.warning(f"尝试激活多个索引，但当前预设 '{self.current_preset_name}' 无提示词")
                return False, "当前预设中没有可用的提示词", []
                
            # 检查索引是否有效
            invalid_indices = []
            max_index = len(all_prompts) - 1
            for idx in indices:
                if not (0 <= idx <= max_index):
                    invalid_indices.append(idx)
                    
            if invalid_indices:
                logger.warning(f"激活提示词时发现无效索引: {invalid_indices} (有效范围: 0-{max_index})")
                return False, f"无效的提示词索引: {', '.join(map(str, invalid_indices))}，有效范围: 0-{max_index}", []
                
            # 激活所有有效索引对应的提示词
            newly_active = self.prompts_manager.activate_prompts(all_prompts, indices)
            
            if newly_active:
                # 保存激活状态
                self.prompts_manager.save_activation_state(self.current_preset_name, all_prompts)
                
                activated_names = [p.get('name', '未命名') for p in newly_active]
                logger.info(f"已激活 {len(newly_active)} 个提示词: {activated_names}")
                return True, f"已成功激活 {len(newly_active)} 个提示词", newly_active
            else:
                # 可能所有提示词都已经被激活
                logger.info("所选提示词均已激活，无需重复激活")
                return True, "所选提示词均已激活", []
        except Exception as e:
            logger.error(f"激活多个提示词索引时发生错误: {e}", exc_info=True)
            return False, "激活多个提示词时发生内部错误", []
    
    def activate_prompt_group(self, group_name: str) -> Tuple[bool, str, List[Dict[str, Any]]]:
        """
        激活提示词组合
        
        Args:
            group_name: 组合名称
            
        Returns:
            (成功标志, 消息, 新激活的提示词列表)
        """
        try:
            all_prompts = self.get_current_prompts()
            
            if not all_prompts:
                 logger.warning(f"尝试激活组合 '{group_name}'，但当前预设 '{self.current_preset_name}' 无提示词")
                 return False, "当前预设中没有可用的提示词", []
            
            if not group_name:
                 logger.warning("尝试激活组合但名称为空")
                 return False, "组合名称不能为空", []
            
            # 获取组合中的提示词索引
            indices = self.groups_manager.get_prompt_group(group_name)
            
            if indices is None:
                 logger.warning(f"找不到组合 '{group_name}'")
                 return False, f"找不到组合 '{group_name}'", []
            if not indices:
                 logger.info(f"组合 '{group_name}' 为空，无需激活")
                 return False, f"组合 '{group_name}' 为空", []

            # 激活组合中的所有提示词
            newly_active = self.prompts_manager.activate_prompts(all_prompts, indices)
            
            if newly_active:
                activated_names = [p.get('name', '未命名') for p in newly_active]
                logger.info(f"已激活组合 '{group_name}' 中的 {len(newly_active)} 个提示词: {activated_names}")
                return True, f"已激活组合 '{group_name}' 中的 {len(newly_active)} 个提示词", newly_active
            else:
                logger.info(f"组合 '{group_name}' 中的提示词已全部激活")
                return True, f"组合 '{group_name}' 中的提示词已全部激活", []
        except Exception as e:
            logger.error(f"激活组合 '{group_name}' 时发生错误: {e}", exc_info=True)
            return False, f"激活组合 '{group_name}' 时发生内部错误", []
    
    def deactivate_prompt(self, index: int) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        关闭指定索引的激活提示词
        
        Args:
            index: 激活提示词索引
            
        Returns:
            (成功标志, 消息, 关闭的提示词)
        """
        try:
            if not self.prompts_manager.active_prompts:
                logger.warning("尝试关闭提示词，但当前无激活提示词")
                return False, "当前没有已激活的提示词", None
            
            if 0 <= index < len(self.prompts_manager.active_prompts):
                removed_prompt = self.prompts_manager.deactivate_prompt(index)
                if removed_prompt:
                    # 保存激活状态
                    all_prompts = self.get_current_prompts()
                    self.prompts_manager.save_activation_state(self.current_preset_name, all_prompts)
                    
                    prompt_name = removed_prompt.get('name', '未命名')
                    logger.info(f"已关闭激活列表索引 {index} 对应的提示词: '{prompt_name}'")
                    return True, f"已关闭提示词: {prompt_name}", removed_prompt
                else:
                    logger.error(f"尝试关闭激活列表索引 {index} 失败")
                    return False, "关闭提示词失败 (内部逻辑错误)", None
            else:
                logger.warning(f"尝试关闭无效的激活列表索引: {index} (共 {len(self.prompts_manager.active_prompts)} 个)")
                return False, f"无效的激活提示词索引: {index}", None
        except Exception as e:
            logger.error(f"关闭激活列表索引 {index} 时发生错误: {e}", exc_info=True)
            return False, "关闭提示词时发生内部错误", None
    
    def deactivate_multiple_prompts(self, indices: List[int]) -> Tuple[bool, str, List[Dict[str, Any]]]:
        """
        关闭多个激活提示词索引
        
        Args:
            indices: 激活提示词索引列表
            
        Returns:
            (成功标志, 消息, 被关闭的提示词列表)
        """
        try:
            if not indices:
                logger.warning("尝试关闭空的索引列表")
                return False, "提示词索引列表不能为空", []
            
            active_prompts = self.prompts_manager.active_prompts
            if not active_prompts:
                logger.warning("尝试关闭多个提示词，但当前无激活提示词")
                return False, "当前没有已激活的提示词", []
            
            # 检查索引是否有效
            invalid_indices = []
            max_index = len(active_prompts) - 1
            valid_indices = []
            
            for idx in indices:
                if 0 <= idx <= max_index:
                    valid_indices.append(idx)
                else:
                    invalid_indices.append(idx)
            
            if invalid_indices and not valid_indices:
                logger.warning(f"关闭提示词时所有索引均无效: {invalid_indices} (有效范围: 0-{max_index})")
                return False, f"无效的激活提示词索引: {', '.join(map(str, invalid_indices))}，有效范围: 0-{max_index}", []
            
            if invalid_indices:
                logger.warning(f"关闭提示词时发现部分无效索引: {invalid_indices}，将忽略这些索引")
            
            # 按照从大到小的顺序排序索引，以避免移除早期索引后导致后续索引错位
            valid_indices.sort(reverse=True)
            
            # 关闭所有有效索引对应的提示词
            deactivated_prompts = []
            for idx in valid_indices:
                # 由于我们是从大到小移除，索引不会变化
                removed_prompt = self.prompts_manager.deactivate_prompt(idx)
                if removed_prompt:
                    deactivated_prompts.append(removed_prompt)
            
            if deactivated_prompts:
                deactivated_names = [p.get('name', '未命名') for p in deactivated_prompts]
                logger.info(f"已关闭 {len(deactivated_prompts)} 个提示词: {deactivated_names}")
                return True, f"已成功关闭 {len(deactivated_prompts)} 个提示词", deactivated_prompts
            else:
                # 可能所有提示词索引都无效，或者其他问题导致无法关闭
                logger.warning("未能关闭任何提示词")
                return False, "未能关闭任何提示词", []
        except Exception as e:
            logger.error(f"关闭多个提示词索引时发生错误: {e}", exc_info=True)
            return False, "关闭多个提示词时发生内部错误", []
    
    def deactivate_prompt_group(self, group_name: str) -> Tuple[bool, str, List[Dict[str, Any]]]:
        """
        关闭指定组合中的所有提示词
        
        Args:
            group_name: 组合名称
            
        Returns:
            (成功标志, 消息, 被关闭的提示词列表)
        """
        logger.info(f"请求关闭组合 '{group_name}' 中的提示词")
        try:
            if not self.current_preset_name:
                logger.warning(f"尝试关闭组合 '{group_name}' 但未选择预设")
                return False, "当前未选择预设", []
                
            if not group_name:
                logger.warning("尝试关闭组合但名称为空")
                return False, "组合名称不能为空", []

            # 获取组合中的提示词索引 (相对于完整预设列表)
            indices = self.groups_manager.get_prompt_group(group_name)
            
            if indices is None: # 组合在当前预设的组合配置中不存在
                logger.warning(f"找不到要关闭的组合 '{group_name}' (在预设 '{self.current_preset_name}' 的组合配置中)")
                return False, f"找不到组合 '{group_name}'", []
            if not indices:
                logger.info(f"组合 '{group_name}' 为空，无需关闭")
                return True, f"组合 '{group_name}' 为空，无需关闭", [] # 成功，但没有要做的事情

            # 获取当前预设的所有提示词
            all_prompts = self.get_current_prompts()
            if not all_prompts:
                 logger.warning(f"尝试关闭组合 '{group_name}'，但当前预设 '{self.current_preset_name}' 无提示词")
                 # 如果找到了索引，这种情况不太可能发生，但仍需检查
                 return False, "当前预设中没有可用的提示词", []

            # 根据索引找到对应的提示词对象 (从完整的预设列表)
            prompts_to_deactivate = []
            invalid_indices_in_group = []
            max_index = len(all_prompts) - 1
            for idx in indices:
                if 0 <= idx <= max_index:
                    prompts_to_deactivate.append(all_prompts[idx])
                else:
                    # 这表明保存的组合数据与当前的提示词不一致
                    invalid_indices_in_group.append(idx)
            
            if invalid_indices_in_group:
                 logger.error(f"组合 '{group_name}' 包含无效索引: {invalid_indices_in_group} (当前提示词范围 0-{max_index})。可能需要刷新或编辑组合。将尝试关闭有效索引对应的提示词。")
                 # 继续处理有效的索引

            if not prompts_to_deactivate:
                logger.warning(f"组合 '{group_name}' 中的索引均无效或未找到对应提示词，无法关闭")
                return False, f"组合 '{group_name}' 中的索引无效或未找到对应提示词", []

            # 调用 PromptsManager 关闭这些提示词 (使用引用比较)
            deactivated_prompts = self.prompts_manager.deactivate_prompts_by_reference(prompts_to_deactivate)
            
            if deactivated_prompts:
                deactivated_names = [p.get('name', '未命名') for p in deactivated_prompts]
                logger.info(f"已关闭组合 '{group_name}' 中的 {len(deactivated_prompts)} 个提示词: {deactivated_names}")
                return True, f"已关闭组合 '{group_name}' 中的 {len(deactivated_prompts)} 个提示词", deactivated_prompts
            else:
                logger.info(f"组合 '{group_name}' 中的提示词 ({len(prompts_to_deactivate)} 个有效) 均未激活，无需关闭")
                return True, f"组合 '{group_name}' 中的提示词均未激活", [] # 成功，但没有提示词被激活

        except Exception as e:
            logger.error(f"关闭组合 '{group_name}' 时发生错误: {e}", exc_info=True)
            return False, f"关闭组合 '{group_name}' 时发生内部错误", []

    def clear_active_prompts(self) -> Tuple[bool, str, int]:
        """
        清空当前激活的所有提示词
        
        Returns:
            (成功标志, 消息, 清空的提示词数量)
        """
        try:
            count = self.prompts_manager.clear_active_prompts()
            if count == 0:
                logger.info("尝试清空激活提示词，但列表已为空")
                return True, "当前没有激活的提示词", 0
            else:
                logger.info(f"已清空 {count} 个激活的提示词")
                return True, f"已清空 {count} 个激活的提示词", count
        except Exception as e:
            logger.error(f"清空激活提示词时发生错误: {e}", exc_info=True)
            return False, "清空激活提示词时发生内部错误", -1
    
    def add_prompt(self, name: str, content: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        添加新的提示词到当前预设
        
        Args:
            name: 提示词名称
            content: 提示词内容
            
        Returns:
            (成功标志, 消息, 添加的提示词)
        """
        try:
            if not self.current_preset_name:
                 logger.warning("尝试添加提示词但未选择预设")
                 return False, "当前未选择预设", None
            
            if not name:
                 logger.warning("尝试添加提示词但名称为空")
                 return False, "提示词名称不能为空", None
                 
            if not content:
                 logger.warning(f"尝试添加提示词 '{name}' 但内容为空")
                 return False, "提示词内容不能为空", None
            
            # 添加提示词
            prompt = self.prompts_manager.add_prompt_to_preset(name, content, self.current_preset_name, self.presets_manager.presets)
            
            if prompt:
                logger.info(f"成功添加提示词 '{name}' 到预设 '{self.current_preset_name}'")
                return True, f"成功添加提示词: {name}", prompt
            else:
                return False, "添加提示词失败 (可能是文件写入错误)", None
        except Exception as e:
            logger.error(f"添加提示词 '{name}' 时发生错误: {e}", exc_info=True)
            return False, "添加提示词时发生内部错误", None
    
    def update_prompt(self, index: int, name: str, content: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        修改指定索引的提示词
        
        Args:
            index: 提示词索引
            name: 新的提示词名称
            content: 新的提示词内容
            
        Returns:
            (成功标志, 消息, 修改后的提示词)
        """
        try:
            if not self.current_preset_name:
                logger.warning("尝试修改提示词但未选择预设")
                return False, "当前未选择预设", None
            
            if not name:
                logger.warning("尝试修改提示词但新名称为空")
                return False, "提示词名称不能为空", None
                
            if not content:
                logger.warning(f"尝试修改提示词但新内容为空")
                return False, "提示词内容不能为空", None
            
            all_prompts = self.get_current_prompts()
            
            if not all_prompts:
                logger.warning(f"尝试修改索引 {index}，但当前预设 '{self.current_preset_name}' 无提示词")
                return False, "当前预设中没有可用的提示词", None
            
            if not (0 <= index < len(all_prompts)):
                logger.warning(f"尝试修改无效索引 {index} (共 {len(all_prompts)} 个提示词)")
                return False, f"无效的提示词索引: {index}", None
            
            # 获取原始提示词信息
            original_prompt = all_prompts[index]
            original_name = original_prompt.get('name', '未命名')
            
            # 调用PromptsManager的update_prompt方法进行修改
            updated_prompt = self.prompts_manager.update_prompt(
                index, name, content, self.current_preset_name, all_prompts
            )
            
            if updated_prompt:
                logger.info(f"已将提示词 '{original_name}' 修改为 '{name}'")
                return True, f"已修改提示词: {name}", updated_prompt
            else:
                return False, "修改提示词失败 (无效索引、非用户创建或文件错误)", None
                
        except Exception as e:
            logger.error(f"修改提示词索引 {index} 时发生错误: {e}", exc_info=True)
            return False, "修改提示词时发生内部错误", None
    
    def delete_prompt(self, index: int) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        删除指定索引的提示词
        
        Args:
            index: 提示词索引
            
        Returns:
            (成功标志, 消息, 删除的提示词)
        """
        try:
            if not self.current_preset_name:
                 logger.warning("尝试删除提示词但未选择预设")
                 return False, "当前未选择预设", None
            
            all_prompts = self.get_current_prompts()
            
            if not all_prompts:
                 logger.warning(f"尝试删除索引 {index}，但当前预设 '{self.current_preset_name}' 无提示词")
                 return False, "当前预设中没有可用的提示词", None

            if not (0 <= index < len(all_prompts)):
                logger.warning(f"尝试删除无效索引 {index} (共 {len(all_prompts)} 个提示词)")
                return False, f"无效的提示词索引: {index}", None

            deleted_prompt = self.prompts_manager.delete_prompt(index, self.current_preset_name, all_prompts)
            
            if deleted_prompt:
                prompt_name = deleted_prompt.get('name', '未命名')
                logger.info(f"已删除提示词 '{prompt_name}' (原索引 {index}) 从预设 '{self.current_preset_name}'")
                return True, f"已删除提示词: {prompt_name}", deleted_prompt
            else:
                return False, "删除提示词失败 (无效索引、非用户创建或文件错误)", None
        except Exception as e:
            logger.error(f"删除提示词索引 {index} 时发生错误: {e}", exc_info=True)
            return False, "删除提示词时发生内部错误", None
    
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
        try:
            if not self.current_preset_name:
                logger.warning("尝试创建组合但未选择预设")
                return False, "当前未选择预设"
            
            if not name:
                logger.warning("尝试创建组合但名称为空")
                return False, "组合名称不能为空"
            
            all_prompts = self.get_current_prompts()
            
            if self.groups_manager.create_prompt_group(name, indices, self.current_preset_name, all_prompts):
                logger.info(f"已为预设 '{self.current_preset_name}' 创建提示词组合: '{name}'")
                return True, f"已创建提示词组合: {name}"
            else:
                return False, f"创建组合 '{name}' 失败 (组名已存在、索引无效或保存错误)"
        except Exception as e:
            logger.error(f"创建组合 '{name}' 时发生错误: {e}", exc_info=True)
            return False, f"创建组合 '{name}' 时发生内部错误"
    
    def update_prompt_group(self, name: str, indices: List[int]) -> Tuple[bool, str]:
        """
        更新提示词组合
        
        Args:
            name: 组合名称
            indices: 提示词索引列表
            
        Returns:
            (成功标志, 消息)
        """
        try:
            if not self.current_preset_name:
                logger.warning(f"尝试更新组合 '{name}' 但未选择预设")
                return False, "当前未选择预设"
            
            if name not in self.groups_manager.prompt_groups:
                logger.warning(f"尝试更新不存在的组合 '{name}'")
                return False, f"组合 '{name}' 不存在"
            
            all_prompts = self.get_current_prompts()
            
            if self.groups_manager.update_prompt_group(name, indices, self.current_preset_name, all_prompts):
                logger.info(f"已更新预设 '{self.current_preset_name}' 的提示词组合: '{name}'")
                return True, f"已更新提示词组合: {name}"
            else:
                return False, f"更新组合 '{name}' 失败 (索引无效或保存错误)"
        except Exception as e:
            logger.error(f"更新组合 '{name}' 时发生错误: {e}", exc_info=True)
            return False, f"更新组合 '{name}' 时发生内部错误"
    
    def delete_prompt_group(self, name: str) -> Tuple[bool, str]:
        """
        删除提示词组合
        
        Args:
            name: 组合名称
            
        Returns:
            (成功标志, 消息)
        """
        try:
            if not self.current_preset_name:
                logger.warning(f"尝试删除组合 '{name}' 但未选择预设")
                return False, "当前未选择预设"
            
            if name not in self.groups_manager.prompt_groups:
                logger.warning(f"尝试删除不存在的组合 '{name}'")
                return False, f"组合 '{name}' 不存在"
            
            if self.groups_manager.delete_prompt_group(name, self.current_preset_name):
                logger.info(f"已删除预设 '{self.current_preset_name}' 的提示词组合: '{name}'")
                return True, f"已删除提示词组合: {name}"
            else:
                return False, f"删除组合 '{name}' 失败 (保存错误)"
        except Exception as e:
            logger.error(f"删除组合 '{name}' 时发生错误: {e}", exc_info=True)
            return False, f"删除组合 '{name}' 时发生内部错误"
    
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
                modified_system = f"{current_prefix}\n\n{modified_system}"
            else:
                modified_system = current_prefix
        
        # 添加激活的提示词到用户提示词前
        if active_prompts:
            active_content = ""
            for prompt in active_prompts:
                active_content += f"\n\n{prompt.get('content', '')}"
            
            modified_user = f"{active_content}\n\n{modified_user}"
        
        if active_prompts or current_prefix:
            logger.debug(f"处理LLM请求: 添加了前缀 '{bool(current_prefix)}' 和 {len(active_prompts)} 个激活提示词到预设 '{self.current_preset_name}'")
        return modified_system, modified_user
    
    def terminate(self):
        """停用控制器，清理资源"""
        self.prompts_manager.clear_active_prompts()