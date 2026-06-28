# 源码编译
## 创建工作空间
mkdir -p ~/dev_ws/src
## 拷贝源码包到~/dev_ws/src目录下并解压，修改解压后的文件名为deptrum-ros-driver
当前目录结构如下图
dev_ws
└── src
    └── deptrum-ros-driver
## stellar400编译
1. `cd ~/dev_ws/src/deptrum-ros-driver`
2. 修改package.xml的包名 `sed -i 's/deptrum-ros-driver/deptrum-ros-driver-stellar400/g' package.xml`,需注意不要重复修改
3. `cd ~/dev_ws`
3. `colcon build --cmake-args -DSTREAM_SDK_TYPE=STELLAR400`
## stellar420编译
1. `cd ~/dev_ws/src/deptrum-ros-driver`
2. 修改package.xml的包名 `sed -i 's/deptrum-ros-driver/deptrum-ros-driver-stellar420/g' package.xml`,需注意不要重复修改
3. `cd ~/dev_ws`
4. `colcon build --cmake-args -DSTREAM_SDK_TYPE=STELLAR420`
## aurora930编译
1. `cd ~/dev_ws/src/deptrum-ros-driver`
2. 修改package.xml的包名 `sed -i 's/deptrum-ros-driver/deptrum-ros-driver-aurora930/g' package.xml`,需注意不要重复修改
3. `cd ~/dev_ws`
4. `colcon build --cmake-args -DSTREAM_SDK_TYPE=AURORA930`
## nebula编译
1. `cd ~/dev_ws/src/deptrum-ros-driver`
2. 修改package.xml的包名 `sed -i 's/deptrum-ros-driver/deptrum-ros-driver-nebula/g' package.xml`,需注意不要重复修改
3. `cd ~/dev_ws`
4. `colcon build --cmake-args -DSTREAM_SDK_TYPE=NEBULA`

## 安装位置
默认安装到~/dev_ws/install/package_name下，如需修改安装目录，编译过程中可加 `--install-base /path/to/install/directory`
## Install Udev
## 如果非root权限用户启动Ros程序时不能枚举到设备，而root权限能枚举到设备时，则需要安装udev（之前安装过的不必重复安装，通过我司提供的deb安装则不必手动安装，deb安装过程中会自动安装），具体安装如下:
1. 打开位于源码包下/ext目录下的sdk包后进入scripts，
scripts/
├── 99-deptrum-libusb.rules
├── install_dependency.sh
└── setup_udev_rules.sh
执行`sh ./setup_udev_rules.sh` 去设置udev权限
2. 安装成功后即可通过普通权限枚举到设置，正常启动

## Aurora 930 相机参数

| 参数 | 值 |
|------|-----|
| 型号 | Aurora 930 (idVendor=3251, idProduct=1930) |
| 固件 | v1.7.2 |
| 接口 | USB 2.0 |

### 分辨率模式

| index | IR | RGB | 深度 |
|-------|-----|-----|------|
| 0 | 320×200, 8bit | 320×200 YUV | — |
| 1 | 480×300, 16bit | 480×300 YUV | — |
| 2 | 640×400, 8bit | 640×400 YUV | 640×400 |

### SDK 库链接修复

```bash
ln -sf libdeptrum_stream_aurora900.so.1.1.22 libdeptrum_stream_aurora900.so
```

### 启动

```bash
ros2 launch deptrum-ros-driver-aurora930 aurora930_launch.py resolution_mode_index:=2
```

### 话题 (命名空间 /aurora)

| 话题 | 类型 | 频率 | 说明 |
|------|------|------|------|
| `/aurora/rgb/image_raw` | Image(BGR8) | ~15Hz | RGB 彩色 640×400 |
| `/aurora/rgb/camera_info` | CameraInfo | — | RGB 内参 |
| `/aurora/depth/image_raw` | Image(16UC1) | ~15Hz | 深度图 mm |
| `/aurora/ir/image_raw` | Image(mono8) | ~15Hz | IR 红外 |
| `/aurora/ir/camera_info` | CameraInfo | — | IR 内参 |
| `/aurora/points2` | PointCloud2 | — | 点云 |