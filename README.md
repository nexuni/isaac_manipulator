# Isaac Manipulator

This repository is for the demo in hsinchu office. Mainly follow the [tutorial](https://nvidia-isaac-ros.github.io/reference_workflows/isaac_manipulator/tutorials/tutorial_pick_and_place.html)

## Hardware

- Nvidia Jetson Orin
- ur10e
- Robotiq hande
- realsense D455

## Robot Setup

The following setups are necessary to control the robot and the gripper via ros2:

1. Download  `rs485-1.0.urcap` from [here](https://github.com/UniversalRobots/Universal_Robots_ToolComm_Forwarder_URCap/releases) and install it to the UR teach pendant. This is the version to enable control ur robot and control the gripper with RS485 at the same time.
2. Follow the description on [web](https://nvidia-isaac-ros.github.io/reference_workflows/isaac_manipulator/tutorials/tutorial_e2e.html#set-up-ur-robot) to setup the `external_control` program with the `urcap` downloaded in step 1.
3. Everytime using the robot, you should follow the steps to activate the gripper:
    1. Go to `tool_io/io_interface_control` page on the UR teach pendant, set to `gripper`.
    2. Go to `urcaps/gripper` page, actuvate the gripper.
    3. Back to `tool_io/io_interface_control` page, change the value to `user`.
4. Create the virtual comport for controlling the gripper. The comport `/tmp/ttyUR` is created with the command:

    ``` bash
    ros2 run ur_robot_driver tool_communication.py --ros-args -p robot_ip:=[ROBOT_IP]
    ```
    After the settings in step3 and the creation of virtual comport, you could control the gripper from your computer.
    You could test the communication with the [test file](https://github.com/AGH-CEAI/robotiq_hande_driver/blob/humble-devel/robotiq_hande_driver/test/communication_test.cpp).
5. When you want to control the robot, follow the tutorial to run `ur_control.launch.py` or the cooresponding launch file. After the node in the main computer is launched, press `play` on the UR teach pendant to enable the robot. 

## Edit the pick_and_place.launch for custom gripper

The default setting, config files, and launch files only support ur10e/ur5e with gripper robotiq-2f-85/-140. However, the gripper we used is robotiq hande. Following is the steps and necessary files to run with a custom gripper.

[Tutorial](https://nvidia-isaac-ros.github.io/concepts/manipulation/cumotion_moveit/tutorial_custom_manipulator.html#creating-an-xrdf-file-for-a-custom-manipulator)

### .xrdf file

Follow the [tutorial](https://nvidia-isaac-ros.github.io/concepts/manipulation/cumotion_moveit/tutorial_custom_manipulator.html#creating-an-xrdf-file-for-a-custom-manipulator)

### Control Robotiq Hande with ros2 action

You could control the hande gripper with ros2 action after starting the `controller` node. The control command is:

```bash
ros2 action send_goal /robotiq_gripper_controller/gripper_cmd control_msgs/action/GripperCommand "{command: {position: 0.025, max_effort: 1.0}}"
```

- `position` is the target position in unit of meter. `0.025` for open, `0.0` for closed.
- `max_effort` is the max force or torque of the gripper, which ranges from `0.0` to `1.0`. `1.0` for the max effort, `0.0` means the min effort. The actual value (in N) need to be checked in the relevant documents.
