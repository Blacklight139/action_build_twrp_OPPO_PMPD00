# Tasks

- [x] Task 1: 修改 `.github/workflows/blank.yml` 的输入参数与设备树生成步骤
  - [x] SubTask 1.1: 把 `IMG_URL` 改为可选（默认空字符串），新增 `BUILD_TWRP` 布尔输入（默认 `false`）
  - [x] SubTask 1.2: Download recovery image 步骤加条件：仅当 `IMG_URL` 非空时才 `wget`，否则直接使用 checkout 出的仓库 `recovery.img`
  - [x] SubTask 1.3: 设备树生成与 release 步骤保持原逻辑（仅输入来源改变），保留 `DeviceTree_<run_number>.zip` 上传到 Release

- [x] Task 2: 在 `blank.yml` 中新增 TWRP 编译 job（`build-twrp`），与设备树 job 解耦
  - [x] SubTask 2.1: 新 job `needs: generate-device-tree`，`if: github.event.inputs.BUILD_TWRP == 'true'`
  - [x] SubTask 2.2: 从上一步 Release（或 artifact）下载 `DeviceTree_<run_number>.zip` 解压得到 device tree
  - [x] SubTask 2.3: 准备 TWRP 编译环境（用 `ubuntu-22.04` runner + 安装 `git-core gnupg flex bison build-essential zip curl zlib1g-dev gcc-multilib ...` 等标准 AOSP 依赖；或直接用社区 docker 镜像如 `docker://runner/twrp-builder`，优先选最小可行方案）
  - [x] SubTask 2.4: Clone 最小化 omni/twrp 源码树（仅 manifest + 当前设备所需项目，用 `--depth=1` 减少 clone 量；目标分支 `twrp-12.1` 或 `twrp-11`，根据 recovery.img 的 Android 11 选 `twrp-11`）
  - [x] SubTask 2.5: 把 device tree 复制到源码树 `device/<vendor>/<model>/`，运行 `source build/envsetup.sh && lunch omni_<model>-eng && mka recoveryimage`
  - [x] SubTask 2.6: 把产物 `out/target/product/<model>/recovery.img` 重命名为 `TWRP_<device>_<run_number>.img`，上传到与设备树相同的 Release（用 `softprops/action-gh-release` 的 `tag_name: dt-<run_number>` 复用同一个 release）

- [x] Task 3: 处理编译失败的降级路径
  - [x] SubTask 3.1: 编译 job 设置 `timeout-minutes: 360`（GitHub Actions 单 job 上限），超时自动 fail
  - [x] SubTask 3.2: 由于设备树 job 与编译 job 解耦，编译失败不影响 device tree release
  - [x] SubTask 3.3: 在编译 job 末尾加 `if: always()` 的诊断步骤，打印 `out/` 下 recovery.img 是否存在、`file` 输出

- [x] Task 4: 更新 `README.md`
  - [x] SubTask 4.1: 在 README 末尾追加一段（不修改已有内容），说明 workflow 现在既生成设备树也编译 TWRP recovery.img
  - [x] SubTask 4.2: 列出两个 Release 资产命名规则：`DeviceTree_<run_number>.zip` 与 `TWRP_<device>_<run_number>.img`
  - [x] SubTask 4.3: 说明如何降级：把 `BUILD_TWRP` 设为 `false` 即只生成设备树；说明编译可能因 6h 超时失败，但设备树仍可下载

- [x] Task 5: 本地静态校验 workflow 语法与 README
  - [x] SubTask 5.1: 用 `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/blank.yml'))"` 校验 YAML 合法
  - [x] SubTask 5.2: `git diff` 确认只改了 `.github/workflows/blank.yml` 与 `README.md`，未动 `recovery.img` / `prop.default` / `repack_recovery.py`

# Task Dependencies
- [Task 2] depends on [Task 1]
- [Task 3] depends on [Task 2]
- [Task 4] 可与 [Task 2] 并行
- [Task 5] depends on [Task 1, Task 2, Task 4]
