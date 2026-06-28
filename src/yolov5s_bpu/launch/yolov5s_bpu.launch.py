"""一键启动: Aurora930 相机 + YOLOv5s BPU + 深度标注 + Web 可视化"""

import os, subprocess
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch_ros.actions import Node
from launch.substitutions import TextSubstitution, LaunchConfiguration
from ament_index_python.packages import get_package_prefix


def generate_launch_description():
    # 拷贝 config
    pkg_path = os.path.join(get_package_prefix('yolov5s_bpu'), "lib/yolov5s_bpu")
    os.system(f'cp -rn {pkg_path}/config .')

    config_file_arg = DeclareLaunchArgument(
        'config_file', default_value=TextSubstitution(text='/root/dev_ws/src/config/weaponconfig/yolov5sconfig.json'))
    msg_pub_topic_arg = DeclareLaunchArgument(
        'msg_pub_topic_name', default_value=TextSubstitution(text='hobot_dnn_detection'))

    # Aurora930 相机
    aurora = Node(
        package='deptrum-ros-driver-aurora930',
        executable='aurora930_node',
        namespace='aurora',
        output='screen',
        parameters=[{
            "rgb_enable": True, "ir_enable": False, "depth_enable": True,
            "point_cloud_enable": False, "rgbd_enable": False,
            "ir_fps": 15, "rgb_fps": 15,
            "depth_correction": True, "align_mode": True, "laser_power": 1.0,
            "resolution_mode_index": 2,
            "minimum_filter_depth_value": 150, "maximum_filter_depth_value": 4000,
        }],
    )

    # YOLOv5s BPU
    yolo = Node(
        package='yolov5s_bpu',
        executable='yolov5s_bpu_node',
        name='yolov5s_bpu',
        output='screen',
        parameters=[{
            'config_file': LaunchConfiguration('config_file'),
            'msg_pub_topic_name': LaunchConfiguration('msg_pub_topic_name'),
        }],
        arguments=['--ros-args', '--log-level', 'info'])

    # nginx
    nginx_cmd = './sbin/nginx -p .'
    try:
        running = nginx_cmd.encode() in subprocess.check_output(
            ['ps', 'ax'], stderr=subprocess.DEVNULL)
    except Exception:
        running = False
    if not running:
        web_path = os.path.join(get_package_prefix('websocket'), 'lib/websocket/webservice')
        cwd = os.getcwd()
        os.chdir(web_path)
        os.system(nginx_cmd)
        os.chdir(cwd)

    # Web 可视化
    web = Node(
        package='websocket',
        executable='websocket',
        name='websocket',
        output='screen',
        parameters=[{
            'image_topic': '/image_jpeg',
            'image_type': 'mjpeg',
            'only_show_image': False,
            'output_fps': 0,
            'smart_topic': LaunchConfiguration('msg_pub_topic_name'),
        }],
        arguments=['--ros-args', '--log-level', 'warn'])

    return LaunchDescription([
        config_file_arg, msg_pub_topic_arg,
        aurora, yolo, web,
    ])
