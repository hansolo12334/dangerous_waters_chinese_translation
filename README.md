# Dangerous Waters 汉化研究

`Dangerous Waters` 是一款非常优秀的老游戏。本仓库用于研究文本、字体与 UI 图片的汉化路线。  
`.ndx/.grp` 工具来自 [Adam Mil 的逆向文章](https://www.adammil.net/blog/v108_Reverse_Engineering_Dangerous_Waters.html)。

## 当前结论

- UI 图片可以从 `.ndx/.grp` 解包、修改并重新打包；已有测试图见 `example/temp1.png`。
- 英文文字本体并不在 `fru_bold_r1.bmp` 字体图片里：逆向已确认主文本存放于 `AppTextE.dll` 的 UTF-16 `RT_STRING` 资源。
- 操作台文本另外位于 `Interfaces\<平台>\TextE.dll`；中国型号 Kilo 会使用 `Interfaces\Kilo\TextCE.dll`。
- 主菜单图片 PoC 已在游戏中验证可以显示中文；动态文本 ASCII PoC 也已验证能从 `AppTextE.dll` 读取。
- 动态文本直接写入中文会出现 UTF-8 字节乱码；弹窗使用的 FUI 位图字体只按单字节槽位索引，不能直接显示 Unicode 汉字。
- 文泉驿点阵字形重映射 PoC 已在游戏中验证成功，动态弹窗可以显示中文。
- 不覆盖 ASCII 的 UTF-8 FUI 注入包已可构建：代理 `dinput8.dll` 接管动态中文串，并从新增的独立 `dw_zh_*` 字体页绘制汉字。

详细逆向记录与测试路线见 `docs/reverse_engineering.md`。
已确认的静态图片汉化候选与推进顺序见 `docs/static_graphics_inventory.md`。
任务文件提取、翻译、构建、安装与验收流程见 `docs/mission_localization_workflow.md`。
通用 `AppTextE.dll` 与平台 `TextE.dll` 动态文本汉化流程见 `docs/dll_text_localization_workflow.md`。

## 文本 PoC

使用你指定的 Python 环境导出 DLL 字符串并生成一个中文显示试验 DLL：

```powershell
$python = 'D:\Miniconda\envs\mujoco\python.exe'
$game = 'D:\project\dangerous waters\Dangerous Waters'
& $python scripts\dw_string_tool.py extract "$game\AppTextE.dll" translations\export\AppTextE.tsv
& $python scripts\dw_string_tool.py patch "$game\AppTextE.dll" translations\poc_apptext_zh.json build\AppTextE.dll
& $python scripts\export_all_text.py --game-dir $game
```

`AppTextE.dll` 只影响动态文字；启动主菜单按钮属于图片，因此替换 DLL 后仅观察首页看不到改变是正常的。另需注意程序通过 `LoadStringA` 读文本，中文还会受系统 ANSI 代码页或后续程序补丁影响。

### 动态文本 PoC

主菜单点击 `EXIT` 后的确认框正文确定来自 `AppTextE.dll` 的资源 ID `1259`，标题来自 ID `1258`。生成两个可测试 DLL：

```powershell
& $python scripts\build_dynamic_text_poc.py --game-dir $game
```

- 先用 `build\dynamic_text_poc\ascii\AppTextE.dll` 覆盖原 DLL 并点击 `EXIT`；确认对话框标题显示 `APP TEXT DLL POC`，证明 DLL 被实际读取。
- 中文 DLL 已实测为乱码：`LoadStringA` 输出的 UTF-8 字节被位图字体逐字节绘制，不能仅靠替换 DLL 完成汉化。

### 位图字形重映射 PoC

为验证动态弹窗能否经现有字体引擎显示汉字，可把仅用于测试的 ASCII 槽位重绘为汉字，并让 DLL 写入这些代理字符：

```powershell
& $python scripts\build_bitmap_font_text_poc.py --game-dir $game
```

备份后同时覆盖 `AppTextE.dll` 与 `Graphics\shared.ndx/.grp` 为 `build\bitmap_font_text_poc\` 中同名文件，再点击 `EXIT`。该实验已实机确认标题可显示“中文动态文本测试”，正文可显示“是否退出游戏？”。此包会临时把数字和少量符号字形替换成汉字，只用于确认技术路径，测试后应恢复原文件。

该脚本默认直接读取 `assets\wqy-bitmapsong\wenquanyi_12pt.pcf` 的 `16×16` 文泉驿点阵汉字，尺寸与游戏基础字体槽位吻合，也避免依赖本机系统字体。文泉驿字体许可证信息见其目录内 `README` 与 `COPYING`。

### UTF-8 注入 PoC

完整动态路线不再占用英文、数字或标点槽位，而是在 `Graphics\shared` 中追加独立中文字库页，并以 32 位 `dinput8.dll` 代理钩住 FUI 的字宽和绘字核心：

```powershell
& $python scripts\build_utf8_fui_hook_poc.py --game-dir $game --translations translations\poc_exit_zh.json
```

脚本若发现 `$game\Graphics\back\shared.ndx/.grp`，会优先将其作为干净的原始字库来源；这很重要，因为早期字形重映射 PoC 会永久改写测试包中的 ASCII 字形。测试前备份现用文件，再从 `build\utf8_fui_hook_poc\` 复制 `dinput8.dll`、`AppTextE.dll` 与 `Graphics\shared.ndx/.grp` 到游戏目录，进入主菜单点击 `EXIT` 检查中文动态弹窗。

该包的工作方式是：ASCII 串完全回到游戏原绘制路径；含 UTF-8 中文的串由代理解码，并映射到新增 `dw_zh_00.bmp/.dim` 等页。扩大翻译范围时，把新的 JSON 文本文件继续附加到 `--translations` 后，脚本会自动收集新增汉字并按需生成多页字库。

### 任务简报汉化

任务选择页与简报内容位于明文 `Scenario\*.ms/.mp/.mc` 文件中。`African Bees Nest` 已定位为 `Scenario\SM08.ms`，其中首页描述来自 `DESCRIPTION#1`、任务名来自 `MISSIONTITLE#1`、简报正文来自 `PLAYERTASKING#1`。生成已翻译的任务样例包：

```powershell
& $python scripts\build_mission_poc.py --game-dir $game
```

将 `build\mission_zh_poc\runtime\` 内的 `dinput8.dll`、`AppTextE.dll`、`Graphics\` 与 `Scenario\` 覆盖到备份后的游戏目录；在 `MISSIONS` 中选择“非洲蜂巢”，即可测试任务说明和任务书。

批量导出全部单人、多人和战役任务文本：

```powershell
& $python scripts\export_scenario_text.py --game-dir $game
```

导出的 JSON 位于 `translations\scenario_export\`；每个键按文件内出现顺序标识文本块，例如 `MISSIONTITLE#1`、`DESCRIPTION#1`、`PLAYERTASKING#1`。单文件回填命令为：

```powershell
& $python scripts\scenario_text_tool.py patch "$game\Scenario\SM08.ms" translations\scenarios\SM08_zh.json build\Scenario\SM08.ms
```

## 图形与字库

无需 Python 依赖即可使用仓库内置的 `grp.exe` 查看和解包资源：

```powershell
.\grp\bin\grp.exe "D:\project\dangerous waters\Dangerous Waters\Graphics\shared" -list "*fru*"
.\grp\bin\grp.exe "D:\project\dangerous waters\Dangerous Waters\Graphics\shared" -unpack "fru_plain.*" build\shared_fonts -force
```

现有 `scripts/unpack_dw_files.py` 与 `scripts/repack_dw_files.py` 是早期 Python.NET 实验脚本；当前 `mujoco` Python 环境没有 `pythonnet/clr`，优先直接使用 `grp\bin\grp.exe`。
注意：此版本 `grp.exe -unpack` 即使成功打印 `OK` 也会返回退出码 `1`，自动化脚本以实际导出文件是否存在为准。

## UI 回包

以 `Graphics\mainmenu.ndx/.grp` 为例，可先解除旧资源再加入修改图并压紧归档：

```powershell
.\grp\bin\grp_rebuild.exe "D:\project\dangerous waters\Dangerous Waters\Graphics\mainmenu" -unlink "MAINMENU_bkg.bmp" -add ".\modified\MAINMENU_bkg.bmp" -repack
```

修改资源前请保留原始 `.ndx/.grp` 与 DLL 备份。

### 主菜单汉化包

启动游戏后立刻可见的菜单按钮是 `Graphics\mainmenu.grp` 中的四态图片，不来自 `AppTextE.dll`。生成九个主菜单按钮的中文图片包：

```powershell
& $python scripts\build_mainmenu_poc.py --game-dir $game
```

备份游戏目录下 `Graphics\mainmenu.ndx` 与 `Graphics\mainmenu.grp` 后，用 `build\mainmenu_zh\Graphics\` 内的同名文件覆盖。当前按钮翻译如下：

| 资源 | 中文标签 |
| --- | --- |
| `MissionEditor_x575y340.bmp` | 任务编辑器 |
| `missions_x510y140.bmp` | 任务 |
| `campaign_x560y190.bmp` | 战役 |
| `multiplayer_x560y240.bmp` | 联机对战 |
| `playerslog_x550y390.bmp` | 玩家日志 |
| `options_x510y440.bmp` | 选项 |
| `quickmission_x585y285.bmp` | 快速任务 |
| `usniref_x460y485.bmp` | 海军资料库 |
| `exit_x550y555.bmp` | 退出 |

脚本使用 `assets\wqy-bitmapsong\wenquanyi_12pt.pcf` 的点阵字形绘制四种按钮状态，翻译文案可在 `scripts\build_mainmenu_poc.py` 的 `BUTTON_LABELS` 中调整。
