# Copyright 2026 ZQU-Foray
#
# 「点云 → 定位」整链：场地仿真 + 机器人 + gz 桥 + 点云时序修复 + point_lio + foray_localization。
#
# 数据链：
#   gpu_lidar ──桥──> /livox/lidar ──ign_sim_pointcloud_tool──> /velodyne_points ──> point_lio
#                                              └─ 补 time / ring（仿真点云没有逐点时间戳）
#   /aft_mapped_to_init（point_lio 里程计）──> foray_localization 的 odom
#   /livox/lidar（原始点云，帧 front_mid360）──> foray_localization 的 cloud
#
# 定位节点用 `foray_localization_bringup` 自带的兵种参数（sentry.yaml）当基线，
# 只覆盖仿真相关项，避免两处默认值漂移。

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    ExecuteProcess,
    IncludeLaunchDescription,
    OpaqueFunction,
    TimerAction,
)
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare

# 迁移包 parameters.json 的实测雷达安装高度（279.62 mm）
LIDAR_POSE = ("0.08", "0.0", "0.27962", "0.0", "0.0", "0.0")

# ign_sim_pointcloud_tool 按「垂直角 → 环号」重排点，参数必须与传感器视场一致：
# samples=32、-7°…+52°（= -0.12217304764…0.90757121104 rad）→ ang_res_y = 59/31
ANG_RES_Y = "1.903225806451613"


def _initial_pose(context, *args, **kwargs):
    """整链起来后把定位摆到 spawn 位姿（GICP 只吃 0.5 m 内的初值）。"""
    if LaunchConfiguration("set_initial_pose").perform(context) != "true":
        return []
    return [
        TimerAction(
            period=float(LaunchConfiguration("initial_pose_delay").perform(context)),
            actions=[
                Node(
                    package="foray_simulation_bringup",
                    executable="set_initial_pose.py",
                    name="sim_set_initial_pose",
                    output="screen",
                    parameters=[
                        {
                            "x": LaunchConfiguration("x"),
                            "y": LaunchConfiguration("y"),
                            "yaw": LaunchConfiguration("yaw"),
                        }
                    ],
                )
            ],
        )
    ]


def generate_launch_description():
    sim_launch = PathJoinSubstitution(
        [FindPackageShare("foray_simulation_bringup"), "launch", "simulation.launch.py"]
    )
    point_lio_params = PathJoinSubstitution(
        [FindPackageShare("foray_simulation_bringup"), "config", "point_lio_sim.yaml"]
    )
    map_manifest = PathJoinSubstitution(
        [FindPackageShare("foray_simulation_bringup"), "map", "rmul_2027", "manifest.yaml"]
    )
    sentry_params = PathJoinSubstitution(
        [FindPackageShare("foray_localization_bringup"), "config", "sentry.yaml"]
    )

    sim_include = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(sim_launch),
        launch_arguments={
            "headless": LaunchConfiguration("headless"),
            "gui": LaunchConfiguration("gui"),
            "rviz": LaunchConfiguration("rviz"),
            "x": LaunchConfiguration("x"),
            "y": LaunchConfiguration("y"),
            "yaw": LaunchConfiguration("yaw"),
        }.items(),
    )

    # 传感器装在 chassis 上、TF 只由静态发布器给出（SDF 里没有 joint）
    lidar_tf = Node(
        package="tf2_ros",
        executable="static_transform_publisher",
        name="front_mid360_static_tf",
        arguments=["--frame-id", "base_footprint", "--child-frame-id", "front_mid360",
                   "--x", LIDAR_POSE[0], "--y", LIDAR_POSE[1], "--z", LIDAR_POSE[2],
                   "--roll", LIDAR_POSE[3], "--pitch", LIDAR_POSE[4], "--yaw", LIDAR_POSE[5]],
        parameters=[{"use_sim_time": True}],
    )

    cloud_tool = Node(
        package="ign_sim_pointcloud_tool",
        executable="ign_sim_pointcloud_tool_node",
        name="ign_sim_pointcloud_tool",
        output="screen",
        parameters=[
            {
                "pcd_topic": "/livox/lidar",
                "n_scan": 32,
                "horizon_scan": 1875,
                "ang_bottom": -7.0,
                "ang_res_y": float(ANG_RES_Y),
            }
        ],
    )

    point_lio = Node(
        package="point_lio",
        executable="pointlio_mapping",
        name="point_lio",
        output="screen",
        parameters=[point_lio_params],
    )

    localization_params = [
        sentry_params,
        {
            "use_sim_time": True,
            "map_manifest": map_manifest,
            "verify_map_hashes": True,
            # 仿真里点云没有逐点时间戳，定位直接用原始桥出点云；里程计来自 point_lio
            "cloud_topic": "/livox/lidar",
            "odom_topic": "/aft_mapped_to_init",
        },
    ]

    map_server = Node(
        package="foray_localization_ros",
        executable="map_server_node",
        name="foray_map_server",
        output="screen",
        parameters=localization_params,
        condition=IfCondition(LaunchConfiguration("start_map_server")),
    )

    localization = Node(
        package="foray_localization_ros",
        executable="localization_node",
        name="foray_localization",
        output="screen",
        parameters=localization_params,
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument("headless", default_value="false"),
            DeclareLaunchArgument("gui", default_value="false"),
            DeclareLaunchArgument("rviz", default_value="false"),
            DeclareLaunchArgument("x", default_value="6.0"),
            DeclareLaunchArgument("y", default_value="4.0"),
            DeclareLaunchArgument("yaw", default_value="0.0"),
            DeclareLaunchArgument("set_initial_pose", default_value="true"),
            DeclareLaunchArgument("initial_pose_delay", default_value="12.0"),
            DeclareLaunchArgument("start_map_server", default_value="true"),
            sim_include,
            lidar_tf,
            cloud_tool,
            point_lio,
            map_server,
            localization,
            OpaqueFunction(function=_initial_pose),
        ]
    )
