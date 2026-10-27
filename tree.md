# tree.md — 目录结构与职责

仓根即 colcon 空间根，包一律在 `src/` 下。

```
foray_simulation/
├── README.md                     # 本仓唯一需求来源
├── AGENTS.md                     # AI / 协作者规范
├── THIRD_PARTY_NOTICES.md        # 三方来源与许可证归属链
├── tree.md  plan.md  decision.md # 结构 / 计划 / 决策
├── .foray-layer                  # 层级声明（META）
├── .gitignore  .clang-format  .github/
└── src/
    ├── foray_rmul_2027_field/            # 场地资源包（纯资产，无运行时节点）
    │   ├── package.xml                   #   ament_cmake，exec_depend ros_ign_gazebo
    │   ├── CMakeLists.txt                #   安装 models/worlds/maps/docs/previews
    │   ├── models/rmul_2027/             #   model.config + model.sdf + meshes/ + materials/
    │   ├── worlds/rmul_2027.sdf          #   唯一交付的世界（Fortress 口径）
    │   ├── maps/rmul_2027/               #   官方 PGM + nav2 YAML + STEP 复核参数
    │   ├── docs/                         #   场地规格、STEP 审计报告、机器校验记录
    │   ├── previews/                     #   场地预览图（文档用，不参与运行）
    │   ├── tools/                        #   上游生成/审计脚本（只读参考，不安装）
    │   └── test/test_field_assets.py     #   资源断言：插件前缀、地图几何、网格可解析
    └── foray_simulation_bringup/         # 启动层：把仿真器接到本仓算法上
        ├── package.xml                   #   ament_cmake
        ├── CMakeLists.txt
        ├── launch/                       #   世界 / 机器人 / 定位 / 寻路 的 launch
        ├── config/                       #   桥接配置、Nav2 参数、世界-机器人位姿表
        ├── rviz/                         #   仿真用 RViz 视图
        ├── map/rmul_2027/                #   定位侧输入：PCD + PGM + manifest.yaml
        ├── scripts/
        │   ├── make_pcd.py               #   场地网格 → 先验点云（三角面格点采样）
        │   ├── make_manifest.py          #   地图目录 → manifest.yaml（含 sha256）
        │   └── sim_up.sh                 #   一键起整链
        └── test/
            ├── test_pcd_align.py         #   A5：点云投影 vs 官方地图 IoU
            └── test_manifest.py          #   A4：清单契约 + 篡改检测
```

## 职责边界

| 目录 | 职责 | 不做什么 |
|---|---|---|
| `foray_rmul_2027_field` | 场地几何、材质、地图基准、场地规格文档 | 不放 launch、不写节点 |
| `foray_simulation_bringup` | 世界组装、机器人 spawn、桥接、参数、一键脚本 | 不实现定位/导航算法（那是 `foray_localization` / `foray_navigation`） |
| `map/rmul_2027` | 定位侧先验（点云 + 栅格 + 清单） | 不做运行时修改；重新生成靠脚本 |
| `tools/`（field 包内） | 上游资产生成与审计脚本，供追溯 | 不被安装、不被运行时依赖 |
