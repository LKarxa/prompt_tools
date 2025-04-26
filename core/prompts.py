"""
提示词管理模块
"""
import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from astrbot.api import logger
import traceback # 添加 traceback 以便详细记录错误

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
        self.activation_state_filename = "prompt_activation_state.json"  # 保存激活状态的文件名
    
    def ensure_directory_exists(self, directory: Path) -> None:
        """确保目录存在，如果不存在则创建"""
        if not directory.exists():
            directory.mkdir(parents=True)
            logger.info(f"创建目录: {directory}")
    
    def get_activation_state_path(self, preset_name: str) -> Path:
        """
        获取指定预设的激活状态文件路径
        
        Args:
            preset_name: 预设名称
            
        Returns:
            激活状态文件的路径
        """
        preset_folder = self.output_folder / preset_name
        return preset_folder / self.activation_state_filename
    
    def save_activation_state(self, preset_name: str, preset_prompts: List[Dict[str, Any]]) -> bool:
        """
        保存提示词激活状态到预设文件夹中的JSON文件
        
        Args:
            preset_name: 预设名称
            preset_prompts: 预设中的所有提示
            
        Returns:
            是否保存成功
        """
        try:
            if not preset_name:
                logger.warning("未指定预设名称，无法保存激活状态")
                return False
                
            preset_folder = self.output_folder / preset_name
            self.ensure_directory_exists(preset_folder)
            
            activation_state_path = self.get_activation_state_path(preset_name)
            
            # 创建活跃状态的映射
            active_prompts_names = {prompt.get('name', ''): prompt for prompt in self.active_prompts}
            
            # 为每个提示词创建激活状态对象
            activation_data = []
            for prompt in preset_prompts:
                name = prompt.get('name', '')
                if not name:
                    continue
                    
                # 检查是否激活
                is_active = name in active_prompts_names
                
                activation_data.append({
                    "name": name,
                    "active": is_active
                })
            
            # 将激活状态保存为JSON
            with open(activation_state_path, 'w', encoding='utf-8') as f:
                json.dump(activation_data, f, ensure_ascii=False, indent=4)
            
            logger.info(f"已保存提示词激活状态至: {activation_state_path}")
            return True
            
        except Exception as e:
            logger.error(f"保存提示词激活状态时出错: {str(e)}", exc_info=True)
            return False
    
    def load_activation_state(self, preset_name: str, preset_prompts: List[Dict[str, Any]]) -> bool:
        """
        从预设文件夹中的JSON文件加载提示词激活状态
        
        Args:
            preset_name: 预设名称
            preset_prompts: 预设中的所有提示
            
        Returns:
            是否成功加载了激活状态
        """
        try:
            if not preset_name:
                logger.warning("未指定预设名称，无法加载激活状态")
                return False
                
            activation_state_path = self.get_activation_state_path(preset_name)
            
            if not activation_state_path.exists():
                logger.info(f"未找到激活状态文件: {activation_state_path}，将保持当前状态")
                return False
            
            # 加载激活状态数据
            with open(activation_state_path, 'r', encoding='utf-8') as f:
                activation_data = json.load(f)
            
            # 清空当前激活的提示
            self.active_prompts = []
            
            # 创建名称到提示对象的映射
            prompts_by_name = {prompt.get('name', ''): prompt for prompt in preset_prompts if prompt.get('name')}
            
            # 根据加载的状态激活提示
            activated_count = 0
            for entry in activation_data:
                name = entry.get('name', '')
                is_active = entry.get('active', False)
                
                if name and is_active and name in prompts_by_name:
                    prompt = prompts_by_name[name]
                    self.active_prompts.append(prompt)
                    activated_count += 1
            
            logger.info(f"已从 {activation_state_path} 加载提示词激活状态，激活了 {activated_count} 个提示词")
            return True
            
        except Exception as e:
            logger.error(f"加载提示词激活状态时出错: {str(e)}", exc_info=True)
            return False
    
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
        try:
            if 0 <= index < len(self.active_prompts):
                removed_prompt = self.active_prompts.pop(index)
                logger.info(f"已从激活列表移除提示词 (原激活索引 {index}): '{removed_prompt.get('name', '未命名')}'")
                return removed_prompt
            else:
                logger.warning(f"尝试关闭无效的激活索引: {index}")
                return None
        except IndexError: # 应该被上面的范围检查捕获，但保留为安全措施
            logger.error(f"关闭激活索引 {index} 时发生 IndexError", exc_info=True)
            return None
    
    def deactivate_prompts_by_reference(self, prompts_to_deactivate: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        根据提示词对象引用关闭多个激活的提示词
        
        Args:
            prompts_to_deactivate: 要关闭的提示词对象列表
            
        Returns:
            实际被关闭的提示词列表
        """
        deactivated_list = []
        
        # 创建要停用的提示词集合，使用稳定的表示进行比较
        try:
            # 尝试使用排序后的项目元组作为可哈希表示
            prompts_set = set(tuple(sorted(p.items())) for p in prompts_to_deactivate)
        except TypeError:
            logger.error("无法创建用于停用查找的提示集，可能包含不可哈希类型。将回退到线性搜索。", exc_info=True)
            prompts_set = None

        # 从后往前遍历以避免移除项目时的索引问题
        indices_to_remove = []
        for i in range(len(self.active_prompts) - 1, -1, -1):
            active_prompt = self.active_prompts[i]
            should_remove = False
            
            if prompts_set is not None:
                try:
                    # 使用相同的稳定表示进行比较
                    active_prompt_tuple = tuple(sorted(active_prompt.items()))
                    if active_prompt_tuple in prompts_set:
                        should_remove = True
                except TypeError:
                    # 如果此特定项目哈希失败，则回退到线性搜索
                    if active_prompt in prompts_to_deactivate: # 直接对象比较
                        should_remove = True
            else:
                # 如果集合创建完全失败，则回退到线性搜索
                if active_prompt in prompts_to_deactivate: # 直接对象比较
                    should_remove = True
            
            if should_remove:
                indices_to_remove.append(i)

        if not indices_to_remove:
            logger.info("请求关闭的提示词均未在激活列表中找到")
            return []

        # 按索引移除提示词（已按降序排序）
        for index in indices_to_remove:
            try:
                removed = self.active_prompts.pop(index)
                deactivated_list.append(removed)
                logger.info(f"通过引用关闭提示词: '{removed.get('name', '未命名')}' (原激活索引 {index})")
            except IndexError:
                # 逻辑正确的情况下不应发生，但仍记录以防万一
                logger.error(f"尝试通过引用关闭时移除索引 {index} 出错", exc_info=True)

        # 按与激活列表相对的原始顺序返回
        deactivated_list.reverse()
        return deactivated_list
    
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
    
    def update_prompt(self, index: int, name: str, content: str, preset_name: str, preset_prompts: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        修改指定预设中指定索引的提示词
        
        Args:
            index: 提示词索引
            name: 新的提示词名称
            content: 新的提示词内容
            preset_name: 预设名称
            preset_prompts: 预设中的所有提示
            
        Returns:
            修改后的提示词信息，如果修改失败则返回None
        """
        if not preset_name:
            logger.warning("未指定预设名称，无法修改提示词")
            return None
        
        if index < 0 or index >= len(preset_prompts):
            logger.warning(f"无效的提示词索引: {index}")
            return None
        
        original_prompt = preset_prompts[index]
        original_name = original_prompt.get("name", "未命名")
        
        # 检查是否为用户创建的提示词，或者允许修改系统提示词
        if not original_prompt.get("user_created", False):
            logger.warning(f"提示词 '{original_name}' 不是由用户创建的，无法修改")
            return None
        
        # 检查提示词是否在激活列表中，如果在则需要更新激活列表中的数据
        was_active = False
        active_index = -1
        for i, active_prompt in enumerate(self.active_prompts):
            if active_prompt is original_prompt:  # 使用对象身份进行比较
                was_active = True
                active_index = i
                break
        
        # 更新提示词数据
        original_prompt["name"] = name
        original_prompt["content"] = content
        
        # 如果已激活，直接修改激活列表中的引用也会被更新
        if was_active:
            logger.info(f"提示词 '{original_name}' 已激活，同步更新激活列表中的数据")
        
        # 尝试保存到文件
        try:
            preset_folder = self.output_folder / preset_name
            
            # 尝试找到并删除原文件
            identifier = original_prompt.get("identifier", "")
            file_deleted = False
            
            if identifier:
                # 尝试使用不同的文件名模式
                possible_filenames = [
                    f"user_{identifier}.json",
                    f"{identifier}.json",
                    f"user_{original_name.replace(' ', '_')}.json",
                    f"{original_name.replace(' ', '_')}.json"
                ]
                
                for filename in possible_filenames:
                    file_path = preset_folder / filename
                    if file_path.exists():
                        try:
                            os.remove(file_path)
                            file_deleted = True
                            logger.info(f"已删除原文件: {file_path}")
                            break
                        except Exception as e:
                            logger.error(f"删除原文件 {file_path} 时出错: {str(e)}")
            
            # 保存新文件
            if self.save_prompt_to_file(original_prompt, preset_name):
                logger.info(f"已将提示词 '{original_name}' 修改为 '{name}'")
                
                # 保存激活状态
                self.save_activation_state(preset_name, preset_prompts)
                
                return original_prompt
            else:
                return None
                
        except Exception as e:
            logger.error(f"修改提示词 '{original_name}' 时出错: {str(e)}")
            return None