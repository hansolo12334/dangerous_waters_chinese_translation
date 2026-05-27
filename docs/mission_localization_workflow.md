# Dangerous Waters 任务文本汉化完整工作流

## 1. 目标与适用范围

本工作流用于汉化 `MISSIONS` 页面、任务简报与任务相关说明文本，覆盖以下场景资源：

| 文件类型 | 用途 | 当前数量 |
| --- | --- | ---: |
| `Scenario\*.ms` | 单人任务 / 平台任务 | 25 |
| `Scenario\*.mp` | 多人任务 | 7 |
| `Scenario\*.mc` | 战役关卡 | 11 |

目前已识别 43 个任务文件，共 784 个可提取文本块。已完成的首个样例是 `Scenario\SM08.ms` 中的 `African Bees Nest`，中文名为“非洲蜂巢”。

此流程不负责主菜单按钮图片、`AppTextE.dll` 通用 UI 文本或各平台操作台 `TextE.dll` 文本；它们属于并行的汉化资源线。

## 2. 技术前提

任务文件本身是带结构关键字的明文文本：

```text
DESCRIPTION
BEGINTEXT
Set Sea & Anchor Detail and get underway for open waters.
ENDTEXT
MISSIONTITLE
BEGINTEXT
African Bees Nest
ENDTEXT
```

任务正文可以回填 UTF-8 中文，但原版游戏的 FUI 字体渲染器按单字节绘制，直接放入中文会乱码。因此任务汉化包必须与 UTF-8 动态文字补丁一同安装：

- `dinput8.dll`：代理 DLL，钩住 FUI 字宽与绘字函数，解码 UTF-8 中文。
- `Graphics\shared.ndx/.grp`：保留原英文字库，追加 `dw_zh_*.bmp/.dim` 中文字体页。
- `Scenario\<任务文件>`：写入 UTF-8 中文后的任务文本文件。
- `AppTextE.dll`：当前测试包同时包含已验证的中文动态 UI 文本；任务本身不依赖其资源 ID。

中文字库页由翻译内容自动生成。每页可容纳 224 个新增字形，超过时脚本会继续生成 `dw_zh_01`、`dw_zh_02` 等页面。

## 3. 环境与目录约定

以下命令均在仓库根目录执行：

```powershell
Set-Location 'D:\project\dangerous waters\dangerous_waters_chinese_translation'
$python = 'D:\Miniconda\envs\mujoco\python.exe'
$game = 'D:\project\dangerous waters\Dangerous Waters'
```

推荐采用以下目录分工：

| 目录 | 内容 | 是否编辑 |
| --- | --- | --- |
| `$game\Scenario\` | 游戏当前使用的任务文件 | 仅安装测试包时覆盖 |
| `translations\scenario_export\` | 从原任务导出的英文参考 JSON | 不直接作为最终译文维护 |
| `translations\scenarios\*_zh.json` | 人工维护的中文译文 | 是 |
| `build\mission_zh_poc\runtime\` | 可复制到游戏目录的生成包 | 不直接编辑 |

## 4. 开始前的备份

首次安装任何任务汉化包前，备份以下文件：

```powershell
$backup = Join-Path $game 'ChinesePatchBackup'
New-Item -ItemType Directory -Force -Path $backup, "$backup\Graphics", "$backup\Scenario" | Out-Null
Copy-Item "$game\AppTextE.dll" "$backup\AppTextE.dll" -Force
Copy-Item "$game\Graphics\shared.ndx" "$backup\Graphics\shared.ndx" -Force
Copy-Item "$game\Graphics\shared.grp" "$backup\Graphics\shared.grp" -Force
Copy-Item "$game\Scenario\SM08.ms" "$backup\Scenario\SM08.ms" -Force
if (Test-Path "$game\dinput8.dll") { Copy-Item "$game\dinput8.dll" "$backup\dinput8.dll" -Force }
```

批量推进时，每新增一个将要覆盖的任务文件，也将其原文件复制到 `$backup\Scenario\`。

注意：早期“代理 ASCII 槽位”实验会污染 `Graphics\shared` 的正常英文字形。字体构建脚本在存在 `$game\Graphics\back\shared.ndx/.grp` 时会优先以该备份档案为干净源；不要删除它。

## 5. 任务文件中的可翻译块

工具仅提取并回填由 `BEGINTEXT` / `ENDTEXT` 包围的以下四类字段：

| 字段 | 常见显示位置 | 翻译建议 |
| --- | --- | --- |
| `MISSIONTITLE` | 任务列表、简报标题 | 必译，尽量简短 |
| `DESCRIPTION` | 列表简介、目标/事件说明 | `#1` 通常优先翻译，后续块按界面验证推进 |
| `PLAYERTASKING` | 玩家简报 / 作战命令 | 必译，内容最长 |
| `TASKINGMESSAGE` | 任务指令或动态任务信息 | 若存在，应翻译并实机触发验证 |

同一字段可在一个任务文件内出现多次。JSON 键使用出现顺序编号，例如：

```json
{
  "DESCRIPTION#1": "整备锚泊与航行设备，立即出港驶向外海。",
  "MISSIONTITLE#1": "非洲蜂巢",
  "PLAYERTASKING#1": "..."
}
```

`DESCRIPTION#2` 之后通常对应目标、事件或对象说明，并非任务列表首页描述。不要在未确认显示场景前一次性意译全部目标文本。

## 6. 第一步：导出英文任务文本

导出全部任务：

```powershell
& $python scripts\export_scenario_text.py --game-dir $game
```

默认输出至 `translations\scenario_export\`。当前会导出全部 `*.ms`、`*.mp` 与 `*.mc` 文件。

只查看或导出一个任务，例如 `SM08`：

```powershell
& $python scripts\scenario_text_tool.py extract `
  "$game\Scenario\SM08.ms" `
  "translations\scenario_export\SM08.json"
```

导出结果是纯 JSON，可直接检索原文：

```powershell
Select-String -LiteralPath 'translations\scenario_export\SM08.json' -Pattern 'African|EMERGENCY'
```

## 7. 第二步：建立中文译文文件

在 `translations\scenarios\` 中创建与任务文件对应的译文文件。命名规则为：

| 原任务文件 | 中文译文文件 |
| --- | --- |
| `SM08.ms` | `SM08_zh.json` |
| `KSM01.ms` | `KSM01_zh.json` |
| `MP4-NGFS.mp` | `MP4-NGFS_zh.json` |
| `001_Petropavlovsk.mc` | `001_Petropavlovsk_zh.json` |

可以从导出的 JSON 复制起步，然后仅保留当前要验证的条目。局部翻译是允许的；未出现在 `_zh.json` 中的文本块保持英文原文。

### 首轮翻译顺序

对每个任务，建议按以下顺序推进：

1. `MISSIONTITLE#1`：先确认任务列表中标题显示正常。
2. `DESCRIPTION#1`：确认列表说明或预览区域。
3. `PLAYERTASKING#1`：确认简报正文分页、换行和滚动。
4. `TASKINGMESSAGE#*`：进入游戏触发任务消息后验证。
5. `DESCRIPTION#2` 及之后文本：在确认其目标/事件显示位置后翻译。

## 8. 翻译规范与不可破坏内容

### 必须保留

- JSON 键名，如 `PLAYERTASKING#1`，不得自行改名。
- 格式标记 `<R>`；它承担正文中的换行/段落排版作用。
- 军事编号结构，如 `1.`、`A.`、`(1)`，建议保留便于阅读与原文核对。
- 舰号、编制号、时间及坐标等任务事实，如 `FFG 38`、`CTF 60`、`1830/2`。
- 任务中有操作意义的专名或呼号；首次可写为“柯茨号（FFG 38）”一类中英兼容形式。

### 不应编辑

不要直接编辑任务原文件中的结构与逻辑语句，包括但不限于：

- `ENTITY`、`HULLID`、`ALLIANCE`、`WAYPOINT`
- `SCRIPT` 块内的命令文本
- `GOAL`、`TRIGGERTYPE`、`ATTACHEDTARGETOBJ`
- `BEGINTEXT` 与 `ENDTEXT` 标记本身

使用 `scenario_text_tool.py patch` 回填可避免误改这些结构。

### 文风与版面建议

- 任务列表标题尽量控制在 4–12 个汉字，避免过长挤压。
- 列表简介使用一句话，优先描述玩家任务，不展开背景。
- 简报正文可使用中文标点；英文缩写、舰名和单位保持可辨识。
- 现有中文字形为 `16×16` 点阵，长段落显示密度高；应避免冗长直译。
- 不要把 `<R>` 改成普通换行；普通换行只用于提高 JSON 可读性，游戏版面由 `<R>` 主导。

## 9. 第三步：回填单个任务进行检查

将一个译文 JSON 回填到独立输出文件，而不直接覆盖游戏原件：

```powershell
New-Item -ItemType Directory -Force -Path 'build\Scenario' | Out-Null
& $python scripts\scenario_text_tool.py patch `
  "$game\Scenario\SM08.ms" `
  "translations\scenarios\SM08_zh.json" `
  "build\Scenario\SM08.ms"
```

检查中文是否实际写入：

```powershell
Select-String -LiteralPath 'build\Scenario\SM08.ms' -Pattern '非洲蜂巢|交战规则'
```

工具以 UTF-8 写出目标任务文件，也能读取已经安装过中文的 UTF-8 任务文件，因此可重复迭代构建。

## 10. 第四步：构建可运行任务汉化包

### 当前样例包

构建已完成译文的 `SM08` 包：

```powershell
& $python scripts\build_mission_poc.py --game-dir $game
```

输出路径：

```text
build\mission_zh_poc\runtime\
├─ dinput8.dll
├─ AppTextE.dll
├─ Graphics\
│  ├─ shared.ndx
│  └─ shared.grp
└─ Scenario\
   └─ SM08.ms
```

### 多任务合并包

当 `translations\scenarios\` 下已有多个译文文件时，可一次生成统一运行包：

```powershell
& $python scripts\build_mission_poc.py --game-dir $game `
  --scenario-translations `
  translations\scenarios\SM08_zh.json `
  translations\scenarios\KSM01_zh.json `
  translations\scenarios\P3SM01_zh.json
```

构建器会：

1. 收集所有译文中出现的中文字符。
2. 将所需字形生成到新增 `dw_zh_*` 字体页。
3. 重建 `Graphics\shared.ndx/.grp`。
4. 编译相应字符映射的 `dinput8.dll`。
5. 逐个回填任务文件至输出包的 `Scenario\` 目录。

注意：每次译文新增字符后，必须重新复制新的 `dinput8.dll` 与 `Graphics\shared.ndx/.grp`；只复制新的任务文件可能会让新增汉字显示为问号。

## 11. 第五步：安装测试包

以 `build\mission_zh_poc\runtime\` 为例：

```powershell
$pack = 'D:\project\dangerous waters\dangerous_waters_chinese_translation\build\mission_zh_poc\runtime'
Copy-Item "$pack\dinput8.dll" "$game\dinput8.dll" -Force
Copy-Item "$pack\AppTextE.dll" "$game\AppTextE.dll" -Force
Copy-Item "$pack\Graphics\shared.ndx" "$game\Graphics\shared.ndx" -Force
Copy-Item "$pack\Graphics\shared.grp" "$game\Graphics\shared.grp" -Force
Copy-Item "$pack\Scenario\*" "$game\Scenario\" -Force
```

安装后启动游戏，进入 `MISSIONS` 页面验证任务。

## 12. 第六步：实机验收清单

### 任务列表页

- 任务标题是否显示中文，且未截断或覆盖相邻控件。
- `DESCRIPTION#1` 是否显示完整，换行是否合理。
- 其他仍为英文的任务是否保持英文，字母、数字、标点是否无污染。

### 简报页

- `PLAYERTASKING#1` 是否正常出现。
- 中文标点、数字、舰号与英文缩写是否正确。
- 多行文本是否居左、是否出现重叠或异常空行。
- 页面滚动、翻页或返回按钮是否正常。

### 进入任务后

- 任务是否能够正常载入，无解析错误或闪退。
- `TASKINGMESSAGE` 或后续目标说明在触发时是否显示正常。
- 已汉化任务的游戏逻辑、目标判定和脚本行为是否不受影响。

### 字库回归检查

- 主菜单退出弹窗中文是否仍正常。
- 任意英文界面中的 `A-Z`、数字与符号是否仍是正常原字形。
- 若出现问号，确认该字符是否已包含在本次构建使用的译文 JSON 中。

## 13. 批量推进建议

任务文件数量较多，建议按可测试的批次推进，而非一次翻译全部内容：

| 批次 | 内容 | 目标 |
| --- | --- | --- |
| A | `SM*.ms` | 先完成当前可进入的单人任务链 |
| B | `KSM*.ms`、`P3SM*.ms`、`SSM*.ms` | 按平台覆盖单人任务 |
| C | `*.mc` | 战役任务，需同时检查战役入口显示 |
| D | `*.mp` | 多人任务，最后处理并验证联机界面 |

每个批次采用同一循环：

1. 导出该批次英文 JSON。
2. 建立 `_zh.json` 并先翻译标题、首页说明、玩家简报。
3. 构建含该批次所有译文的运行包。
4. 逐任务实机检查并记录显示问题。
5. 再补充目标说明、动态任务消息和术语统一。

建议维护一个术语表，至少统一以下类别：

- 舰艇类型与型号：`FFG`、`SSN`、`P-3`、`MH-60`
- 指挥编制：`CTF`、`Task Force`、`Fleet`
- 交战规则术语：`Hostile Act`、`Hostile Intent`、`ROE`
- 导航与战术词汇：`Waypoint`、`Transit`、`Search`、`Barrier`

## 14. 常见问题与排障

### 中文显示为乱码

原因通常是仅覆盖了 `Scenario\*.ms`，未安装 UTF-8 钩子及中文字体页。

处理：

```powershell
Copy-Item 'build\mission_zh_poc\runtime\dinput8.dll' "$game\dinput8.dll" -Force
Copy-Item 'build\mission_zh_poc\runtime\Graphics\shared.*' "$game\Graphics\" -Force
```

### 个别汉字显示为 `?`

原因是任务译文已变化，但仍使用旧版字体页或旧版 `dinput8.dll`。

处理：重新运行 `build_mission_poc.py`，并同时覆盖 `dinput8.dll` 与 `Graphics\shared.ndx/.grp`。

### 英文字符被替换成中文

原因通常是仍安装了早期“代理 ASCII 槽位”测试包。

处理：重新生成当前 UTF-8 包，并确保构建输出显示使用干净源：

```text
Using shared font source archive: ...\Graphics\back\shared
```

### 再次构建时提示解码失败

当前版本 `scenario_text_tool.py` 已可读取原始 ASCII 或已汉化的 UTF-8 任务文件。如仍遇到问题，检查是否使用了旧脚本副本或任务文件已被非 UTF-8 编辑器另存为其他编码。

### 任务载入失败或行为异常

首先恢复备份的原任务文件。常见原因是手工编辑了文本块之外的结构语句。后续只通过 `scenario_text_tool.py patch` 回填译文，不直接保存完整 `.ms/.mp/.mc` 文件。

## 15. 恢复原版

恢复测试前的资源：

```powershell
$backup = Join-Path $game 'ChinesePatchBackup'
Copy-Item "$backup\AppTextE.dll" "$game\AppTextE.dll" -Force
Copy-Item "$backup\Graphics\shared.ndx" "$game\Graphics\shared.ndx" -Force
Copy-Item "$backup\Graphics\shared.grp" "$game\Graphics\shared.grp" -Force
Copy-Item "$backup\Scenario\*" "$game\Scenario\" -Force
if (Test-Path "$backup\dinput8.dll") {
  Copy-Item "$backup\dinput8.dll" "$game\dinput8.dll" -Force
} else {
  Remove-Item "$game\dinput8.dll" -Force -ErrorAction SilentlyContinue
}
```

## 16. 当前可直接测试的样例

当前已提供：

| 文件 | 内容 |
| --- | --- |
| `translations\scenarios\SM08_zh.json` | “非洲蜂巢”任务的标题、列表描述与玩家简报译文 |
| `scripts\build_mission_poc.py` | 含中文字库与任务回填的统一构建命令 |
| `build\mission_zh_poc\runtime\` | 构建后可安装测试的运行包 |

首轮测试重点不是译文润色，而是确认长篇中文任务简报在 FUI 页面中的换行、滚动、字体页扩展和任务加载安全性。显示链路确认稳定后，即可按本流程逐批推进全部任务文本。
