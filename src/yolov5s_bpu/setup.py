from setuptools import setup, find_packages

package_name = 'yolov5s_bpu'

setup(
    name=package_name,
    version='1.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch',
            ['launch/yolov5s_bpu.launch.py',
             'launch/record.launch.py']),
        ('lib/' + package_name + '/config/redconfig',
            ['config/redconfig/yolov5workconfig.json',
             'config/redconfig/custom.list',
             'config/redconfig/converted_model.bin']),
        ('lib/' + package_name + '/config/weaponconfig',
            ['config/weaponconfig/yolov5workconfig.json',
             'config/weaponconfig/custom.list',
             'config/weaponconfig/converted_model.bin']),
        ('lib/' + package_name + '/config/blueconfig',
            ['config/blueconfig/yolov5workconfig.json',
             'config/blueconfig/custom.list',
             'config/blueconfig/converted_model.bin']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='user',
    maintainer_email='user@example.com',
    description='YOLOv5s object detection with Horizon RDK X5 BPU acceleration',
    license='Apache License 2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'yolov5s_bpu_node = yolov5s_bpu.yolov5s_bpu_node:main',
            'record_node = yolov5s_bpu.record_node:main',
        ],
    },
)
