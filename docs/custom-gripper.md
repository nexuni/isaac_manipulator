# Use a Custom Gripper

The [upstream repository](https://github.com/NVIDIA-ISAAC-ROS/isaac_manipulator) and the tutorial support robot type of ur5e and ur10e, and gripper type of robotiq-2f-85/140. We made some edition to make the whole pipeline also applicable with robotiq-hande. This is the documentation recording all of the steps.

Some content of this README is also shown in [Tutorial for Integrating Custom Manipulators with cuMotion](https://nvidia-isaac-ros.github.io/concepts/manipulation/cumotion_moveit/tutorial_custom_manipulator.html). This web is also recommended to read.

## Gripper Driver

To control the new gripper with ros2, you need a driver with ros2_control interface. The best way is to search it online. If there is no package for the gripper, here are 2 examples to mimic. [robotiq_driver](https://github.com/PickNikRobotics/ros2_robotiq_gripper/tree/main/robotiq_driver), [robotiq_hande_driver](https://github.com/AGH-CEAI/robotiq_hande_driver/).

## URDF, SRDF, XRDF

### .urdf.xacro w/ ros2_control

Most of the gripper will have these information online. You could seach `<gripper_name>-description` to find if there is any pre-defined files.

The first URDF file we need is a `.urdf.xacro` with ros2_control part. In this file, the links, joints, and meshes are defined. [This file](https://github.com/macmacal/robotiq_hande_description/blob/humble-devel/urdf/robotiq_hande_gripper.urdf.xacro) is a good example. Regarding ros2_control, you must define a interface/plugin you defined in the gripper driver. For example, `robotiq_hande_driver/RobotiqHandeHardwareInterface` in [`robotiq_hande_gripper.ros2_control.xacro`](https://github.com/macmacal/robotiq_hande_description/blob/humble-devel/urdf/robotiq_hande_gripper.ros2_control.xacro) corresponds to the [driver](https://github.com/AGH-CEAI/robotiq_hande_driver/blob/humble-devel/robotiq_hande_driver/hardware/src/hande_hardware_interface.cpp) it use.

We also need a urdf file **without** ros2_control part. This file should be named like `robotiq_hadne.urdf`. You should put all links into this file, like [ur_robotiq_hande_gripper.urdf](../isaac_manipulator_pick_and_place/urdf/ur10e_robotiq_hande.urdf). These `.urdf` file is for isaacSim. You could generate `.usd` file with the isaacSim's tools `URDF Importer`. How to do it refer to the [tutorial](https://docs.isaacsim.omniverse.nvidia.com/4.5.0/robot_setup/ext_isaacsim_asset_importer_urdf.html). With `.usd` files, you could easily generate `.obj` and `.mtl` files which `pick_and_place_orchestrator.py` need. `.usd` file of the gripper is also necessary for generating grasp files.

### SRDF

SRDF file is the most easiest part of all. All you need to do is to identify the links which may have collision to other links but it is normal. [`robotiq_hande.srdf.xacro`](../isaac_manipulator_pick_and_place/srdf/robotiq_hande.srdf.xacro) is a good example.

### XRDF

XRDF is a file to define the collision region of the whole arm. It takrs time to define multiple spheres to cover the whole arm. The whole process is described in [tutorial](https://docs.omniverse.nvidia.com/isaacsim/latest/advanced_tutorials/tutorial_motion_generation_robot_description_editor.html). Just follow it, you could get a XRDF for your robot.

### Partial test
After URDF, SRDF, XRDF files are ready, it is recommended to have a test to see if these files work. You could launch a basic cuMotion planner to test if it is possible to plan a trajectory. Folow this [tutorial](https://nvidia-isaac-ros.github.io/repositories_and_packages/isaac_ros_cumotion/isaac_ros_cumotion_moveit/index.html) and change the `urdf` and `xrdf` file to your new ones. You could test the correctness of these files.

## launch files

1. `isaac_manipulator_pick_and_place/launch/ur_hande_pick_and_place.launch.py`: basically, all files related to gripper need to be editted. You could search `gripper_type` in the launch file.
2. `isaac_manipulator_ros_python_utils/isaac_manipulator_ros_python_utils/launch_utils.py`: you need to define the get_gripper_collision_links for your gripper. 
3. `isaac_manipulator_ros_python_utils/isaac_manipulator_ros_python_utils/types.py`: you need to add the string of your gripper type here.