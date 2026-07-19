# TWRP Device Tree生成工具
- 这个工具怎么用？
- 1.首先你要搞到你的设备任意一个可以开机系统的
- boot.img AB分区 
- recovery.img 除了AB分区以外的所有分区 

-----

- 2.将这个仓库fork到你的用户名下

-----

- 3.将recovery.img或boot.img上传至一个可以提供直链下载的位置，这里我推荐直接将img文件上传至这个仓库，然后点进去点view raw，来获取直链

-----

- 4.点击actions － make twrp device － run workflow，然后在那个链接框里面输入你刚刚获取的直链

-----

 - 5、填写完成后点击 'Run workflow' 开始运行

-----
## 编译结果
- 可以在 [Release](../../releases) 下载


注意：
- 1.如果安卓版本低于9.0，需要手动解包recovery.img并在defxx.prop内添加  
- ro.product.first_api_level=23 #安卓api版本号，如安卓6.0是23  
- 2.如果你的设备是oppo，且出现了AssertionError: Property ro.product.system.device could not be found in build.prop  
- system/build.prop和vendor/build.prop的内容一起合并到/prop.default然后打包生成    

-----

## 直接使用仓库内 recovery.img 并编译 TWRP
- 现在 workflow 支持两种 recovery.img 输入方式：
  - 默认：直接使用仓库根目录下已上传的 `recovery.img`（无需再手动获取 raw 直链）
  - 可选：在 `IMG_URL` 输入框填入外部直链，会覆盖仓库内文件

- 新增 `BUILD_TWRP` 布尔输入（默认 `false`）：
  - 不勾选（默认）：只运行设备树生成 job，产物为 `DeviceTree_<run_number>.zip`
  - 勾选 `true`：在设备树生成完成后，额外运行 build-twrp job，clone minimal-manifest-twrp 的 `twrp-11` 源码树，注入设备树后执行 `mka recoveryimage`，产物为 `TWRP_<device>_<run_number>.img`，上传到同一个 Release

- Release 资产命名规则：
  - 设备树：`DeviceTree_<run_number>.zip`
  - 可刷 TWRP 镜像：`TWRP_<device>_<run_number>.img`（`<device>` 由设备树内 `AndroidProducts.mk` 自动推断）

- 降级与超时说明：
  - build-twrp job 设置了 `timeout-minutes: 360`（GitHub Actions 单 job 上限），超时自动失败
  - 设备树 job 与编译 job 通过 Release 解耦：即使 build-twrp 失败/超时，`DeviceTree_<run_number>.zip` 仍然可从 Release 下载
  - 如仅需设备树，把 `BUILD_TWRP` 保持 `false` 即可
