from ament_index_python.packages import get_package_share_directory

import os
import yaml

from launch_ros.actions import ComposableNodeContainer, Node
from launch_ros.descriptions import ComposableNode
from launch_ros.parameter_descriptions import ParameterFile
from launch_ros.substitutions import FindPackageShare

import isaac_ros_launch_utils as lu

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
from launch.conditions import IfCondition
from launch.substitutions import Command, FindExecutable, LaunchConfiguration
from launch.substitutions import PathJoinSubstitution, PythonExpression
from launch.launch_description_sources import PythonLaunchDescriptionSource
from moveit_configs_utils import MoveItConfigsBuilder
import isaac_manipulator_ros_python_utils.constants as constants

def launch_setup(context, *args, **kwargs):
    yolov8_object_class_id = str(context.perform_substitution(
        LaunchConfiguration('yolov8_object_class_id')))
    input_fps = LaunchConfiguration('input_fps')
    dropped_fps = LaunchConfiguration('dropped_fps')
    static_transform_filepath = str(context.perform_substitution(
        LaunchConfiguration('static_transform')))

    static_transform_launch = None
    if static_transform_filepath != '':
        static_transform_launch = IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                static_transform_filepath
            )
        )


    launch_files_include_dir = os.path.join(
        get_package_share_directory('isaac_manipulator_bringup'), 'launch', 'include')

    realsense_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([launch_files_include_dir, '/realsense.launch.py']),
        launch_arguments={
            'num_cameras': '1',
            'run_standalone': 'True',
        }.items(),
    )  

    # Original Image Resolution
    depth_image_width = 1280
    depth_image_height = 720
    rgb_image_width = 1280
    rgb_image_height = 720

    # object detection image size
    obj_detection_width = 640
    obj_detection_height = int(rgb_image_height * obj_detection_width / rgb_image_width)
    input_image_topic = '/camera_1/color/image_raw'
    input_camera_info = '/camera_1/color/camera_info'
    input_depth_topic = '/camera_1/aligned_depth_to_color/image_raw'

    # object detection server and YOLOv8 topics
    yolov8_rgb_image_topic = '/resize/image'
    yolov8_rgb_camera_info = '/resize/camera_info'
    yolov8_detections_topic = '/detections'

    # foundation pose server and foundationpose topics
    foundation_pose_rgb_image_topic = '/resize/image'
    foundation_pose_rgb_camera_info = '/resize/camera_info'
    foundation_pose_depth_image_topic = '/resize_depth/image'
    foundation_pose_detections_topic = yolov8_detections_topic


    dropped_image_topic_name = '/yolov8/image_dropped'
    dropped_camera_info_topic_name = '/yolov8/camera_info_dropped'
    dropped_depth_image_topic_name = '/yolov8/depth/image_dropped'
    drop_node_node = ComposableNode(
        name='yolov8_drop_node',
        package='isaac_ros_nitros_topic_tools',
        plugin='nvidia::isaac_ros::nitros::NitrosCameraDropNode',
        parameters=[{
            'input_qos': 'SENSOR_DATA',
            'output_qos': 'SENSOR_DATA',
            'X': dropped_fps,
            'Y': input_fps,
            'mode': 'mono+depth',
            'depth_format_string': 'nitros_image_mono16',
            'sync_queue_size': 100
        }],
        remappings=[
            ('image_1', input_image_topic),
            ('camera_info_1', input_camera_info),
            ('depth_1', input_depth_topic),
            ('image_1_drop', dropped_image_topic_name),
            ('camera_info_1_drop', dropped_camera_info_topic_name),
            ('depth_1_drop', dropped_depth_image_topic_name),
        ]
    )


    # Create resize node of rgb and depth image for object detection
    resize_node = ComposableNode(
        name='object_detection_resize_node',
        package='isaac_ros_image_proc',
        plugin='nvidia::isaac_ros::image_proc::ResizeNode',
        parameters=[{
            'input_qos': 'SENSOR_DATA',
            'input_width': rgb_image_width,
            'input_height': rgb_image_height,
            'output_width': obj_detection_width,
            'keep_aspect_ratio': True,
            'encoding_desired': 'rgb8',
            'disable_padding': True
        }],
        remappings=[
            ('image', dropped_image_topic_name),
            ('camera_info', dropped_camera_info_topic_name),
        ],
    )

    resize_depth_node = Node(
        name='object_detection_resize_depth_node',
        package='isaac_manipulator_pick_and_place',
        executable='mono16_resize_node.py',
        parameters=[{
            'input_qos': 'SENSOR_DATA',
            'input_width': depth_image_width,
            'input_height': depth_image_height,
            'output_width': obj_detection_width,
            'output_height': obj_detection_height,
        }],
        remappings=[
            ('image_raw', dropped_depth_image_topic_name),
            ('image_raw_output', '/resize_depth/image'),
        ],
    )

    isaac_ros_ws_path = lu.get_isaac_ros_ws_path()
    labels_file_path = os.path.join(
        isaac_ros_ws_path, 'isaac_ros_assets/models/yolov8', 'labels.yaml'
    )
    with open(labels_file_path) as labels_file:
        labels_config = yaml.safe_load(labels_file)

    number_of_classes = len(labels_config["yolov8"]["labels"])

    yolov8_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            [launch_files_include_dir, '/yolov8.launch.py']
        ),
        launch_arguments={
            'image_width': str(obj_detection_width),
            'image_height': str(obj_detection_height),
            'image_input_topic': yolov8_rgb_image_topic,
            'camera_info_input_topic': yolov8_rgb_camera_info,
            'detections_2d_array_output_topic': yolov8_detections_topic,
            'yolov8_input_qos': 'DEFAULT',
            'yolov8_engine_file_path':
                isaac_ros_ws_path + '/isaac_ros_assets/models/yolov8/robot8.plan',
            'yolov8_model_file_path':
                isaac_ros_ws_path + '/isaac_ros_assets/models/yolov8/robot8.onnx',
            'number_of_classes': str(number_of_classes),
        }.items()
    )

    if int(yolov8_object_class_id) not in labels_config["yolov8"]["labels"]:
        raise NotImplementedError('Object Class Id is not supported')

    object_folder_name = labels_config["yolov8"]["labels"][int(yolov8_object_class_id)]
    object_folder_path = os.path.join(
        isaac_ros_ws_path, 'isaac_ros_assets/isaac_ros_foundationpose', object_folder_name
    )


    foundationpose_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            [launch_files_include_dir, '/foundationpose_yolov8.launch.py']
        ),
        launch_arguments={
            'is_object_following': 'True',
            'camera_type': 'realsense',
            'rgb_image_width': str(obj_detection_width),
            'rgb_image_height': str(obj_detection_height),
            'rgb_image_topic': foundation_pose_rgb_image_topic,
            'rgb_camera_info_topic': foundation_pose_rgb_camera_info,
            'foundation_pose_server_depth_topic_name': foundation_pose_depth_image_topic,
            'realsense_depth_image_topic': foundation_pose_depth_image_topic,
            'detection2_d_array_topic': foundation_pose_detections_topic,
            'mesh_file_path': object_folder_path + '/AR-Code-Object-Capture-app.obj',
            'texture_path': object_folder_path + '/baked_mesh_tex0.png',
            'refine_model_file_path': isaac_ros_ws_path + '/isaac_ros_assets/models'
                                                          '/foundationpose/refine_model.onnx',
            'refine_engine_file_path': isaac_ros_ws_path + '/isaac_ros_assets/models'
                                                           '/foundationpose/'
                                                           'refine_trt_engine.plan',
            'score_model_file_path': isaac_ros_ws_path + '/isaac_ros_assets'
                                                         '/models/foundationpose/score_model.onnx',
            'score_engine_file_path': isaac_ros_ws_path + '/isaac_ros_assets/models/'
                                                          'foundationpose/score_trt_engine.plan',
            'object_class_id': yolov8_object_class_id
        }.items()
    )

    manipulation_container = ComposableNodeContainer(
        name=constants.MANIPULATOR_CONTAINER_NAME,
        namespace='',
        package='rclcpp_components',
        executable='component_container_mt',
        composable_node_descriptions=[
            resize_node,
            drop_node_node,
        ],
        arguments=['--ros-args', '--log-level', 'nvblox_node:=error'],
        output='screen'
    )

    nodes_to_start = [
        manipulation_container,
        realsense_launch,
        resize_depth_node,
        yolov8_launch,
        foundationpose_launch,   
    ]

    if static_transform_launch is not None:
        nodes_to_start.append(static_transform_launch)

    return nodes_to_start


def generate_launch_description():
    launch_args = [
        DeclareLaunchArgument(
            'input_fps',
            default_value='30',
            description='FPS for input message to the drop node'
        ),
        DeclareLaunchArgument(
            'dropped_fps',
            default_value='28',
            description='FPS that are dropped by the drop node'
        ),
        DeclareLaunchArgument(
            'yolov8_object_class_id',
            description='Class ID of the object to be detected.'
        ),
        DeclareLaunchArgument(
            'static_transform',
            default_value='',
            description='Filepath of the static transform launch file'
        ),
    ]


    return LaunchDescription(launch_args + [OpaqueFunction(function=launch_setup)])