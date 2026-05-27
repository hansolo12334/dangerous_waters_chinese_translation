# 文本与字体逆向记录

## 主文本 DLL

- 分析对象：`D:\project\dangerous waters\Dangerous Waters\dangerouswaters.exe`。
- IDA 数据库基址为 `0x400000`；`0x43339C` 引用格式串 `%s\AppText%c.dll`，随后加载语言资源 DLL。
- 语言字符在拼接前被转为大写，英文运行路径加载 `AppTextE.dll`。
- `AppTextE.dll` 的资源区由 `RT_STRING` 组成，目前提取到 2354 条可翻译文本。
- `0x459300` 已标记为 `load_app_text_dll_once`，负责缓存并加载语言资源 DLL。
- `0x459370` 已标记为 `get_app_text_ansi`，其内部通过 `LoadStringA` 把资源文本读入 256 字节 ANSI 缓冲区，而非直接保留 UTF-16。
- 实机验证：ASCII 替换弹窗标题与正文可以显示；中文替换会显示 UTF-8 字节对应的西文乱码，说明资源 DLL 链路已生效而编码/渲染链路仍为单字节。

## 工作站文本 DLL

| 文件 | 字符串数 |
| --- | ---: |
| `Interfaces\688I\textE.dll` | 620 |
| `Interfaces\AkulaII\textE.dll` | 728 |
| `Interfaces\FFG\TextE.dll` | 740 |
| `Interfaces\Kilo\TextE.dll` | 946 |
| `Interfaces\MH60\TextE.dll` | 397 |
| `Interfaces\P3\textE.dll` | 377 |
| `Interfaces\ssn21\TextE.dll` | 619 |
| `Interfaces\Kilo\TextCE.dll` | 946 |

`controllers.ini` 中中国 Kilo 使用 `[TEXTDLL] "Textc"`，再拼接当前英文语言码 `E`，因此 `TextCE.dll` 是平台台词分支而不是完整中文包。

## 字体路径

- `dangerouswaters.exe` 导入 `DrawTextW`、`DrawTextA` 与 `CreateFontIndirectA`，说明至少存在一条 Unicode GDI 绘制路径；但已测试的退出弹窗经 FUI 自绘控件而非可直接利用的系统消息框路径。
- 可执行文件中还含有 `fru_plain.bmp`、`fru_bold.bmp`、`font3D.bmp` 字体名称。
- `grp\bin\grp.exe <游戏目录>\Graphics\shared -list "*fru*"` 能列出 `fru_plain.bmp/.dim`、`fru_bold.bmp/.dim` 等字体资源。
- 各平台的 `Interfaces\<平台>\fonts.ndx/.grp` 另包含工作站专用字体，例如 Kilo 的 `LGoth_10.bmp/.dim`。
- `fru_plain.dim` 等字体定义文件为文本格式，记录 `block_width`、`block_height` 与 `32..255` 的字形宽度。
- 字体解析函数 `assign_single_byte_font_glyph`（`0x47F960`）将编号强制转为 `unsigned char` 后索引 256 项字形表，因此该 FUI 字体不能直接按 Unicode 汉字码位取字。
- 字宽测量函数 `measure_fui_bitmap_text_bytes`（`0x47E850`）在 `0x47E8E2` 对字符串逐字节读取，并以每个字节直接索引同一字形表；未发现 UTF-8 或 GBK 双字节组合处理。
- 单行绘制函数 `render_fui_bitmap_text_line_bytes`（`0x47EAC0`）与对齐/多行绘制函数 `render_fui_bitmap_text_bytes`（`0x47EBA0`）同样以原始字节索引字形，最终调用 `draw_fui_font_glyph_quad`（`0x47EDF0`）提交字形四边形。
- 共享字体初始化函数 `initialize_shared_fui_fonts`（`0x42DF20`）载入 `fru_plain`、`fru_bold`、`fru_small`、`arial_nonaa`，其唯一的收尾调用 `finalize_shared_font_archive_thunk`（`0x401582`）可在 `shared` 资源仍可用时作为追加中文字库页的预加载切口。
- 弹窗构造代码还会以 `strlen()` 计算排版位置，因此即使只替换绘制动作，多字节中文仍会造成对齐和换行错误。

结论是：DLL 文本已可提取和回填，当前退出弹窗确认走单字节位图字库。完整动态汉化需要改造文字解码/绘制链路，或建立受限的单字节代理字符字库。

## 主菜单观察结果

- 主菜单启动画面中的 `OPTIONS` 并非 DLL 动态文字，而是 `Graphics\mainmenu.grp` 内 `options_x510y440.bmp` 的四态按钮图片。
- 因此仅替换 `AppTextE.dll` 后观察启动画面不会变化；DLL PoC 需要触发弹窗或实际使用动态文本的工作站/编辑器界面。
- `scripts\build_mainmenu_poc.py` 已扩展为重绘九张主菜单四态图片：任务、战役、快速任务、任务编辑器、联机对战、玩家日志、选项、海军资料库与退出。
- 初始 `OPTIONS` 图片 PoC 已由实机确认能够显示中文；完整菜单包输出至 `build\mainmenu_zh\Graphics\mainmenu.ndx/.grp`。
- 主菜单 `EXIT` 动作在 `0x4351B4` 读取字符串 ID `1259`（`Are you sure you want to exit the game?`），并将 ID `1258` 作为对话框标题，因此适合作为动态文本固定测试点。
- `scripts\build_dynamic_text_poc.py` 会生成 ASCII 与中文两份 `AppTextE.dll`，用于把“资源是否加载”和“中文是否可渲染”拆成两个实验。
- 该动态文本实验已经得出结论：ASCII 成功，直接中文产生乱码。

## 单字节字形重映射实验

- `scripts\build_bitmap_font_text_poc.py` 会同步生成一份代理 ASCII 的 `AppTextE.dll` 与重绘后的 `Graphics\shared.ndx/.grp`。
- 代理映射为 `0..9`、`@`、`#`、`$`、`!` 到所需汉字；退出弹窗标题的代理串应渲染成“中文动态文本测试”，正文应渲染成“是否退出游戏？”。
- `assets\wqy-bitmapsong\wenquanyi_12pt.pcf` 提供可直接提取的 `16×16` 中文点阵，与基础 `fru_*` 字格尺寸一致；脚本已直接解析 PCF 字形表而非依赖系统 TTF。
- 实机验证成功：替换测试 DLL 与重绘后的 `Graphics\shared` 后，退出弹窗已能正确显示上述中文标题与正文。
- 该方案用于证明 FUI 位图字体可承载汉字，不是最终翻译方案，因为字形槽是全局共享的：被占用的 ASCII 字符在其他画面也会随之变成汉字。用户已实测观察到这一副作用。

## 动态中文方案判断

- 不修改程序时，每套 FUI 位图字体最多只能稳定使用 256 个单字节槽位，其中正常英文、数字、符号已占用大部分；覆盖常用 ASCII 会立即破坏其他界面。
- 可以把少量低使用率槽位用于菜单/弹窗的有限翻译，但不足以承载 `AppTextE.dll` 与平台文本 DLL 的完整汉化。
- 完整方案需要同时补丁化“字符串输入/解码、字宽测量、实际绘制”三环。仅将 `LoadStringA` 换为 Unicode 或仅扩大 `.bmp/.dim` 都不能解决问题。
- `scripts\build_utf8_fui_hook_poc.py` 与 `native\dinput8_proxy\dinput8_proxy.cpp` 已实现第一版注入式路线：游戏导入的 `DINPUT8.DirectInput8Create` 由本地 32 位代理转发，同时代理钩住上述三个 FUI 函数。
- 注入包对纯 ASCII 串调用游戏原路径；对 UTF-8 中文串进行码点解码、正确字宽测量与中文页绘制。中文页命名为 `dw_zh_00.bmp/.dim` 起，按翻译 JSON 中实际出现的字形自动扩展，避免占用正常 ASCII 槽。
- 为避免中文字库纹理在资源档案切换后无法装载，代理在 `finalize_shared_font_archive_thunk` 收尾前预加载所有新增中文页；此处发生于原始共享字体载入完成且 `shared` 仍处于有效加载上下文时。
- 当前游戏目录中的 `Graphics\shared` 已因早期代理槽测试与 `Graphics\back\shared` 哈希不同；UTF-8 构建脚本优先以 `Graphics\back\shared` 为干净源，防止继承旧 ASCII 字形污染。

## 任务简报文本

- `MISSIONS` 页面使用的任务内容并不来自 `AppTextE.dll`；单人任务、多人任务和战役关卡为 `Scenario\*.ms`、`*.mp`、`*.mc` 明文文件。
- `African Bees Nest` 位于 `Scenario\SM08.ms`：首个 `DESCRIPTION` 文本块为列表说明，首个 `MISSIONTITLE` 为任务标题，首个 `PLAYERTASKING` 为玩家简报。
- EXE 中存在 `MISSIONTITLE`、`DESCRIPTION`、`PLAYERTASKING` 标识及 `%s\scenario\%s` 文件路径；任务选择代码直接读取场景文件，故 UTF-8 FUI 注入后可直接回填 UTF-8 中文任务正文。
- `scripts\scenario_text_tool.py` 可按 `FIELD#序号` 提取/回填 `BEGINTEXT` 至 `ENDTEXT` 文本块，避免改动任务实体、触发器和脚本命令。
- `scripts\build_mission_poc.py` 已生成 `SM08` 的中文验证包：任务名“非洲蜂巢”、首页描述及完整玩家任务书；该翻译引入 203 个中文字形，仅需一个新增字体页。

## 推荐推进顺序

1. 实机验证 `build\utf8_fui_hook_poc` 的退出弹窗，并确认切入其他 FUI 界面后英文不再被中文字形污染。
2. 将翻译 JSON 扩展到常用菜单、设置与平台文本 DLL，逐屏确认仍存在的非 FUI 字体路径。
3. 对仍使用 `strlen()` 进行位置计算的少量控件补充 UTF-8 逻辑字符宽度修正，并保留格式符验证。
4. 继续处理 UI 图片与 `Scenario\*.ms` / `*.mc` 明文任务文本。
