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
