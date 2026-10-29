#!/usr/bin/env bash
# 一键起整链：仿真 → 定位 → 寻路（I7 完成后接通定位与 Nav2；当前只起仿真+桥）。
set -o pipefail

usage() {
    echo "用法: sim_up.sh [--gui] [--rviz] [--x X] [--y Y] [--yaw RAD]"
    exit 1
}

gui=false
rviz=false
x=0.0
y=0.0
yaw=0.0
while [[ $# -gt 0 ]]; do
    case "$1" in
        --gui) gui=true; shift ;;
        --rviz) rviz=true; shift ;;
        --x) x="$2"; shift 2 ;;
        --y) y="$2"; shift 2 ;;
        --yaw) yaw="$2"; shift 2 ;;
        *) usage ;;
    esac
done

exec ros2 launch foray_simulation_bringup simulation.launch.py \
    gui:="$gui" headless:="$([[ $gui == true ]] && echo false || echo true)" \
    rviz:="$rviz" x:="$x" y:="$y" yaw:="$yaw"
