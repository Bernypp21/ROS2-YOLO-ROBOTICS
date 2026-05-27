'''
The purpose of this file is launch ros with all the configuration, robot, and world models
'''


import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node


def generate_launch_description():

    # including name for package located in the package.xml
    package_name='my_robot_description'

    #launching rsp file
    rsp = IncludeLaunchDescription(
            PythonLaunchDescriptionSource([os.path.join(
                    get_package_share_directory(package_name), 'launch','rsp.launch.py'
                    )]), launch_arguments={'use_sim_time': 'true'}.items()
    )
    #launching gazebo provided by gazebo ros package
    ros_bridge = Node( 
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=[
       # Camera bridge (Host -> Docker) notice bracket placemnet 
            '/robot/camera/image@sensor_msgs/msg/Image[gz.msgs.Image',
            '/camera/camera_info@sensor_msgs/msg/CameraInfo[gz.msgs.CameraInfo',
            
            # Control bridge (Docker -> Host) notice ] is for docker to hsot
            '/cmd_vel@geometry_msgs/msg/Twist]gz.msgs.Twist',     
            
            # Odometry bridge (Gazebo -> ROS 2)
            # Notice the '[' character indicating flow direction from Gazebo to ROS
            '/odom@nav_msgs/msg/Odometry[gz.msgs.Odometry',
            
            # Transform bridge (Gazebo -> ROS 2)
            # Required so robot TF transforms are updated in Rviz
            '/tf@tf2_msgs/msg/TFMessage[gz.msgs.Pose_V'
        ],
        output='screen',
        parameters=[{'use_sim_time':True}]
    )

    yolo_node = Node(
        package='my_yolo_detector',
        executable='yolo',
        name='yolo',
        output='screen',
        parameters=[{'use_sim_time':True}]
    )
    
    # launching all of them togethor
    return LaunchDescription([
        rsp,
        ros_bridge,
        yolo_node,
    ])


