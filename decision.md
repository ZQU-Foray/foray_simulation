# decision.md — 关键工程决策

> 只记「改变了实现方向」的决策。每条都要有当时的理由，避免后人重复讨论。

## D1 仿真器口径：Ignition Gazebo Fortress（gz-sim 6），不是 Harmonic

- 参考的 SMBU 系仿真仓（`rmu_gazebo_simulator`）就是 **Humble + Fortress + `gz_version: 6`**，
  上游现成的世界插件组合、`ros_gz_bridge` 话题映射可直接照抄。
- 容器环境实测：`osrf/ros:humble-desktop-full` 自带 ignition-gazebo 6.18、`ros_gz_bridge`、
  `ros_gz_sim`，**无需自建镜像**即可起仿真。
- guodong 迁移包声明的是 Jazzy + Harmonic，**本仓只取它的资产**（网格/地图/复核参数），
  世界文件按 Fortress 重写（插件名前缀 `ignition-gazebo-*`，SDF 1.9 在 sdformat12 下可加载，
  已实测）。
- 代价：Fortress 的 `gpu_lidar` 需要显式加载 `ignition-gazebo-sensors-system`（带 `ogre2`），
  否则**静默不发数据**；世界必须自带 `<light>` 与地面，镜像里没有 `model://sun`。

## D2 官方 STEP 不入库

`source_cad/RMUL2027_3V3_V1.0.0.stp`（1.99 MB）版权归 RoboMaster 官方、仅用于几何审计，
体积也不适合进仓。只保留由它派生的**分件 DAE** 与复核参数（`maps/rmul_2027/*.json`），
获取方式写进 `THIRD_PARTY_NOTICES.md`。

## D3 先验点云由网格自行采样，不用上游网盘 PCD

`pb2025_sentry_nav` 的先验 PCD 不在 git（网盘分发），且是别的赛季场地。本仓改为
`make_pcd.py` 从同包网格表面采样：

- 只用顶点会得到 **166 点**（每个分件 36 个顶点 = 12 个三角形），GICP 完全不够用
  → 必须做**三角面内格点采样**；
- 采样间距 **0.08 m**：5 cm 时 260898 点 / 3.1 MB 过于臃肿，8 cm 得 102433 点 / 1.2 MB，
  且在 2.5 cm 栅格上仍能覆盖围挡全表面；
- 输出为**定长头 + binary** PCD，字段按字典序排列，保证同输入逐字节同哈希（sha256 可复现）。

## D4 A5 的 IoU 判定口径

两条数据链必须互相独立，断言才不是自证：占据图取官方 PGM，点云由网格采样。

- **点云占据**：栅格内存在 `z > 0.02 m` 的点。2 cm 是底盘可通行分界（中央控制区 10 mm、
  补给垫 3 mm 可通行；围挡 420 mm、高地 200 mm、工作台 403 mm、隧道顶 270 mm 记占据）。
- **比较范围**：外场矩形 `(-0.3, -0.3) – (12.3, 8.3)`（内场 12×8 + 0.3 m 围挡）。官方 PGM
  把场外 0.1 m 余量也标成占据，点云不含该区域，不排除会系统性拉低约 12% IoU。
- **表面膨胀**：点投影按采样半径 `spacing/2 = 0.04 m` 膨胀，否则 0.3 m 厚围挡上只留 7 行点，
  IoU 会掉到 0.22（首轮实测）。
- 结果：**IoU 0.9331 / 召回 0.9777 / 精确 0.9534**，门槛 0.90。

## D5 manifest 与栅格/PCD 同目录

`foray_localization` 的地图加载按 `manifest 目录 / 字段值` 定位文件，`pcd_file` / `grid_file`
必须是相对路径且不含 `..`。因此地图目录固定为 `map/rmul_2027/`，`make_manifest.py` 只负责
读 nav2 yaml 的 `image/resolution/origin`、读 PGM 尺寸、算两个 sha256，**不猜、不手填**。

## D6 只交付一个 canonical 世界

迁移包提供 `rmul_2027.sdf` / `_preview` / `_native` / `_native_preview` 四个变体。调试变体
（内联模型、preview 机器人）不入库：世界只有一份，差异靠 launch 参数与 `visual_quality`
表达，避免四份世界各自漂移。

## D7 本仓层级为 META

仿真属于工具链，不在算法六层里。`.foray-layer` 声明 `layer: META`、`depends_on_layers: []`，
与 `foray_ws` 一致；它**运行时**依赖 `foray_localization` 的可执行文件，但不链接其代码，
因此不构成层级依赖。

## D8 点云与 IMU 的仿真口径

- **线数与视场**：`<vertical><samples>32</samples>-0.12217304764…0.90757121104</vertical>`
  （-7°…+52°）、`<horizontal><samples>1875</samples>±π</horizontal>`，取自
  `pb2025_robot_description` 的 `resource/models/mid360/model.sdf.xmacro`（上游 pin 注解见
  `THIRD_PARTY_NOTICES.md`）。Fortress 的 `gpu_lidar` 支持 32 线，实测 `height=32`、
  `width=1875`、`point_step=32`，字段 `x/y/z/intensity(FLOAT32)/ring(UINT16)`。
- **nominal 10 Hz 而非 20 Hz**：Livox MID-360 默认出点率 10 Hz；`update_rate=20` 只会让渲染
  线程更吃力而不增加信息量。软件渲染（`LIBGL_ALWAYS_SOFTWARE=1`）下实测 6.8–7.2 Hz，
  与 RTF ≈ 0.7 一致；GPU 直通环境应达 10 Hz。因此 A1 的门槛按 normal 10 Hz 写，
  CI 只保证 ≥ 6.5 Hz。
- **IMU 必须靠 `imu-system`**：世界只加载 `sensors-system` 时 `gpu_lidar` 正常、`imu` 话题
  却根本不出现（连 `ign topic -l` 都查不到，`ros_gz_bridge` 也不报错——它按需懒订阅）。
  世界必须同时加载 `ignition-gazebo-imu-system`。`test_field_assets.py` 已把这条写成断言。
- **机器人本体不建轮系**：用 `ignition-gazebo-velocity-control` 平面速度控制，Nav2 直接给
  `/cmd_vel`；真实底盘的运动学差异不在「点云→定位→寻路」这条链路的验证范围内。

## D9 I6 暂停：上游 point_lio 在本仿真里收不到数据

**现象**：`point_lio` 进程存活、`ros2 topic info` 显示它订阅了 `/velodyne_points`（BEST_EFFORT）
与 `/livox/imu`、也是 `/aft_mapped_to_init` 的发布者，但插桩后 `sync_packages`
一秒不停打印 `lidar_buf=0 imu_deque=0 imu_en=1 last_imu=-1.000`——**两个回调从未被调用**，
`/aft_mapped_to_init` 一帧都没有，`foray_localization` 因此 `pose_valid=false`、A2 无从取证。
同一时刻同一个容器里，`foray_localization` 的 `map_server_node` 能正常加载地图、
python 探针能收到同两条话题的数据。

**已排除**（每条都实测过，回执见 `local/evidence-sim/i6-point-lio-blocker.txt`）：
- 节点名未 remap → 直接 segfault：`ros2 run point_lio pointlio_mapping` 时 YAML 的
  `point_lio:` 段不生效，`prior_pcd.enable` 回默认真值、`prior_pcd_map_path` 为空字符串，
  加载空路径崩溃。**跑 point_lio 必须 `-r __node:=point_lio`**（或走 launch）。
- 参数未生效：`ros2 param get` 逐项确认 `common.lid_topic=velodyne_points`、
  `common.imu_topic=livox/imu`、`preprocess.lidar_type=2`、`use_sim_time=True`、
  `prior_pcd.enable=False`。
- 点云里的 `inf`：仿真顶棚开放，约 79% 回波是 ±inf；用一个只保留有限点的调试节点过滤后
  再喂给它，**仍然没有回调**。
- 执行器：把 `executor.spin_some()` 换成 `rclcpp::spin_some(nh)` 报
  `Node '/point_lio' has already been added to an executor`（证明节点确实在 executor 里），
  换成「专用线程 `executor.spin()`」也仍然是零回调。

**三条备选路线**（下一步从这里挑一条，不在本次范围内）：
1. 继续查上游（可能是 RMW 事件队列 / `spin_some` 在 Humble 多线程 executor 上的行为，
   或需要打成 component 交给容器 spin）。
2. 换里程计源：`rmoss_gz_base` 或 `ignition-gazebo-odometry-publisher-system` 出 odom。
   代价是 A2 退化成「真值输入 + GICP 微调」，验收力度变弱。
3. 路线 2 + 一个几十行的漂移注入节点，让 GICP 真的需要纠偏，A2 仍有效。

**本次决定**：先停在这里，把 I1–I5 交付干净（资产 / PCD / manifest / 机器人 / 桥 / 点云时序），
I6–I8 留待下一轮；`localization_sim.launch.py` 与 `point_lio_sim.yaml` 保留在树里，
它们是下一个接手者直接可用的起点。

## D10 摆位必须用 MODE_GEOMETRIC

`foray_localization` 的 `/localization/relocalize` 服务有两个模式：`MODE_GEOMETRIC=0`、
`MODE_PLACE=1`。本仓 `scripts/set_initial_pose.py` 必须用 **MODE_GEOMETRIC**：用 MODE_PLACE
会被拒（`place 后端默认关闭（D10）；请使用 MODE_GEOMETRIC 给定初值`），仿真里没有 place 后端。
服务名是**绝对名** `/localization/relocalize`（不是 `/foray_localization/relocalize`）。
