# 用仓库 recovery.img 生成 TWRP 设备树并编译 TWRP recovery.img Spec

## Why
仓库现有 `.github/workflows/blank.yml` 仅通过外部 URL 下载 recovery.img 后用 `twrpdtgen` 生成 TWRP 设备树。用户希望：(1) 直接使用仓库内已有的 `recovery.img` 作为输入（无需外部直链）；(2) 在生成设备树之后进一步真正编译出一个可刷入的 TWRP recovery.img，并发布到 Release。这样最终产物既有 device tree zip 也有可刷的 TWRP recovery.img。

## What Changes
- **BREAKING** 修改 `.github/workflows/blank.yml`：把 `IMG_URL` 输入参数从必填改为可选（保留以兼容外部链接），默认直接使用仓库根目录的 `recovery.img`，不再用 `wget` 下载。新增一个 `BUILD_TWRP` 布尔输入，控制是否继续走真正编译步骤。
- 新增 `.github/workflows/build_twrp.yml`（或在 `blank.yml` 中新增第二个 job）：在生成 device tree 后，clone 最小化 TWRP/omni 源码树（基于 docker 镜像或 `aosp` 镜像，仅 arm64 + 当前设备），把 device tree 放入 `device/<vendor>/<model>/`，执行 `source build/envsetup.sh && lunch && mka recoveryimage`，把产物 `recovery.img` 重命名为 `TWRP_<device>_<run_number>.img` 上传到 Release。
- 新增 `.github/workflows/` 下的辅助脚本（如 `scripts/prepare_twrp_build.sh`）：把 device tree 复制到源码树正确位置、注入 prop.default 相关 fixup（按 README 提示：低版本安卓加 `ro.product.first_api_level`、OPPO 设备合并 build.prop 到 prop.default——这些已由前一个 spec 在镜像层面解决，编译时 device tree 内的 `*.prop` 也需保持一致）。
- README 末尾追加一段说明：现在 workflow 既生成 device tree 也编译 TWRP recovery.img，并提示用户如果编译 job 超时如何降级到仅生成 device tree。
- 不修改 `/workspace/recovery.img`、`/workspace/prop.default` 本身（它们是输入产物，由前一个 spec 处理）。

## Impact
- Affected specs:
  - `replace-recovery-prop`：本 spec 依赖前一个 spec 的产物（已注入 prop.default 的 recovery.img）作为编译输入，但不修改它。
- Affected code:
  - `.github/workflows/blank.yml`（修改输入默认值、新增 build job 或拆分 workflow）
  - 新增 `.github/workflows/build_twrp.yml`（如选择拆分）
  - 新增 `scripts/prepare_twrp_build.sh`（如需）
  - `README.md`（追加说明，不重写）

## ADDED Requirements

### Requirement: 使用仓库内 recovery.img 作为输入
workflow SHALL 优先使用仓库根目录的 `recovery.img` 作为 TWRP 设备树生成与编译的输入；当且仅当用户在 `IMG_URL` 输入框中显式填入了非空 URL 时，才下载该 URL 覆盖仓库内 `recovery.img`。

#### Scenario: 用户未填 IMG_URL
- **WHEN** workflow 触发时 `IMG_URL` 为空或等于默认占位值
- **THEN** 直接使用 checkout 出来的 `/workspace/recovery.img`，不执行 `wget`

#### Scenario: 用户填了 IMG_URL
- **WHEN** 用户在 `IMG_URL` 输入框填入有效直链
- **THEN** `wget` 下载覆盖 `recovery.img`，后续步骤使用下载后的文件

### Requirement: 生成 TWRP 设备树
workflow SHALL 调用 `twrpdtgen` 处理 `recovery.img`，输出 device tree 到 `device_tree_output/`，并打包成 `DeviceTree_<run_number>.zip` 上传到 Release。此步骤行为与原 workflow 一致，仅输入来源改变。

#### Scenario: 设备树生成成功
- **WHEN** `recovery.img` 是合法 Android boot image 且 ramdisk 可解包
- **THEN** `device_tree_output/` 下出现 `AndroidProducts.mk`、`Android.mk`、`<vendor>/<model>/` 目录树，并成功打 zip 上传到 Release

### Requirement: 编译 TWRP recovery.img
当 `BUILD_TWRP` 输入为 true 时，workflow SHALL 在设备树生成后初始化 TWRP 编译环境，把 device tree 注入源码树，编译出 `recovery.img`，重命名为 `TWRP_<device>_<run_number>.img` 并上传到同一个 Release。

#### Scenario: 编译成功
- **WHEN** `BUILD_TWRP=true` 且编译在 runner 资源/时限内完成
- **THEN** Release 中新增 `TWRP_<device>_<run_number>.img`，且 `file` 命令识别为 Android bootimg

#### Scenario: 编译超时或失败
- **WHEN** 编译 job 因 6h 超时或源码树问题失败
- **THEN** device tree zip 仍然在 Release 中可下载（两个 job 解耦，编译失败不影响设备树 release）；workflow run 标记为 failed 但用户已能得到 device tree

### Requirement: 两阶段解耦
设备树生成 job 与 TWRP 编译 job SHALL 通过 Release 资产（或 artifact）解耦：编译 job 依赖设备树 job 的产物，但设备树 job 不依赖编译 job。这样即便编译超时，用户也能拿到设备树。

#### Scenario: 编译 job 失败
- **WHEN** 编译 job 失败或被取消
- **THEN** 设备树 job 仍为 success，Release 中仍包含 `DeviceTree_<run_number>.zip`

### Requirement: README 更新
README 末尾 SHALL 追加一段（不修改已有内容），说明当前 workflow 既生成设备树也编译 TWRP recovery.img，并列出两个 Release 资产的命名规则与降级方式（把 `BUILD_TWRP` 设为 false 即可仅生成设备树）。

#### Scenario: 用户查看 README
- **WHEN** 用户打开 README
- **THEN** 能看到新增段落，明确两个产物的文件名与如何关闭编译步骤

## MODIFIED Requirements

### Requirement: blank.yml 输入参数
原 `IMG_URL` 为必填、默认值为外部 GitHub raw 链接。修改为：可选（默认空字符串），且新增 `BUILD_TWRP` 布尔输入（默认 `false`，避免无意义消耗 runner 配额）。`LIBRARY_NAME` 保持不变。

#### Scenario: 默认触发
- **WHEN** 用户直接点 Run workflow 不改任何输入
- **THEN** `IMG_URL` 为空 → 使用仓库内 `recovery.img`；`BUILD_TWRP` 为 false → 只生成设备树

## REMOVED Requirements
（无）
