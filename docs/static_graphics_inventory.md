# Graphics 静态文字资源清单

本清单基于解包后的图片目视确认，范围为 `Dangerous Waters\Graphics`。以下图片内的英文属于烘焙图像，不会随 `AppTextE.dll` 翻译自动变化。

## 已处理：主菜单

归档：`Graphics\mainmenu.ndx/.grp`

| 资源 | 当前译文 |
| --- | --- |
| `missions_x510y140.bmp` | 任务 |
| `campaign_x560y190.bmp` | 战役 |
| `multiplayer_x560y240.bmp` | 联机对战 |
| `quickmission_x585y285.bmp` | 快速任务 |
| `MissionEditor_x575y340.bmp` | 任务编辑器 |
| `playerslog_x550y390.bmp` | 玩家日志 |
| `options_x510y440.bmp` | 选项 |
| `usniref_x460y485.bmp` | 海军资料库 |
| `exit_x550y555.bmp` | 退出 |

`688i_menu.bmp`、`AKULA_menu.bmp`、`FFG7_menu.bmp`、`KILO_menu.bmp`、`MH60_menu.bmp`、`P3C_menu.bmp` 与 `SSN21_menu.bmp` 显示平台型号名称，暂不翻译。

## 高优先级界面

| 归档 | 已确认包含英文的图片 | 建议译文/内容 |
| --- | --- | --- |
| `mis_sel` | `MISSIONS_bkg.bmp`, `MISSIONSCampaign_bkg.bmp`, `missionsmp_bkg.bmp` | 标题、任务位置/描述/目标等背景栏目 |
| `mis_sel` | `MISSIONS_TRAINING_x030y110.bmp`, `MISSIONS_SINGLE_x030y160.bmp`, `MISSIONS_SAVED_x030y205.bmp` | 训练、单人任务、存档任务 |
| `mis_sel` | `mp_sort_mission.bmp`, `mp_sort_platform.bmp`, `mp_sort_player.bmp` | 任务、平台、玩家排序列 |
| `options` | `options_bkgrd.bmp` | `OPTIONS` 标题及左侧类别 |
| `options` | `Options_game_x30y110.bmp`, `options_3d_x30y155.bmp`, `options_crew_x30y205.bmp`, `options_sound_x30y255.bmp`, `options_controls_x30y300.bmp`, `options_mulitplayer_x30y350.bmp` | 游戏、3D、乘员、声音、控制、多人 |
| `playerslog` | `PLAYERSLOG_bkgrd.bmp`, `PLAYERSLOG_CAMPAIGN_x030y105.bmp`, `PLAYERSLOG_SINGLE_x030y155.bmp`, `PLAYERSLOG_TRAINING_x030y205.bmp` | 玩家日志、战役、单人、训练 |
| `qmission` | `QuickMission_bkg.bmp` | 快速任务标题及平台、任务类型、随机种子、难度等栏目 |
| `usniref` | `USNIref.bmp`, `x030y105.bmp`, `x030y155.bmp`, `x030y205.bmp` | 海军资料库、文本、照片、3D |

以上界面紧邻主菜单入口，最适合作为下一批静态图汉化。

## 游戏流程界面

| 归档 | 已确认包含英文的图片 | 内容 |
| --- | --- | --- |
| `brief` | `MSBRIEF_BACKGROUND.bmp`, `MSBRIEF_CANCEL_x530y560.bmp`, `MSBRIEF_LOADOUT_x430y560.bmp` | 任务简报、取消、武器挂载 |
| `debrief` | `missiondebrief_bkg.bmp`, `msdebriefreplay_x30y160.bmp`, `msdebriefstatus_x30y110.bmp` | 任务复盘、回放、状态 |
| `wpnloadout` | `WL_BKG.bmp`, `WL_cancel_x530y560.bmp` | 武器挂载标题与取消 |

通用的 `OK` 图标多为勾号，可不急于修改；`CANCEL` 图片含英文，适合统一替换为“取消”或仅保留叉号。

## 多人界面

| 归档 | 已确认包含英文的图片 | 内容 |
| --- | --- | --- |
| `mp_main` | `MP_bkgplain.bmp`, `MP_LB_host_x020y160.bmp`, `MP_LB_join_x020y110.bmp`, `MP_LB_JOIN_box_x190y70.bmp` | 多人标题、创建/加入及房间表头 |
| `mp_gamerm` | `MP_gameroom_bkg.bmp`, `MP_MS_Stations.bmp` | 多人房间标题与站位页面 |
| `mp_gamerm` | `MP_assign_x015y315.bmp`, `MP_brief_x015y170.bmp`, `MP_missions_x015y105.bmp`, `MP_options_x015y280.bmp`, `MP_platselect_x020y110.bmp`, `MP_RP_x015y370.bmp`, `MP_weap_x015y215.bmp` | 分配岗位、简报、任务选择、选项、平台选择、拒绝玩家、武器挂载 |
| `mp_gamerm` | `MP_GR_CREATE_x235y385.bmp`, `MP_GR_JOINLEAVE_x465y385.bmp`, `MP_SEND_x670y505.bmp` | 建队、加入/离队、发送 |

## 编辑器与通用控件

| 归档 | 已确认包含英文的图片 | 内容 |
| --- | --- | --- |
| `missioneditor` | `ME_background.bmp` | `MISSION EDITOR` 标题 |
| `missioneditor` | `newtab.bmp` | `All`, `Group`, `Triggers`, `Side`, `Type`, `Script` 标签 |
| `shared` | `esc_save.bmp`, `esc_saveexit.bmp` | 暂停菜单的保存、保存并退出 |
| `shared` | `esc_end.bmp`, `esc_missionstatus.bmp`, `esc_options.bmp`, `esc_ref.bmp`, `esc_resume.bmp` | 文件名表明同属暂停菜单，建议后续逐张重绘 |

任务编辑器中的对象添加按钮主要以图标表示，不属于优先文字替换目标。

## 暂不优先

- `loading\LOADING_background.bmp` 未观察到可翻译英文，仅为背景与进度条区域。
- `credits\credits.bmp` 为背景图，正文更可能来自同归档的 `credits.doc`。
- `logo\splash.bmp` 含游戏品牌与版权标识，通常保留原样。
- `usnidata` 主要包含大量 `.txt` 数据库正文，它属于文本翻译批次而非静态图片重绘。

## 推荐制作顺序

1. `mis_sel`、`options`、`playerslog`、`qmission`、`usniref`：覆盖主菜单点击后的首层体验。
2. `brief`、`debrief`、`wpnloadout`：形成完整单人任务流程。
3. `mp_main`、`mp_gamerm`：处理多人入口与房间。
4. `missioneditor` 与 `shared` 暂停菜单：最后处理工具与游戏内通用页面。
