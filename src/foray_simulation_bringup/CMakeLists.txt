cmake_minimum_required(VERSION 3.8)
project(foray_simulation_bringup NONE)

find_package(ament_cmake REQUIRED)

install(
    DIRECTORY launch config rviz models
    DESTINATION share/${PROJECT_NAME}
)

install(
    DIRECTORY map
    DESTINATION share/${PROJECT_NAME}
)

install(
    PROGRAMS scripts/make_pcd.py scripts/make_manifest.py scripts/set_initial_pose.py
             scripts/sim_up.sh
    DESTINATION lib/${PROJECT_NAME}
)

if(BUILD_TESTING)
    # 纯 python 断言用原生 ctest（ament_add_test 需要 gtest 风格结果文件）
    enable_testing()

    # A4：清单自洽 + 栅格改 1 字节必须被检出
    add_test(
        NAME manifest_consistency
        COMMAND python3 test/test_manifest.py map/rmul_2027
        WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
    )

    # A5：由网格采样的点云投影 vs 官方地图，占据 IoU 必须 ≥ 0.90
    add_test(
        NAME pcd_align
        COMMAND python3 test/test_pcd_align.py
                --pcd map/rmul_2027/rmul_2027.pcd
                --grid map/rmul_2027/rmul_2027.pgm
        WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
    )
    set_tests_properties(pcd_align PROPERTIES TIMEOUT 120)
endif()

ament_package()
