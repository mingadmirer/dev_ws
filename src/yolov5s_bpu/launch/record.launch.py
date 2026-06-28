
"""Aurora930 录制 + Web 预览 — 一键启动"""

import os, subprocess
from launch import LaunchDescription
from launch_ros.actions import Node
from ament_index_python.packages import get_package_prefix


def generate_launch_description():
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

    return LaunchDescription([
        # 相机
        Node(
            package='deptrum-ros-driver-aurora930',
            executable='aurora930_node',
            namespace='aurora',
            output='screen',
            parameters=[{
                "rgb_enable": True, "ir_enable": False, "depth_enable": True,
                "point_cloud_enable": False,
                "ir_fps": 15, "rgb_fps": 15,
                "depth_correction": True, "align_mode": True,
                "resolution_mode_index": 2,
            }],
        ),
        # 录制 + Web 预览
        Node(
            package='yolov5s_bpu',
            executable='record_node',
            name='record_node',
            output='screen',
            parameters=[{'output_dir': '/root/Videos', 'fps': 15.0, 'record': False}],
        ),
        # Web 可视化
        Node(
            package='websocket',
            executable='websocket',
            name='websocket',
            output='screen',
            parameters=[{
                'image_topic': '/image_jpeg',
                'image_type': 'mjpeg',
                'only_show_image': True,
            }],
            arguments=['--ros-args', '--log-level', 'warn'],
        ),
    ])
