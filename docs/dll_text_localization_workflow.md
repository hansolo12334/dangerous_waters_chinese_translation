# Dangerous Waters 动态 DLL 文本汉化完整工作流

## 1. 适用范围

本流程用于汉化类似 `translations\poc_exit_zh.json` 的动态 UI 文本，即游戏通过语言资源 DLL 读取并由 FUI 控件绘制的文字。

| 资源 | 内容范围 | 当前提取文本数 |
| --- | --- | ---: |
| `AppTextE.dll` | 通用菜单、按钮、对话框、设置与系统提示 | 2354 |
| `Interfaces\688I\textE.dll` | 688I 操作台界面文本 | 620 |
| `Interfaces\AkulaII\textE.dll` | Akula II 操作台界面文本 | 728 |
| `Interfaces\FFG\TextE.dll` | FFG 操作台界面文本 | 740 |
| `Interfaces\Kilo\TextE.dll` | Kilo 英文操作台文本 | 946 |
| `Interfaces\Kilo\TextCE.dll` | Kilo 特定文本分支 | 946 |
| `Interfaces\MH60\textE.dll` | MH-60 操作台界面文本 | 397 |
| `Interfaces\P3\textE.dll` | P-3 操作台界面文本 | 377 |
| `Interfaces\ssn21\TextE.dll` | SSN-21 操作台界面文本 | 619 |

此流程不处理：

- 主菜单等烘焙在 `.bmp` 中的按钮文字；
- `Scenario\*.ms/.mp/.mc` 中的任务标题与简报文本；
- 仍未确认走 FUI 字体路径的其他特殊文本渲染控件。

任务文本流程见 `docs\mission_localization_workflow.md`，图片汉化候选见 `docs\static_graphics_inventory.md`。

## 2. 为什么需要 DLL 文本补丁与字体补丁同时存在

动态文本链路已通过逆向和实机测试确认：

1. 游戏根据语言加载 `AppTextE.dll` 或平台 `TextE.dll` 中的 `RT_STRING` 资源。
2. 通用文本读取函数通过 `LoadStringA` 返回字节串。
3. 原始 FUI 位图字体函数按每个字节索引 `0..255` 字形。
4. 中文 UTF-8 文本在未打补丁时会被拆为多个西文乱码字形。

因此，仅生成中文 DLL 并不能显示中文。可运行包必须包含：

| 文件 | 作用 |
| --- | --- |
| `dinput8.dll` | UTF-8 FUI 注入代理，解码中文并正确计算字宽/绘制字形 |
| `Graphics\shared.ndx/.grp` | 包含新增 `dw_zh_*` 中文字体页 |
| `AppTextE.dll` | 回填后的通用 UI 中文文本 |
| `Interfaces\<平台>\TextE.dll` 或 `TextCE.dll` | 可选的平台界面中文文本 |

当前注入方案已验证 `AppTextE.dll` 中退出确认框中文可以显示，并且不会占用正常 ASCII 字形。

## 3. 环境与目录约定

命令均在仓库根目录运行：

```powershell
Set-Location 'D:\project\dangerous waters\dangerous_waters_chinese_translation'
$python = 'D:\Miniconda\envs\mujoco\python.exe'
$game = 'D:\project\dangerous waters\Dangerous Waters'
```

推荐的译文组织结构：

```text
translations\
├─ export\                         # 从原 DLL 导出的 TSV 参考表
├─ poc_exit_zh.json                # 已验证的通用动态弹窗样例
├─ poc_apptext_zh.json             # 已验证的少量通用 UI 样例
└─ dll\
   ├─ AppTextE_zh.json             # 后续维护的通用 UI 正式译文
   ├─ FFG_TextE_zh.json            # FFG 平台译文
   ├─ Kilo_TextE_zh.json           # Kilo 平台译文
   └─ ...
```

建议将 `poc_*.json` 保留为回归测试样例；正式大规模翻译另建 `translations\dll\` 下的 JSON，避免试验文案混入成品。

批量制作时，推荐始终从备份的干净 DLL 回填，而不是从游戏目录里已经装过测试译文的 DLL 继续累积修改。例如将 `$backup\AppTextE.dll` 作为 `--apptext-source`。

## 4. 开始前备份

至少备份将要覆盖的通用资源、字体资源与注入 DLL：

```powershell
$backup = Join-Path $game 'ChinesePatchBackup'
New-Item -ItemType Directory -Force -Path $backup, "$backup\Graphics", "$backup\Interfaces" | Out-Null
Copy-Item "$game\AppTextE.dll" "$backup\AppTextE.dll" -Force
Copy-Item "$game\Graphics\shared.ndx" "$backup\Graphics\shared.ndx" -Force
Copy-Item "$game\Graphics\shared.grp" "$backup\Graphics\shared.grp" -Force
if (Test-Path "$game\dinput8.dll") { Copy-Item "$game\dinput8.dll" "$backup\dinput8.dll" -Force }
```

若将处理某个平台，例如 FFG：

```powershell
New-Item -ItemType Directory -Force -Path "$backup\Interfaces\FFG" | Out-Null
Copy-Item "$game\Interfaces\FFG\TextE.dll" "$backup\Interfaces\FFG\TextE.dll" -Force
```

注意：早期代理槽位字库测试曾覆盖正常 ASCII 字形。构建字体包时应使用干净的 `Graphics\back\shared.ndx/.grp`；现有构建脚本若发现该备份会自动优先使用。

## 5. DLL 与运行界面的对应关系

### 通用界面：`AppTextE.dll`

`AppTextE.dll` 适合作为首轮工作对象，因为容易触发和复核：

| 已确认资源 ID | 原始位置 / 用途 | 已验证示例 |
| ---: | --- | --- |
| `42` | 常见取消按钮 | `取消` |
| `43` | 常见是/确认按钮 | `是` |
| `47` | 关闭按钮 | `关闭` |
| `355` | 选项相关文本 | `选项` |
| `1058` | 选项相关文本 | `选项` |
| `1258` | 主菜单退出确认框标题 | `中文动态文本测试` |
| `1259` | 主菜单退出确认框正文 | `这段文字来自 AppTextE.dll，是否退出游戏？` |

触发 `1258` / `1259` 的方式是主菜单点击 `EXIT`，因此它们适合作为每次字体或运行包重建后的冒烟测试。

### 平台界面：`Interfaces\<平台>\TextE.dll`

进入具体舰艇/飞机操作界面后的仪表、操作按钮、状态文字通常来自对应平台 DLL。例如测试 FFG 内容时，应进入 FFG 任务或相应平台界面，并覆盖：

```text
Interfaces\FFG\TextE.dll
```

Kilo 另存在 `TextCE.dll`。根据已逆向的 `controllers.ini` 逻辑，这不是完整通用中文包，而是 Kilo 的独立文本分支；应单独导出、翻译和测试。

## 6. 第一步：导出所有 DLL 文本

一次导出所有已知通用与平台 DLL：

```powershell
& $python scripts\export_all_text.py --game-dir $game
```

默认输出到 `translations\export\`，每个文件为带 BOM 的 UTF-8 TSV：

```text
id    source    translation
1258  S.C.S. - Dangerous Waters
1259  Are you sure you want to exit the game?
```

仅导出单个 DLL：

```powershell
& $python scripts\dw_string_tool.py extract `
  "$game\AppTextE.dll" `
  "translations\export\AppTextE.tsv"
```

或导出平台 DLL：

```powershell
& $python scripts\dw_string_tool.py extract `
  "$game\Interfaces\FFG\TextE.dll" `
  "translations\export\FFG_TextE.tsv"
```

### 如何从界面反查字符串 ID

首选方法是搜索导出的 TSV：

```powershell
Select-String -LiteralPath 'translations\export\AppTextE.tsv' -Pattern 'Options|Cancel|Exit'
Select-String -LiteralPath 'translations\export\FFG_TextE.tsv' -Pattern 'Radar|Sonar|Fire'
```

若一个英文文本在多个 DLL 中均存在：

1. 先确认显示位置是在通用菜单还是具体平台操作台。
2. 只在一个候选 DLL 中做 ASCII 探针替换，例如将目标字符串临时改为 `FFG TEST`。
3. 进入对应页面确认实际读取的是哪一份 DLL。
4. 确认来源后再写入正式中文 JSON。

## 7. 第二步：建立 JSON 译文文件

`dw_string_tool.py patch` 读取的译文文件是 UTF-8 JSON，对象键为十进制字符串 ID，值为中文译文：

```json
{
  "42": "取消",
  "43": "是",
  "1258": "中文动态文本测试",
  "1259": "这段文字来自 AppTextE.dll，是否退出游戏？"
}
```

### 命名约定

| 对应源文件 | 建议译文文件 |
| --- | --- |
| `AppTextE.dll` | `translations\dll\AppTextE_zh.json` |
| `Interfaces\FFG\TextE.dll` | `translations\dll\FFG_TextE_zh.json` |
| `Interfaces\Kilo\TextE.dll` | `translations\dll\Kilo_TextE_zh.json` |
| `Interfaces\Kilo\TextCE.dll` | `translations\dll\Kilo_TextCE_zh.json` |

JSON 文件可以只包含当前要测试的一小批 ID；未列出的字符串保持原始英文。推荐从少量可触发文本开始，而不是立即填满 2354 条通用文本。

## 8. 翻译规则与安全限制

### 必须保留格式符

部分字符串被游戏当作格式模板，可能含有：

```text
%s  %d  %02d  %.1f  %%
```

译文中必须保留原来的格式符及顺序，例如：

```json
{
  "100": "速度：%d 节",
  "101": "%s 已损坏"
}
```

`dw_string_tool.py` 会自动比较原文与译文中的格式符；若更改、漏掉或调换顺序，将拒绝生成 DLL：

```text
string 100 changes format tokens: ['%d'] -> []
```

这属于保护机制，不应绕过。应修改译文以保留占位符。

### 控制文本长度

当前回填工具在原 `RT_STRING` 数据块的现有空间内修改字符串，不重建 PE 资源表。若同一个资源块内中文总长度超过原始容量，会报错：

```text
resource block N grows from ... to ... bytes; shorten translations or rebuild resources
```

处理方法：

1. 优先精简该批译文，避免冗长表达。
2. 把长提示拆到后续批次并观察同块容量。
3. 若成品翻译确实必须更长，再单独实现资源区重建工具；当前流程不隐式扩大 DLL。

### 文风与版面建议

- 按钮文字短而明确：`取消`、`确定`、`关闭`、`选项`。
- 弹窗与提示优先用一句简洁中文，减少旧界面换行压力。
- 技术缩写、平台名和单位可保留英文，如 `FFG`、`TMA`、`dB`。
- 对会频繁显示的告警/状态文本建立统一术语表，避免同词多译。

## 9. 第三步：生成单个已翻译 DLL

仅验证 DLL 回填正确、尚不测试中文显示时，可生成单个输出文件：

```powershell
New-Item -ItemType Directory -Force -Path 'build\dll_text\AppText' | Out-Null
& $python scripts\dw_string_tool.py patch `
  "$game\AppTextE.dll" `
  "translations\poc_exit_zh.json" `
  "build\dll_text\AppText\AppTextE.dll"
```

平台 DLL 示例：

```powershell
New-Item -ItemType Directory -Force -Path 'build\dll_text\Interfaces\FFG' | Out-Null
& $python scripts\dw_string_tool.py patch `
  "$game\Interfaces\FFG\TextE.dll" `
  "translations\dll\FFG_TextE_zh.json" `
  "build\dll_text\Interfaces\FFG\TextE.dll"
```

重要：此步骤只产生含中文资源的 DLL。若游戏中尚未安装 UTF-8 FUI 注入包，界面仍会显示乱码。

## 10. 第四步：构建通用 `AppTextE.dll` 可运行包

若只翻译 `AppTextE.dll`，可直接使用 UTF-8 运行包构建器。测试已有两个 JSON 的组合：

```powershell
& $python scripts\build_utf8_fui_hook_poc.py --game-dir $game `
  --output-dir 'build\dll_text_apptext\runtime' `
  --apptext-source "$backup\AppTextE.dll" `
  --translations `
  translations\poc_exit_zh.json `
  translations\poc_apptext_zh.json
```

生成结果：

```text
build\dll_text_apptext\runtime\
├─ dinput8.dll
├─ AppTextE.dll
├─ glyph_map.json
└─ Graphics\
   ├─ shared.ndx
   └─ shared.grp
```

正式通用 UI 译文建立后，可替换为：

```powershell
& $python scripts\build_utf8_fui_hook_poc.py --game-dir $game `
  --output-dir 'build\dll_text_apptext\runtime' `
  --apptext-source "$backup\AppTextE.dll" `
  --translations translations\dll\AppTextE_zh.json
```

`--translations` 中列出的 JSON 会同时用于：

1. 回填生成新的 `AppTextE.dll`；
2. 收集所需中文字符并生成字体页；
3. 编译与该字体映射一致的 `dinput8.dll`。

## 11. 第五步：构建包含平台 `TextE.dll` 的运行包

平台 DLL 尚不由 `build_utf8_fui_hook_poc.py` 自动回填，但可以完整地组合到同一个测试包中。

以下以 FFG 为例。

### 11.1 生成通用运行环境并纳入平台字形

```powershell
$pack = 'build\dll_text_ffg\runtime'
& $python scripts\build_utf8_fui_hook_poc.py --game-dir $game `
  --output-dir $pack `
  --apptext-source "$backup\AppTextE.dll" `
  --translations `
  translations\poc_exit_zh.json `
  translations\poc_apptext_zh.json `
  --font-text translations\dll\FFG_TextE_zh.json
```

`--font-text` 仅把平台 JSON 中的汉字加入中文字库和代理映射，不会误将平台 ID 回填进 `AppTextE.dll`。

### 11.2 生成平台 DLL 到同一运行包

```powershell
New-Item -ItemType Directory -Force -Path "$pack\Interfaces\FFG" | Out-Null
& $python scripts\dw_string_tool.py patch `
  "$game\Interfaces\FFG\TextE.dll" `
  "translations\dll\FFG_TextE_zh.json" `
  "$pack\Interfaces\FFG\TextE.dll"
```

同理，多个平台可以继续追加：

```powershell
--font-text `
  translations\dll\FFG_TextE_zh.json `
  translations\dll\P3_TextE_zh.json
```

随后分别用 `dw_string_tool.py patch` 生成对应目录下的 DLL。

### 11.3 为什么不能遗漏 `--font-text`

如果平台 DLL 已写入新的中文字，但字体包没有包含这些字符：

- 已存在于其他译文中的汉字仍可显示；
- 新出现的汉字会显示为 `?`。

每次新增或修改任何 DLL 中文译文后，都应重新构建 `dinput8.dll` 与 `Graphics\shared.ndx/.grp`。

## 12. 第六步：安装可运行包

### 通用 `AppTextE.dll` 包

```powershell
$pack = 'D:\project\dangerous waters\dangerous_waters_chinese_translation\build\dll_text_apptext\runtime'
Copy-Item "$pack\dinput8.dll" "$game\dinput8.dll" -Force
Copy-Item "$pack\AppTextE.dll" "$game\AppTextE.dll" -Force
Copy-Item "$pack\Graphics\shared.ndx" "$game\Graphics\shared.ndx" -Force
Copy-Item "$pack\Graphics\shared.grp" "$game\Graphics\shared.grp" -Force
```

### 包含平台 DLL 的包

```powershell
$pack = 'D:\project\dangerous waters\dangerous_waters_chinese_translation\build\dll_text_ffg\runtime'
Copy-Item "$pack\dinput8.dll" "$game\dinput8.dll" -Force
Copy-Item "$pack\AppTextE.dll" "$game\AppTextE.dll" -Force
Copy-Item "$pack\Graphics\shared.ndx" "$game\Graphics\shared.ndx" -Force
Copy-Item "$pack\Graphics\shared.grp" "$game\Graphics\shared.grp" -Force
Copy-Item "$pack\Interfaces\FFG\TextE.dll" "$game\Interfaces\FFG\TextE.dll" -Force
```

安装后启动游戏，从与本批译文对应的页面进入测试。

## 13. 第七步：实机验收流程

### 13.1 每包必做冒烟测试

先在主菜单点击 `EXIT`，确认：

- 标题 `中文动态文本测试` 显示正常；
- 正文 `这段文字来自 AppTextE.dll，是否退出游戏？` 显示正常；
- `是` / `取消` 按钮或相关动态文字正常；
- 英文 `AppTextE.dll`、数字和标点没有被替换成中文。

若此处失败，不应继续检查平台页面；先排除运行包或字库安装错误。

### 13.2 通用 UI 文本验收

对 `AppTextE.dll` 中每批新增 ID 建立“触发位置”记录：

| ID | 中文译文 | 可触发位置 | 结果 |
| ---: | --- | --- | --- |
| `1259` | `这段文字来自 AppTextE.dll，是否退出游戏？` | 主菜单 `EXIT` | 已验证 |
| `355` | `选项` | 待确认具体动态页面 | 待测 |

每一批建议控制在一个可完整走查的功能页面，例如设置页、弹窗或任务选择页周边控件。

### 13.3 平台文本验收

平台 DLL 必须在相应平台中测试。例如 `Interfaces\FFG\TextE.dll`：

1. 载入可操控 FFG 的任务。
2. 进入含译文的对应工作站页面。
3. 检查按钮、状态条、提示信息和动态数值周围单位。
4. 特别检查 `%s`、`%d` 等格式化文本是否能正常显示运行数据。

### 13.4 回归检查

- 未翻译文本是否仍保持英文正常显示。
- ASCII 字母、数字、单位和文件名是否不受中文字库影响。
- 切换不同界面或平台后是否闪退。
- 页面中是否存在文字被截断、换行错位、控件宽度不足。

## 14. 批量翻译推进方式

### 推荐阶段

| 阶段 | 资源 | 目标 |
| --- | --- | --- |
| A | `AppTextE.dll` 高频通用 UI | 先覆盖菜单、按钮、弹窗与设置界面 |
| B | 当前重点平台 `TextE.dll` | 一个平台一批，配合可进入的任务测试 |
| C | 其余平台 DLL | 统一术语后逐个平台推进 |
| D | 任务文本与 DLL 文本联调 | 同时测试 Missions、简报和操作界面 |

### 每批标准循环

1. 在 TSV 中筛选一个页面或功能域的英文字符串。
2. 在对应 `_zh.json` 中增加少量可触发 ID。
3. 运行 `dw_string_tool.py patch`，确认格式符与容量检查通过。
4. 重建带完整本批字形的 UTF-8 运行包。
5. 安装并实机走查该页面。
6. 记录 ID、触发位置、译文和问题，再进入下一批。

### 术语表建议

通用与平台文本会共享大量术语，建议维护一致译法：

| 英文 | 建议译法 |
| --- | --- |
| `Options` | `选项` |
| `Cancel` | `取消` |
| `Close` | `关闭` |
| `Mission` | `任务` |
| `Tasking` | `任务指令` / 简报语境按需调整 |
| `Contact` | `接触目标` 或 `目标`，需按声纳/雷达语境统一 |
| `Bearing` | `方位` |
| `Range` | `距离` |

## 15. 常见问题与排障

### 仅替换 DLL，中文变乱码

原因：没有安装 `dinput8.dll` 与含中文页的 `Graphics\shared.ndx/.grp`。

处理：使用 `build_utf8_fui_hook_poc.py` 生成完整运行包，并同时覆盖四个核心文件。

### 某些汉字显示为问号

原因：中文 DLL 与字体映射不同步，常见于修改 JSON 后只覆盖了 DLL。

处理：重新构建运行包，并覆盖新的 `dinput8.dll` 与 `Graphics\shared.ndx/.grp`。

### 生成 DLL 时格式符校验失败

原因：译文遗漏或改变了 `%s`、`%d` 等占位符。

处理：恢复原格式符和顺序；不要关闭校验。

### 生成 DLL 时提示资源块变大

原因：某个 RT_STRING 块内的新译文总长度超过原空间。

处理：精简同批译文或拆分调整文本；若无法精简，后续需实现资源表重建而非原位回填。

### 覆盖 `AppTextE.dll` 后主菜单按钮仍为英文

原因：主菜单按钮是 `Graphics\mainmenu.grp` 中的四态图片，而非动态 DLL 文字。

处理：使用主菜单图片包；不要用该画面判断 DLL 文本是否生效。

### 平台页面译文没有出现

检查：

1. 是否覆盖了正确平台目录下的 DLL。
2. 是否进入了使用该平台资源的任务/界面。
3. Kilo 当前测试文本是否实际来自 `TextE.dll` 或 `TextCE.dll`。
4. 用 ASCII 探针先确认字符串来源，再测试中文。

## 16. 恢复原版

恢复通用动态 UI：

```powershell
$backup = Join-Path $game 'ChinesePatchBackup'
Copy-Item "$backup\AppTextE.dll" "$game\AppTextE.dll" -Force
Copy-Item "$backup\Graphics\shared.ndx" "$game\Graphics\shared.ndx" -Force
Copy-Item "$backup\Graphics\shared.grp" "$game\Graphics\shared.grp" -Force
if (Test-Path "$backup\dinput8.dll") {
  Copy-Item "$backup\dinput8.dll" "$game\dinput8.dll" -Force
} else {
  Remove-Item "$game\dinput8.dll" -Force -ErrorAction SilentlyContinue
}
```

如已覆盖平台 DLL：

```powershell
Copy-Item "$backup\Interfaces\FFG\TextE.dll" "$game\Interfaces\FFG\TextE.dll" -Force
```

## 17. 当前可直接使用的回归样例

| 文件 | 用途 |
| --- | --- |
| `translations\poc_exit_zh.json` | 主菜单退出确认框与基础按钮的动态中文回归样例 |
| `translations\poc_apptext_zh.json` | 少量通用 UI 中文扩展示例 |
| `scripts\dw_string_tool.py` | DLL `RT_STRING` 导出与安全回填 |
| `scripts\export_all_text.py` | 导出通用与平台 DLL 文本 |
| `scripts\build_utf8_fui_hook_poc.py` | 生成 AppText 中文运行包并汇总额外字形 |

最稳妥的下一步是先建立 `translations\dll\AppTextE_zh.json`，以功能页面为单位从 `AppTextE.tsv` 中挑选一批可触发文本翻译和实机验证；确认通用控件稳定后，再开始一个具体平台的 `TextE.dll` 翻译。
