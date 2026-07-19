# Tasks

- [x] Task 1: 编写 recovery.img 解包脚本 `repack_recovery.py`，实现 boot image header 解析与 kernel/ramdisk/second/dt 分离
  - [x] SubTask 1.1: 解析 `ANDROID!` header，读取 kernel_size / ramdisk_size / second_size / page_size / dt_size / cmdline 等字段
  - [x] SubTask 1.2: 按 page_size 对齐拆分 kernel、ramdisk、second、dt，分别保存到 `/tmp/recovery_split/` 临时目录
  - [x] SubTask 1.3: 保留原始 header 的 4096 字节（或 page_size 字节）以便重组时复用

- [x] Task 2: 解压 ramdisk 并还原文件树
  - [x] SubTask 2.1: 通过魔数识别 ramdisk 压缩格式（gzip `1f 8b` / lz4 `04 22 4d 18` / xz `fd 37 7a 58 5a` / 未压缩）
  - [x] SubTask 2.2: 用 Python `gzip` / `lzma` 标准库（或 `lz4` 子进程）解压得到 cpio 归档
  - [x] SubTask 2.3: 用 Python 实现 cpio newc 格式解析，把所有 entry 还原到 `/tmp/recovery_ramdisk/`（保留 mode/uid/gid/nlink 等元数据）

- [x] Task 3: 替换 ramdisk 中的 `prop.default`
  - [x] SubTask 3.1: 检查 ramdisk 根目录是否已有 `prop.default`，记录其 mode/uid/gid
  - [x] SubTask 3.2: 用 `/workspace/prop.default` 内容覆盖（或新建）ramdisk 根目录的 `prop.default`，权限沿用原值（新建时用 0644, uid=0, gid=0）
  - [x] SubTask 3.3: 打印替换前后的文件大小与 sha256，方便核对

- [x] Task 4: 重新打包 ramdisk
  - [x] SubTask 4.1: 用 Python 实现 cpio newc 写出，按原 ramdisk 中 entry 的顺序写入所有文件
  - [x] SubTask 4.2: 用与原 ramdisk 相同的压缩格式重新压缩 cpio 归档
  - [x] SubTask 4.3: 校验新 ramdisk 的大小合理（与原大小接近，差异主要来自 prop.default 大小变化）

- [x] Task 5: 重新打包 boot image 并落位
  - [x] SubTask 5.1: 复制原 header 字节，更新 ramdisk_size 字段为新 ramdisk 字节数
  - [x] SubTask 5.2: 按 page_size 对齐拼接 header + kernel + ramdisk + second + dt
  - [x] SubTask 5.3: 用 `file` 命令校验新文件 magic 为 Android bootimg，cmdline 与原文件一致
  - [x] SubTask 5.4: 备份原 `recovery.img` 为 `recovery.img.orig`（仅本次操作期间，避免误覆盖），将新 img 覆盖写入 `/workspace/recovery.img`

- [x] Task 6: 验证
  - [x] SubTask 6.1: 重新解包 `/workspace/recovery.img`，确认 ramdisk 内 `prop.default` 内容与仓库 `prop.default` 一致
  - [x] SubTask 6.2: 确认 `/workspace/recovery.img` 仍可被 `file` 识别为 Android bootimg
  - [x] SubTask 6.3: 确认仓库其它文件（README.md、prop.default、.github/）未被改动

# Task Dependencies
- [Task 2] depends on [Task 1]
- [Task 3] depends on [Task 2]
- [Task 4] depends on [Task 3]
- [Task 5] depends on [Task 4]
- [Task 6] depends on [Task 5]
