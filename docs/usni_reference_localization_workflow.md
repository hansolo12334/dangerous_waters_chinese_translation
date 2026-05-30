# Dangerous Waters 海军资料库汉化工作流

## 1. 资源来源

海军资料库（主菜单“海军资料库” / `USNI Reference`）不是 `AppTextE.dll`，也不是 `Scenario` 任务文本。

它主要由两个图形归档组成：

| 归档 | 内容 |
| --- | --- |
| `Graphics\usniref.ndx/.grp` | 海军资料库界面背景、左侧 `TEXT` / `PHOTO` / `3D` 等按钮图片 |
| `Graphics\usnidata.ndx/.grp` | 资料库正文 `.txt` 与照片 `.jpg` |

截图中的 `TOURVILLE CLASS DD` 对应 `Graphics\usnidata.grp` 内的：

- `TourvilleClassDD.txt`
- `Tourville_DD.jpg`

它的目录入口在 `France_TOC.txt` 中，形如：

```text
<FONT="fru_plain.bmp" COLOR=228 228 228 LINK="TourvilleClassDD.txt","Tourville_DD.jpg","Tourville DDG">   Tourville DD
```

`LINK` 内的 `.txt`、`.jpg` 文件名不能翻译，否则点击目录后会找不到目标；可翻译的是链接标签显示文字和目标 `.txt` 正文。

## 2. 查看与解包

```powershell
$game = 'D:\project\dangerous waters\Dangerous Waters'
.\grp\bin\grp.exe "$game\Graphics\usnidata" -list "*Tour*"
.\grp\bin\grp.exe "$game\Graphics\usnidata" -unpack "TourvilleClassDD.txt" build\usni_probe -force
```

也可解包全部资料：

```powershell
.\grp\bin\grp.exe "$game\Graphics\usnidata" -unpack "*" build\usni_probe -force
```

`usnidata` 中 `.txt` 是资料正文和目录页，`.jpg` 是照片。`usniref` 中的 `.bmp` 是界面图片，属于静态图汉化。

### 2.1 按截图正文反查文件名

有些条目的游戏显示名和文件名不完全一致，例如截图中的 `ARGENTINA / DIESEL SUBMARINES [SS] / TR-1700 CLASS`，真实文件名是：

- 正文：`TR-1700_SantaCruzSS.txt`
- 图片：`TR-1700_SantaCruz.jpg`
- 目录入口：`ARG_TOC.txt`

反查方法：

```powershell
$probe = "build\usni_all_probe"
Remove-Item $probe -Recurse -Force -ErrorAction SilentlyContinue
.\grp\bin\grp.exe "$game\Graphics\usnidata" -unpack "*.txt" $probe -force

rg -n -i "ARGENTINA|TR-1700|DIESEL SUBMARINES|Thyssen|SST-4|CSU-83" $probe
```

目录页中对应链接为：

```text
<FONT="fru_plain.bmp" COLOR=228 228 228 LINK="TR-1700_SantaCruzSS.txt","TR-1700_SantaCruz.jpg","Santa Cruz SSK">    TR-1700 SS
```

另一个容易误判的例子是 `USNI INFORMATION / BROWSER ENTRY INFORMATION`：

- 左上目录标题与按钮项来自 `Country_Weapons_TOC.txt` 或进入后的 `USNI_TOC.txt`。
- 右侧正文 `Terms and Abbreviations` 来自 `Terms.txt`。
- `USNI_TOC.txt` 还链接到 `Abbreviations.txt` 和 `ShipTypeDesignations.txt`。

反查命令：

```powershell
rg -n -i "Browser Entry Information|USNI INFORMATION|Terms and Abbreviations|following abbreviations" build\usni_all_probe
```

关键链接：

```text
<FONT="fru_plain.bmp" COLOR=216 188 24 LINK="USNI_TOC.txt", "nophoto.jpg","">    BROWSER ENTRY INFORMATION
<FONT="fru_plain.bmp" COLOR=228 228 228 LINK="Terms.txt","nophoto.jpg","">    Terms
<FONT="fru_plain.bmp" COLOR=228 228 228 LINK="Abbreviations.txt","nophoto.jpg","">    Acronyms/Abbreviations
<FONT="fru_plain.bmp" COLOR=228 228 228 LINK="ShipTypeDesignations.txt","nophoto.jpg","">    Ship Type Designations
```

## 3. 翻译文件格式

当前样例译文位于：

```text
translations\usni\TourvilleClassDD_zh.json
```

格式：

```json
{
  "file": "TourvilleClassDD.txt",
  "text": "法国\n驱逐舰 [DD]\n图尔维尔级驱逐舰\n..."
}
```

也可以使用更适合目录页的 `lines` 格式。脚本会自动用换行拼回原始文本：

```json
{
  "file": "Country_Weapons_TOC.txt",
  "lines": [
    "<FONT=\"fru_plain.bmp\" COLOR=24 180 240>USNI 资料:",
    "<end>",
    "<FONT=\"fru_plain.bmp\" COLOR=216 188 24 LINK=\"USNI_TOC.txt\", \"nophoto.jpg\", \"\">    浏览器条目说明",
    "<end>"
  ]
}
```

注意：

- `file` 必须是 `usnidata.grp` 内真实文件名。
- `text` 适合普通正文；`lines` 适合带大量 `<FONT>` / `<end>` 的 TOC 目录页。
- 可保留英文型号、雷达型号、导弹型号等技术缩写。
- 如果翻译目录页，如 `France_TOC.txt` 或 `Country_Weapons_TOC.txt`，必须保留 `<FONT ... LINK=\"...\">` 标签、`<end>` 和 `LINK` 文件名；只翻译 `>` 后面的可见文字。

## 4. 生成 usnidata 汉化包

```powershell
$python = 'D:\Miniconda\envs\mujoco\python.exe'
$game = 'D:\project\dangerous waters\Dangerous Waters'

& $python scripts\usni_text_tool.py `
  --game-dir $game `
  --output-dir build\usni_text_poc `
  --translations translations\usni
```

`--translations` 可以混用 JSON 文件和目录。目录会按文件名排序加载其中所有 `*.json`，重复路径会自动去重。

输出：

```text
build\usni_text_poc\Graphics\usnidata.ndx
build\usni_text_poc\Graphics\usnidata.grp
```

安装：

```powershell
Copy-Item "build\usni_text_poc\Graphics\usnidata.ndx" "$game\Graphics\usnidata.ndx" -Force
Copy-Item "build\usni_text_poc\Graphics\usnidata.grp" "$game\Graphics\usnidata.grp" -Force
```

## 5. 必须合并中文字库

USNI 正文显示仍使用 FUI 字体系统。只替换 `usnidata.grp` 后，中文可能显示为 `?`，因为字库映射没有包含 USNI 译文字形。

需要把 USNI JSON 加入统一字体构建：

```powershell
& $python scripts\build_utf8_fui_hook_poc.py `
  --game-dir $game `
  --apptext-source "$game\back\AppTextE.dll" `
  --output-dir build\combined_runtime `
  --translations translations\dll\AppTextE_zh.json `
  --font-text `
    translations\scenarios\SM08_zh.json `
    translations\usni
```

然后同时安装：

```powershell
Copy-Item "build\combined_runtime\dinput8.dll" "$game\dinput8.dll" -Force
Copy-Item "build\combined_runtime\AppTextE.dll" "$game\AppTextE.dll" -Force
Copy-Item "build\combined_runtime\Graphics\shared.ndx" "$game\Graphics\shared.ndx" -Force
Copy-Item "build\combined_runtime\Graphics\shared.grp" "$game\Graphics\shared.grp" -Force
Copy-Item "build\usni_text_poc\Graphics\usnidata.ndx" "$game\Graphics\usnidata.ndx" -Force
Copy-Item "build\usni_text_poc\Graphics\usnidata.grp" "$game\Graphics\usnidata.grp" -Force
```

规则与 Mission 相同：任何新增中文来源都必须放进同一次 `--font-text` 字库构建。

### 5.1 西文重音字符注意事项

当前中文字体页来自 `assets\wqy-bitmapsong\wenquanyi_12pt.pcf`，不一定包含西文重音字符。实测 `TourvilleClassDD.txt` 原文照片署名中的 `Prézelin`，如果仍保留 `é`，游戏会显示为 `Pr?zelin`。

处理建议：

- 优先将少量重音字符转写成 ASCII，例如 `Prézelin` 写作 `Prezelin`。
- 修改 JSON 后必须重新生成 `usnidata` 包；只重建 `dinput8.dll` / `Graphics\shared` 不会改变资料库正文。
- 验证命令：

```powershell
& $python scripts\usni_text_tool.py `
  --game-dir $game `
  --output-dir build\usni_text_poc `
  --translations translations\usni\TourvilleClassDD_zh.json

.\grp\bin\grp.exe build\usni_text_poc\Graphics\usnidata -unpack TourvilleClassDD.txt . -force
Get-Content -Encoding UTF8 .\TourvilleClassDD.txt | Select-String "照片来源"
Remove-Item .\TourvilleClassDD.txt -Force
```

### 5.2 文本已替换但部分汉字显示为 `?`

如果界面出现类似 `USNI ??`、`??器?目?明`、`?大利亚`，说明 `usnidata` 正文已经替换成功，但游戏目录中的 `Graphics\shared.ndx/.grp` 仍是旧字库包，缺少本批新增字形。

处理方式：

1. 重新构建统一字库时，把本批 USNI JSON 也放进 `--font-text`。
2. 同时复制新的 `dinput8.dll` 与 `Graphics\shared.ndx/.grp`。
3. 完全退出游戏后再启动；`shared` 字库在启动/进入界面时加载，运行中覆盖文件不会刷新。

示例：

```powershell
& $python scripts\build_utf8_fui_hook_poc.py `
  --game-dir $game `
  --apptext-source "$game\back\AppTextE.dll" `
  --output-dir build\combined_runtime_usni_toc_lines `
  --translations translations\dll\AppTextE_zh.json `
  --font-text `
    translations\scenarios\SM08_zh.json `
    translations\usni

Copy-Item "build\combined_runtime_usni_toc_lines\dinput8.dll" "$game\dinput8.dll" -Force
Copy-Item "build\combined_runtime_usni_toc_lines\Graphics\shared.ndx" "$game\Graphics\shared.ndx" -Force
Copy-Item "build\combined_runtime_usni_toc_lines\Graphics\shared.grp" "$game\Graphics\shared.grp" -Force
```

## 6. 批量推进建议

优先顺序：

1. 翻译 TOC 目录页，例如 `France_TOC.txt`，确认链接仍能打开。
2. 翻译当前截图对应的 `TourvilleClassDD.txt`，验证正文换行与滚动。
3. 按国家或类别批量推进对应 `.txt`。
4. 最后处理 `Graphics\usniref` 的静态按钮图片：`TEXT`、`PHOTO`、`3D`、`OK` 等。

每批测试清单：

- 目录页显示中文且链接可点击。
- 目标正文页显示中文，不出现 `?`。
- 照片页仍能显示对应 `.jpg`。
- 英文型号、数字、标点未被污染。
