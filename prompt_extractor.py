import json
import os
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("prompt_extractor")

class PromptExtractor:
    """
    从JSON文件中提取提示信息的工具类
    """
    def __init__(self, presets_folder: str = "data/presets", output_folder: str = "prompts"):
        """
        初始化提示提取器
        
        Args:
            presets_folder: JSON文件所在的文件夹路径
            output_folder: 提取的提示信息保存的文件夹路径
        """
        self.presets_folder = Path(presets_folder)
        self.output_folder = Path(output_folder)
        self.prefix_identifier = "__PREFIX__"  # 前缀标识符
        
    def ensure_directory_exists(self, directory: Path) -> None:
        """确保目录存在，如果不存在则创建"""
        if not directory.exists():
            directory.mkdir(parents=True)
            logger.info(f"创建目录: {directory}")
    
    def get_sorted_identifiers(self, data: Dict) -> List[str]:
        """
        从prompt_order字段中获取排序后的identifier列表
        
        Args:
            data: JSON数据
            
        Returns:
            排序后的identifier列表
        """
        try:
            if "prompt_order" not in data:
                logger.warning("没有找到prompt_order字段，将按原始顺序处理")
                return []
            
            # 确保prompt_order是列表格式
            if not isinstance(data["prompt_order"], list):
                logger.warning("prompt_order不是列表格式，将按原始顺序处理")
                return []
            
            # 找到character_id最大的order
            max_character_id = -1
            max_order_item = None
            
            for order_item in data["prompt_order"]:
                if not isinstance(order_item, dict) or "character_id" not in order_item or "order" not in order_item:
                    continue
                    
                character_id = order_item.get("character_id", -1)
                if character_id > max_character_id:
                    max_character_id = character_id
                    max_order_item = order_item
            
            if max_order_item is None:
                logger.warning("没有找到有效的order项，将按原始顺序处理")
                return []
            
            # 从order列表中提取identifier，无论enabled是什么值
            identifiers = []
            for order_entry in max_order_item["order"]:
                if not isinstance(order_entry, dict) or "identifier" not in order_entry:
                    continue
                
                # 无论enabled是true还是false，都包含在排序中
                identifiers.append(order_entry["identifier"])
            
            return identifiers
            
        except Exception as e:
            logger.error(f"解析prompt_order时出错: {str(e)}")
            return []
    
    def extract_prompts_from_file(self, file_path: Path) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
        """
        从单个JSON文件中提取提示信息
        
        Args:
            file_path: JSON文件路径
            
        Returns:
            Tuple包含两个列表:
            1. 正常提示列表，每个条目包含name和content
            2. 前缀提示列表，包含在"personaDescription"之前的条目
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if "prompts" not in data:
                logger.warning(f"文件 {file_path} 中没有找到'prompts'字段")
                return [], []
                
            prompts = data["prompts"]
            
            # 首先过滤掉没有identifier的条目
            prompts = [prompt for prompt in prompts if prompt.get("identifier", "")]
            
            # 获取排序后的identifier列表
            sorted_identifiers = self.get_sorted_identifiers(data)
            
            # 创建identifier到prompt的映射
            prompt_by_identifier = {}
            for prompt in prompts:
                identifier = prompt.get("identifier", "")
                if identifier:
                    prompt_by_identifier[identifier] = prompt
            
            # 按照sorted_identifiers排序prompts
            sorted_prompts = []
            if sorted_identifiers:
                # 使用identifier顺序排序
                for identifier in sorted_identifiers:
                    if identifier in prompt_by_identifier:
                        sorted_prompts.append(prompt_by_identifier[identifier])
                
                # 添加没有在排序列表中但有identifier的提示
                for prompt in prompts:
                    identifier = prompt.get("identifier", "")
                    if identifier and identifier not in sorted_identifiers:
                        sorted_prompts.append(prompt)
            else:
                # 如果没有排序信息，使用原始顺序
                sorted_prompts = prompts
            
            # 找到"personaDescription"的索引位置
            persona_desc_index = -1
            for i, prompt in enumerate(sorted_prompts):
                if prompt.get("identifier") == "personaDescription":
                    persona_desc_index = i
                    break
            
            extracted_prompts = []
            prefix_prompts = []
            
            for i, prompt in enumerate(sorted_prompts):
                if "name" in prompt and "content" in prompt:
                    # 检查是否在"personaDescription"之前
                    if persona_desc_index != -1 and i < persona_desc_index:
                        # 给前缀条目添加标识符，内容为空的检查放在后面
                        prefix_prompt = {
                            "name": f"{self.prefix_identifier}{prompt['name']}",
                            "content": prompt["content"],
                            "is_prefix": True,
                            "identifier": prompt.get("identifier", "")
                        }
                        # 仅当内容不为空时添加
                        if prefix_prompt["content"].strip():
                            prefix_prompts.append(prefix_prompt)
                            logger.info(f"将提示 '{prompt['name']}' 标记为前缀")
                    else:
                        # 正常的提示条目，仅当内容不为空时添加
                        if prompt["content"].strip():
                            extracted_prompts.append({
                                "name": prompt["name"],
                                "content": prompt["content"],
                                "is_prefix": False,
                                "identifier": prompt.get("identifier", "")
                            })
                else:
                    logger.warning(f"提示中缺少'name'或'content'字段: {prompt}")
            
            return extracted_prompts, prefix_prompts
            
        except Exception as e:
            logger.error(f"处理文件 {file_path} 时出错: {str(e)}")
            return [], []
    
    def save_prompt_to_file(self, prompt: Dict[str, Any], preset_name: str) -> None:
        """
        将提示信息保存到JSON文件
        
        Args:
            prompt: 包含name和content的提示信息
            preset_name: 预设名称，用于创建子文件夹
        """
        preset_folder = self.output_folder / preset_name
        self.ensure_directory_exists(preset_folder)
        
        # 创建安全的文件名（替换不安全字符）
        name = prompt.get("name", "未命名")
        safe_name = "".join(c if c.isalnum() or c in [' ', '_', '-'] else '_' for c in name)
        safe_name = safe_name.strip().replace(' ', '_')
        
        file_path = preset_folder / f"{safe_name}.json"
        
        try:
            # 将提示保存为JSON格式
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(prompt, f, ensure_ascii=False, indent=4)
            logger.info(f"保存提示到JSON文件: {file_path}")
        except Exception as e:
            logger.error(f"保存提示到文件 {file_path} 时出错: {str(e)}")
    
    def save_prompt_prefix(self, prefix_prompts: List[Dict[str, Any]], preset_name: str) -> None:
        """
        将前缀提示保存到特殊的前缀文件中
        
        Args:
            prefix_prompts: 前缀提示列表
            preset_name: 预设名称
        """
        if not prefix_prompts:
            return
        
        preset_folder = self.output_folder / preset_name
        self.ensure_directory_exists(preset_folder)
        
        file_path = preset_folder / "prompt_prefix.json"
        
        # 合并所有前缀提示的内容
        combined_content = ""
        for prompt in prefix_prompts:
            content = prompt.get("content", "").strip()
            name = prompt.get("name", "").replace(self.prefix_identifier, "")
            identifier = prompt.get("identifier", "")
            if content:
                combined_content += f"<!-- {name} (identifier: {identifier}) -->\n{content}\n\n"
        
        prefix_data = {
            "name": "System Prompt Prefix",
            "content": combined_content.strip(),
            "is_prefix": True
        }
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(prefix_data, f, ensure_ascii=False, indent=4)
            logger.info(f"保存前缀提示到文件: {file_path}")
        except Exception as e:
            logger.error(f"保存前缀提示到文件 {file_path} 时出错: {str(e)}")
    
    def extract_all_prompts(self) -> Dict[str, List[Dict[str, str]]]:
        """
        提取所有JSON文件中的提示信息并保存
        
        Returns:
            按预设分组的提取结果
        """
        self.ensure_directory_exists(self.output_folder)
        
        if not self.presets_folder.exists():
            logger.error(f"预设文件夹不存在: {self.presets_folder}")
            return {}
            
        result = {}
        
        # 查找所有JSON文件
        json_files = list(self.presets_folder.glob("*.json"))
        
        if not json_files:
            logger.warning(f"在 {self.presets_folder} 中没有找到JSON文件")
            return {}
            
        for json_file in json_files:
            preset_name = json_file.stem  # 获取文件名（不含扩展名）
            prompts, prefix_prompts = self.extract_prompts_from_file(json_file)
            
            if prompts:
                result[preset_name] = prompts
                # 保存提取的提示到文件
                for prompt in prompts:
                    self.save_prompt_to_file(prompt, preset_name)
                
                # 保存前缀提示
                if prefix_prompts:
                    self.save_prompt_prefix(prefix_prompts, preset_name)
            else:
                logger.info(f"文件 {json_file} 中没有找到有效的提示")
        
        return result

# 示例使用方法
if __name__ == "__main__":
    extractor = PromptExtractor()
    extracted_prompts = extractor.extract_all_prompts()
    print(f"提取的提示总数: {sum(len(prompts) for prompts in extracted_prompts.values())}")