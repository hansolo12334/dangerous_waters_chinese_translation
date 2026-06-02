# Dangerous Waters 汉化固化流水线

本流程用于把当前已验证的汉化来源统一构建成一个可安装包：

- 动态 DLL 文本：`translations\dll\AppTextE_zh.json`
- 任务文本：`translations\scenarios\*.json`
- USNI 资料库文本：`translations\usni\*.json`
- 静态图片：目前仅对主菜单关键按钮做程序式汉化，可选启用

## 1. 配置文件

默认配置位于：

```text
config\localization.yaml
```

主要配置项：

```yaml
game_dir: D:\project\dangerous waters\Dangerous Waters
output_dir: build\localized

runtime:
  enabled: true
  wqy_pcf: assets\wqy-bitmapsong\wenquanyi_11pt.pcf
  cjk_glyph_size: 14
  cjk_advance_extra: 2
  apptext_source: D:\project\dangerous waters\Dangerous Waters\back\AppTextE.dll
  shared_source: D:\project\dangerous waters\Dangerous Waters\Graphics\back\shared
  apptext_translations:
    - translations\dll\AppTextE_zh.json
  font_text:
    - translations\scenarios
    - translations\usni

scenarios:
  enabled: true
  source_dir: D:\project\dangerous waters\Dangerous Waters\Scenario
  translations:
    - translations\scenarios
  suffix: _zh

usni:
  enabled: true
  translations:
    - translations\usni

static_graphics:
  mainmenu:
    enabled: false

install:
  enabled: false
```

规则：

- `runtime.cjk_glyph_size`：中文字形实际绘制尺寸，范围 `8..16`。文泉驿 PCF 是位图字体，默认建议 `16` 保持原始清晰度；缩小到 `14` 或 `13` 可能丢笔画、发糊。
- `runtime.cjk_advance_extra`：中文字形额外字距，范围 `0..8`。默认建议 `1`，可缓解紧凑 UI 中的横向粘连。
- `runtime.wqy_pcf`：中文字形来源。需要小字号时优先使用原生小字号 PCF，例如 `wenquanyi_11pt.pcf`，不要把 `wenquanyi_12pt.pcf` 硬缩小。
- `runtime.apptext_translations`：只放要写入 `AppTextE.dll` 的 JSON。
- `runtime.font_text`：放不写入 `AppTextE.dll`、但必须纳入中文字库的 JSON 或目录，例如 `scenarios`、`usni`。
- `scenarios.translations`：任务译文目录或单个 JSON，文件名按 `SM08_zh.json` 这类格式匹配原始任务文件。
- `usni.translations`：USNI 译文目录或单个 JSON。
- `static_graphics.mainmenu.enabled`：是否重绘并回包主菜单关键按钮。

## 2. 一键构建

```powershell
$python = 'D:\Miniconda\envs\mujoco\python.exe'

& $python scripts\build_localization.py `
  --config config\localization.yaml
```

默认输出：

```text
build\localized\package\
├─ dinput8.dll
├─ AppTextE.dll
├─ Graphics\
│  ├─ shared.ndx
│  ├─ shared.grp
│  ├─ usnidata.ndx
│  └─ usnidata.grp
└─ Scenario\
   ├─ SM08.ms
   └─ ...
```

如果启用 `static_graphics.mainmenu.enabled: true`，还会输出：

```text
build\localized\package\Graphics\mainmenu.ndx
build\localized\package\Graphics\mainmenu.grp
```

## 3. 安装

手动复制：

```powershell
$game = 'D:\project\dangerous waters\Dangerous Waters'
$pack = 'D:\project\dangerous waters\dangerous_waters_chinese_translation\build\localized\package'

Copy-Item "$pack\dinput8.dll" "$game\dinput8.dll" -Force
Copy-Item "$pack\AppTextE.dll" "$game\AppTextE.dll" -Force
Copy-Item "$pack\Graphics\*" "$game\Graphics\" -Force
Copy-Item "$pack\Scenario\*" "$game\Scenario\" -Force
```

或直接安装：

```powershell
& $python scripts\build_localization.py `
  --config config\localization.yaml `
  --install
```

也可以在 YAML 中设置：

```yaml
install:
  enabled: true
```

## 4. 静态图片边界

当前脚本化静态图片只适合这类资产：

- 主菜单四态按钮
- 文字区域位置固定
- 背景可用简单矩形擦除
- 中文短词可直接用文泉驿点阵字重绘

不建议强行脚本化：

- 大面积说明图
- 文字与复杂背景混合的图片
- 需要重新排版、描边、透视或纹理修复的图片

这类图片建议使用 Photoshop、GIMP 或人工 PSD 流程处理，再用现有 `grp` 工具回包。

## 5. 常见错误

### 文本已替换但显示 `?`

说明资源文件已经更新，但 `dinput8.dll` / `Graphics\shared.*` 不是包含本批字形的最新运行包。重新运行流水线并覆盖 `dinput8.dll`、`Graphics\shared.ndx/.grp`。

### 中文看起来重叠或不清晰

紧凑 UI 控件常按英文小字体设计。若中文显示过满、贴边或像重叠，可调小中文字形并增加字距：

```yaml
runtime:
  wqy_pcf: assets\wqy-bitmapsong\wenquanyi_11pt.pcf
  cjk_glyph_size: 14
  cjk_advance_extra: 2
  cjk_skip_outline_layers: false
  cjk_max_source_height: 16
```

`cjk_skip_outline_layers` 是实验选项，用于跳过疑似 `fru_*_r1/r3/r4` 的阴影/描边字体层。实测部分界面实际只走这些字体对象，开启后可能导致中文全部消失，因此默认应保持 `false`。

当前可用字体尺寸：

```text
assets\wqy-bitmapsong\wenquanyi_9pt.pcf     原生约 11×11
assets\wqy-bitmapsong\wenquanyi_10pt.pcf    原生约 12×12
assets\wqy-bitmapsong\wenquanyi_11pt.pcf    原生约 14×14
assets\wqy-bitmapsong\wenquanyi_12pt.pcf    原生约 16×16
assets\wqy-bitmapsong\wenquanyi_13px.pcf    原生约 13×13，部分字宽可变
```

`assets\wqy-bitmapsong-extra` 中的 `wenquanyi_14pt.bdf` 与 `wenquanyi_8pt.bdf` 当前为 `0` 字节，不能直接用于构建。

如果仍然拥挤，优先压缩译文或减少单行字数；确实需要试缩小时再尝试：

```yaml
runtime:
  cjk_glyph_size: 14
  cjk_advance_extra: 2
```

修改后必须重新运行 `build_localization.py` 并覆盖 `dinput8.dll`、`Graphics\shared.ndx/.grp`。

### Mission 正常，USNI 变 `?`

确认 `runtime.font_text` 包含：

```yaml
font_text:
  - translations\scenarios
  - translations\usni
```

### 只想构建文本，不处理主菜单

保持：

```yaml
static_graphics:
  mainmenu:
    enabled: false
```

### 新增多个任务

把译文放到：

```text
translations\scenarios
```

然后重新运行 `build_localization.py`。无需逐个追加命令参数。
