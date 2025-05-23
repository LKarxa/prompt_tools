# Prompt Tools - 提示词管理与激活工具

这是一个用于管理和激活提示词的插件，帮助用户更有效地组织、管理和应用提示词到AI对话中。

可以搭配我的另外一个插件使用[https://github.com/LKarxa/astrbot_plugin_regex_filter](https://github.com/LKarxa/astrbot_plugin_regex_filter)

## 功能特点

- 📁 **预设管理**：支持多个提示词预设的加载和切换
- 🔄 **动态激活**：可以在对话中动态激活/关闭特定提示词或提示词组合
- 🔒 **前缀提示**：支持为每个预设设置自动添加的前缀提示
- 🔍 **查看内容**：可以随时查看提示词、前缀或组合的详细内容
- 🔄 **实时刷新**：支持重新提取和加载提示词库
- ✏️ **自定义提示词**：允许用户创建、添加、修改和删除自己的提示词
- 🔗 **提示词组合**：支持将多个提示词组合在一起，一键激活
- 💾 **激活状态保存**：自动记住提示词的激活状态，重启后自动恢复

## 命令列表

所有命令都以 `/prompt` 开头。

### 预设管理
- `presets` - 列出所有可用的提示词预设
- `use <索引>` - 切换到指定索引的预设
- `create_preset <名称>` - 创建一个新的空白预设
- `refresh` - 重新提取和加载所有提示词

### 提示词列表与激活
- `list` - 列出当前预设中的所有提示词（并标记已激活）
- `activate <索引|@组名>` - 激活指定索引的提示词或指定名称的组合
- `deactivate <索引|all>` - 关闭指定索引的激活提示词或所有激活的提示词

### 查看详情
- `view prompt <索引>` - 查看指定索引的提示词内容和状态
- `view prefix` - 查看当前预设的前缀提示内容
- `view group <组名>` - 查看指定名称的提示词组合详情

### 自定义提示词
- `add <名称> [内容]` - 添加自定义提示词（如不提供内容，将在下一条消息中获取）
- `update <索引> <名称> [内容]` - 修改指定索引的提示词（如不提供内容，将在下一条消息中获取）
- `delete <索引>` - 删除指定索引的用户自定义提示词（仅限用户创建的）

### 提示词组合管理
- `group list` - 列出当前预设的所有提示词组合
- `group create <组名> <索引列表>` - 创建提示词组合 (索引以逗号分隔, 例如: 0,1,5)
- `group update <组名> <索引列表>` - 更新提示词组合 (索引以逗号分隔)
- `group delete <组名>` - 删除提示词组合

## 使用方法

1.  **准备预设文件**：
    *   在 `data/plugin_data/prompt_tools/presets` 目录下上传酒馆预设JSON文件

2.  **加载/刷新预设**：
    *   插件启动时会自动加载预设
    *   使用 `/prompt refresh` 手动重新加载或更新预设
    *   使用 `/prompt presets` 查看所有可用的预设
    *   使用 `/prompt use <索引>` 选择要使用的预设
    *   或使用 `/prompt create_preset <名称>` 创建一个全新的预设

3.  **查看与激活提示词**：
    *   使用 `/prompt list` 查看当前预设中的所有提示词及其激活状态
    *   使用 `/prompt view prompt <索引>` 查看具体提示词内容
    *   使用 `/prompt activate <索引>` 激活需要的提示词
    *   激活的提示词将自动添加到与AI的对话中

4.  **管理激活的提示词**：
    *   使用 `/prompt list` 查看当前激活的所有提示词（标记为 ✅）
    *   使用 `/prompt deactivate <索引>` 关闭不需要的提示词
    *   使用 `/prompt deactivate all` 清空所有激活的提示词

5.  **创建自定义提示词**：
    *   使用 `/prompt add <名称>` 添加新的提示词
    *   在下一条消息中输入提示词的具体内容
    *   或直接使用 `/prompt add <名称> <内容>` 一次性添加

6.  **修改提示词**：
    *   使用 `/prompt update <索引> <新名称>` 修改提示词
    *   在下一条消息中输入提示词的新内容
    *   或直接使用 `/prompt update <索引> <新名称> <新内容>` 一次性修改
    *   注意：只能修改用户自己创建的提示词

7.  **使用提示词组合**：
    *   使用 `/prompt group create <组名> 0,1,3` 创建包含多个提示词的组合
    *   使用 `/prompt group list` 查看所有可用的组合
    *   使用 `/prompt view group <组名>` 查看组合详情
    *   使用 `/prompt activate @<组名>` 一键激活组合中的所有提示词

## 提示词组合使用示例

提示词组合功能可以让你将多个经常一起使用的提示词组合起来，方便快速激活：

1.  **创建组合**：
    ```
    /prompt group create 角色扮演 0,1,2
    ```
    这将创建一个名为"角色扮演"的组合，包含索引为0、1、2的提示词

2.  **查看所有组合**：
    ```
    /prompt group list
    ```
    列出当前预设中的所有提示词组合及其包含的提示词

3.  **一键激活**：
    ```
    /prompt activate @角色扮演
    ```
    这将一次性激活"角色扮演"组合中的所有提示词

4.  **查看组合详情**：
    ```
    /prompt view group 角色扮演
    ```
    显示组合中包含的所有提示词及其激活状态

5.  **更新组合**：
    ```
    /prompt group update 角色扮演 0,1,2,5
    ```
    修改组合中包含的提示词列表

## 自动保存激活状态

插件现在会自动保存每个预设中提示词的激活状态：

1. **无需手动保存**：激活或关闭提示词后，状态会自动保存
2. **重启后恢复**：插件重启后，会自动加载上次使用时的激活状态
3. **预设切换记忆**：每个预设都有独立的激活状态记忆，切换预设后会加载该预设特定的激活状态

## 注意事项

-   前缀提示会自动应用于所有对话，无需手动激活，使用 `/prompt view prefix` 查看
-   切换预设 (`/prompt use`) 时会清空当前激活的提示词，并加载目标预设的激活状态
-   刷新提示词库 (`/prompt refresh`) 也会清空当前激活的提示词
-   用户创建的自定义提示词会保存在预设对应的目录中
-   只能修改或删除用户自己创建的提示词，无法修改或删除从JSON文件中提取的系统提示词
-   提示词组合配置会保存在预设特定的配置文件中

## 路径说明

-   原始预设文件目录：`data/plugin_data/prompt_tools/presets/*.json`
-   提取后的提示词目录：`data/plugin_data/prompt_tools/presets/<预设名>/*.json`
-   提示词激活状态文件：`data/plugin_data/prompt_tools/presets/<预设名>/prompt_activation_state.json`
-   提示词组合配置文件：`data/plugin_data/prompt_tools/presets/<预设名>_groups.json`
