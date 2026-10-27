# plan.md — 计划与进度

> 状态：`[x]` 已完成并有可追溯回执 · `[~]` 进行中 · `[ ]` 未开始。
> 任意时刻中断后从这里恢复。

## 当前断点（2026-10-27）

**I1–I5 完成，I6 因上游 `point_lio` 在本仿真里收不到数据而暂停，I6–I8 未做。**
决策与证据见 `decision.md` D9 与 `foray_localization/local/evidence-sim/`
（后者在 `foray_localization` 的 `.gitignore` 范围内，随那个仓归档）。

## M1 场地资产（A0 / A5 的一半）

- [x] **I1 迁移包落盘与自检**：解包 70 文件、`verify_package.py` → `PASS: 69 package files verified`、
      `tools/test_rmul_field.py` → 5 tests OK。
- [x] **I2 新仓骨架与文档**：`README.md` / `AGENTS.md` / `tree.md` / `plan.md` / `decision.md` /
      `THIRD_PARTY_NOTICES.md` / `.foray-layer`(META) / `.gitignore`。
- [x] **I3 场地资产移植**：`src/foray_rmul_2027_field` 成形；世界改为 Fortress 口径
      （`ignition-gazebo-*` 四插件 + `sensors` 带 `ogre2` + 自带 `directional` 光），容器内
      `ign model --list` 见 `rmul_2027`、话题 `/clock` 正常、日志无错误；
      `test/test_field_assets.py` 在 `colcon test` 里通过。

## M2 地图与定位契约（A4 / A5）

- [x] **I4 PCD + manifest**：
      `scripts/make_pcd.py` 三角面格点采样 0.08 m → 102433 点 / 1229370 字节；
      `scripts/make_manifest.py` 生成 `map/rmul_2027/manifest.yaml`（pcd sha256 `7915f37f…fdc775`、
      grid sha256 `cbc170a5…31801`）；
      `test/test_pcd_align.py` → **IoU 0.9331**（门槛 0.90）；
      `test/test_manifest.py` → PASS；
      容器内用真实 `foray_localization` 验证：正例 `地图版本 1.0.0，102433 点，栅格 512x352`，
      篡改 1 字节后 `栅格 sha256 不匹配`。

## M3 机器人 / 桥 / 点云时序（A1）

- [x] **I5 机器人模型、桥、点云时序**（代码与 A1 取证完成）：
      - `models/foray_sim_robot/model.sdf`：`base_footprint` + `chassis` + `front_mid360`，
        `gpu_lidar`（1875×32、-7°…+52°、`update_rate` 10）+ `imu`（200 Hz），
        平面运动用 `ignition-gazebo-velocity-control-system`（不建轮系）。
      - `config/bridge.yaml`：`/clock`、`/livox/lidar`、`/livox/imu`、`/cmd_vel`、`/sim/pose_info`。
      - `launch/simulation.launch.py`：`ros_gz_sim` + `create` + `parameter_bridge` +
        `robot_state_publisher` + 可选 rviz/gui；`scripts/sim_up.sh` 是它的薄封装。
      - A1 实测（`osrf/ros:humble-desktop-full`，headless，软件渲染）：话题全部出现；
        点云 `height=32`、`width=1875`、`point_step=32`、字段 `x/y/z/intensity/ring`；
        `/velodyne_points` 7.85 Hz、`/livox/lidar` 约 7 Hz，与 RTF ≈ 0.7 一致（见 D8）。

## M4 定位 / 寻路 / 一键（A2 / A3 / A6）

- [ ] **I6 定位链路**（**阻塞**，见 D9）：`config/point_lio_sim.yaml`、
      `launch/localization_sim.launch.py`、`scripts/set_initial_pose.py` 已写好；
      静态 TF、地图加载（`先验地图已加载: version=1.0.0 pcd=4137 grid=512x352`）、
      `/localization/state` 发布均实测通。**卡点**：`point_lio` 的回调不触发，
      `/aft_mapped_to_init` 无输出，`foray_localization` 拿不到先验运动、`pose_valid=false`。
      解掉这一点后 A2 才能取证（10 s 内状态 OK、误差 < 0.30 m / < 5°）。
- [ ] **I7**：`config/nav2_params_sim.yaml` + `launch/navigation_sim.launch.py` + 把
      `scripts/sim_up.sh` 扩成「仿真 + 定位 + Nav2」一键；验收：Nav2 穿过隧道 `SUCCEEDED`、
      `sim_up.sh` 300 s 内起整链（A3 / A6）。
- [ ] **I8**：跨仓收尾——`foray_ws/.repos` 增 `foray_simulation`，`foray_docs`
      §6.6 加 scope 词表、`repository_structure.md` 补仓列表，`foray_localization/decision.md`
      的 D17 一并提交。

## 阻塞与待确认

- **I6 阻塞：`point_lio` 回调不触发**。已排除：节点名未 remap（会直接 segfault）、
  参数未生效、点云含 `inf`、`ros2 run` 与 `launch` 的差异、
  `MultiThreadedExecutor::spin_some` 与专用 spin 线程。`ros2 topic info` 显示它确实是订阅者、
  QoS 匹配，同一份数据别的节点能收到。下一步按 `decision.md` D9 的三条路线之一继续。
- 新仓当前落在 `foray_localization/local/staging/foray_simulation`（`local/` 已 gitignore，
  嵌套 git 仓安全）。**迁到 `../foray_simulation` 需要一次 danger-full-access 审批**；
  迁移用 `git clone ./local/staging/foray_simulation ../foray_simulation` 可保留本仓历史。

## 复现命令

```bash
# 单元级（不需要仿真环境）
colcon build --packages-select foray_rmul_2027_field foray_simulation_bringup
colcon test  --packages-select foray_rmul_2027_field foray_simulation_bringup
colcon test-result --all      # 期望 0 errors 0 failures

# 仿真（需要派生镜像）
docker build -t foray_sim:humble-fortress docker/
ros2 launch foray_simulation_bringup simulation.launch.py headless:=true
```
