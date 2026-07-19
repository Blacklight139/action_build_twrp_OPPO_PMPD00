# 替换 recovery.img 内 prop 文件 Spec

## Why
仓库 README 最后两段说明：OPPO 设备出现 `Property ro.product.system.device could not be found in build.prop` 时，需要把 `system/build.prop` 和 `vendor/build.prop` 的内容合并到 `/prop.default` 然后重新打包 recovery.img；安卓版本低于 9.0 时还需在 prop 中加入 `ro.product.first_api_level=23`。仓库已经准备好合并后的 `prop.default`，需要把它注入到 `recovery.img` 的 ramdisk 中并重新打包，供后续 TWRP 设备树生成工作流使用。

## What Changes
- 解包 `recovery.img`：分离 Android boot header / kernel / ramdisk / second / dt，并解压 ramdisk（cpio + gzip/lz4/lzma 之一）。
- 在解出的 ramdisk 文件系统中定位 prop 相关文件（至少包括 `prop.default`、`system/build.prop`、`vendor/build.prop`、`default.prop` 等，按 ramdisk 中实际存在的为准）。
- 用仓库根目录下的 `prop.default` 内容覆盖 ramdisk 中的 `prop.default`（若不存在则在 ramdisk 根目录创建）；其它 prop 文件保持不变，除非 README 步骤要求合并。
- 重新打包 ramdisk（cpio + 原始压缩格式），并使用原 boot header 的所有参数重新拼装 `recovery.img`，保证 `ANDROID!` magic、page_size、kernel/ramdisk 偏移、cmdline 等字段与原文件一致。
- 新生成的 `recovery.img` 覆盖放置在仓库根目录，替换原文件（或生成 `recovery.new.img` 后重命名覆盖，最终路径仍为 `/workspace/recovery.img`）。
- 整个解包/打包过程使用脚本实现，不依赖未安装的 `mkbootimg`/`magiskboot`/`unpackbootimg` 等外部工具，仅用 Python3 标准库 + 系统已安装的 `gzip`/`lzma`/`zip`/`unzip` 完成。

## Impact
- Affected specs: 无（本仓库目前无其它 spec）。
- Affected code:
  - `/workspace/recovery.img`（被替换为新打包版本）
  - 新增打包脚本（临时，可放在 `/workspace/` 下，如 `repack_recovery.py`，任务结束后保留以备复用）
  - `/workspace/prop.default`（只读输入，不修改）

## ADDED Requirements
### Requirement: 解包 recovery.img
系统 SHALL 能够读取 `/workspace/recovery.img`，解析 Android boot image header（magic `ANDROID!`），按 page_size 对齐拆分出 kernel、ramdisk、second、dt（dt_size 字段在新版 header 中可能是 recovery_dtbo_size，按实际 header 处理），并保留原始 header 字节以便重组。

#### Scenario: 标准格式 boot image
- **WHEN** 输入文件 magic 为 `ANDROID!`，page_size 为 4096
- **THEN** 输出 kernel、ramdisk、second、dt 四段原始二进制，且偏移按 page_size 对齐

### Requirement: 解压 ramdisk
系统 SHALL 自动识别 ramdisk 的压缩格式（gzip / lz4 / lzma / xz / 未压缩），解压后得到 cpio 归档；再从 cpio 归档中还原出 ramdisk 文件树（不依赖系统 `cpio` 命令，必要时用 Python 实现 cpio 解析）。

#### Scenario: gzip 压缩的 ramdisk
- **WHEN** ramdisk 前 2 字节为 `1f 8b`
- **THEN** 使用 gzip 解压，得到 cpio newc 格式归档

#### Scenario: lz4 压缩的 ramdisk
- **WHEN** ramdisk 前 4 字节为 lz4 magic `04 22 4d 18`
- **THEN** 若系统无 `lz4` 命令，则报错并提示需要安装 lz4；否则使用 lz4 解压

### Requirement: 替换 prop 文件
系统 SHALL 用仓库根目录的 `prop.default` 内容替换 ramdisk 中已有的 `prop.default`；若 ramdisk 中不存在该文件，则在 ramdisk 根目录新增 `prop.default`，权限 0644、uid/gid 0/0。

#### Scenario: ramdisk 中已存在 prop.default
- **WHEN** 解包后 ramdisk 根目录存在 `prop.default`
- **THEN** 用仓库 `prop.default` 内容覆盖，文件权限/属主保持原值

#### Scenario: ramdisk 中不存在 prop.default
- **WHEN** 解包后 ramdisk 根目录不存在 `prop.default`
- **THEN** 在 ramdisk 根目录创建 `prop.default`，内容来自仓库 `prop.default`，权限 0644，uid=0，gid=0

### Requirement: 重新打包 ramdisk
系统 SHALL 将修改后的 ramdisk 文件树按原 cpio 格式（newc）重新归档，并使用与原 ramdisk 相同的压缩算法重新压缩。

#### Scenario: 原 ramdisk 为 gzip
- **WHEN** 原始 ramdisk 是 gzip 压缩
- **THEN** 新 ramdisk 同样用 gzip 压缩，magic 与原文件一致

### Requirement: 重新打包 boot image
系统 SHALL 用原始 header 字节重建 boot image：kernel、ramdisk、second、dt 按原 page_size 对齐拼接，header 中的 size 字段更新为新 ramdisk 的实际大小，其它字段（magic、cmdline、地址、tags、page_size 等）保持不变。

#### Scenario: 成功重组
- **WHEN** 新 ramdisk 准备就绪
- **THEN** 输出文件以 `ANDROID!` 开头，page_size=4096，cmdline 与原文件一致，新文件可被 `file` 命令识别为 Android bootimg

### Requirement: 输出文件落位
系统 SHALL 将重新打包后的 img 文件覆盖写入 `/workspace/recovery.img`，文件大小、boot header 与原始文件不同（因 ramdisk 内容变化）但结构合法。

## MODIFIED Requirements
（无）

## REMOVED Requirements
（无）
