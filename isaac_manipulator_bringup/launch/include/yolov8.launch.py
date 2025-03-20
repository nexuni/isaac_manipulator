# SPDX-FileCopyrightText: NVIDIA CORPORATION & AFFILIATES
# Copyright (c) 2024 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0

import os

from ament_index_python.packages import get_package_share_directory

from isaac_ros_launch_utils.all_types import ComposableNode, DeclareLaunchArgument, \
    LaunchConfiguration, LoadComposableNodes, LaunchDescription, GroupAction, OpaqueFunction, \
    IncludeLaunchDescription, PythonLaunchDescriptionSource

import isaac_manipulator_ros_python_utils.constants as constants


def launch_setup(context, *args, **kwargs):
    model_file_path = LaunchConfiguration('yolov8_model_file_path')
    engine_file_path = LaunchConfiguration('yolov8_engine_file_path')
    yolov8_input_qos = LaunchConfiguration('yolov8_input_qos')
    detections_2d_array_output_topic = LaunchConfiguration(
        'detections_2d_array_output_topic', default='detections_output')

    image_input_topic = LaunchConfiguration("image_input_topic")
    camera_info_input_topic = LaunchConfiguration("camera_info_input_topic")

    image_width = LaunchConfiguration('image_width')
    image_height = LaunchConfiguration('image_height')

    input_fps = LaunchConfiguration('input_fps')
    dropped_fps = LaunchConfiguration('dropped_fps')

    confidence_threshold = LaunchConfiguration('confidence_threshold')
    nms_threshold = LaunchConfiguration('nms_threshold')
    number_of_classes = LaunchConfiguration('number_of_classes')


    yolov8_is_object_following = str(context.perform_substitution(LaunchConfiguration(
        'yolov8_is_object_following', default='False')))

    drop_node_nodes = []

    dropped_image_topic_name = image_input_topic
    dropped_camera_info_topic_name = camera_info_input_topic

    if yolov8_is_object_following == 'True':
        dropped_image_topic_name = '/yolov8/image_dropped'
        dropped_camera_info_topic_name = '/yolov8/camera_info_dropped'
        drop_node_nodes.append(ComposableNode(
            name='yolov8_drop_node',
            package='isaac_ros_nitros_topic_tools',
            plugin='nvidia::isaac_ros::nitros::NitrosCameraDropNode',
            parameters=[{
                'input_qos': yolov8_input_qos,
                'output_qos': yolov8_input_qos,
                'X': dropped_fps,
                'Y': input_fps,
                'mode': 'mono',
                'sync_queue_size': 100
            }],
            remappings=[
                ('image_1', image_input_topic),
                ('camera_info_1', camera_info_input_topic),
                ('image_1_drop', dropped_image_topic_name),
                ('camera_info_1_drop', dropped_camera_info_topic_name)
            ]
        ))

    yolov8_network_width = 640
    image_mean = '[0.0, 0.0, 0.0]'
    image_stddev = '[1.0, 1.0, 1.0]'
    yolov8_encoder_include_dir = os.path.join(
        get_package_share_directory('isaac_ros_dnn_image_encoder'), 'launch')
    
    yolov8_encoder_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            [yolov8_encoder_include_dir, '/dnn_image_encoder.launch.py']),
        launch_arguments={
            'input_image_width': str(context.perform_substitution(image_width)),
            'input_image_height': str(context.perform_substitution(image_height)),
            'network_image_width': str(yolov8_network_width),
            'network_image_height': str(yolov8_network_width),
            'image_mean': image_mean,
            'image_stddev': image_stddev,
            'attach_to_shared_component_container': 'True',
            'component_container_name': constants.MANIPULATOR_CONTAINER_NAME,
            'dnn_image_encoder_namespace': 'yolov8_encoder',
            'image_input_topic': dropped_image_topic_name,
            'camera_info_input_topic': dropped_camera_info_topic_name,
            'input_qos': yolov8_input_qos,
            'tensor_output_topic': '/tensor_pub',
        }.items(),
    )

    tensor_rt_node = ComposableNode(
        name='yolov8_tensor_rt',
        package='isaac_ros_tensor_rt',
        plugin='nvidia::isaac_ros::dnn_inference::TensorRTNode',
        parameters=[{
            'model_file_path': model_file_path,
            'engine_file_path': engine_file_path,
            'output_binding_names': ['output0'],
            'output_tensor_names': ['output_tensor'],
            'input_tensor_names': ['input_tensor'],
            'input_binding_names': ['images'],
            'verbose': False,
            'force_engine_update': False,
        }],
    )

    yolov8_decoder_node = ComposableNode(
        name='yolov8_decoder_node',
        package='isaac_ros_yolov8',
        plugin='nvidia::isaac_ros::yolov8::YoloV8DecoderNode',
        parameters=[{
            'confidence_threshold': confidence_threshold,
            'nms_threshold': nms_threshold,
            'num_classes': number_of_classes,
        }],
        remappings=[
            ('detections_output', detections_2d_array_output_topic),
        ]
    )
    
    final_nodes = [
        tensor_rt_node,
        yolov8_decoder_node,
    ]
    final_nodes += drop_node_nodes
    load_composable_nodes = LoadComposableNodes(
        target_container=constants.MANIPULATOR_CONTAINER_NAME,
        composable_node_descriptions=final_nodes)

    final_launch = GroupAction(
        actions=[
            load_composable_nodes,
            yolov8_encoder_launch
        ],)

    return [final_launch]


def generate_launch_description():
    launch_args = [
        DeclareLaunchArgument(
            'yolov8_model_file_path',
            default_value='',
            description='The absolute path to the YOLOv8 ONNX file.',
        ),
        DeclareLaunchArgument(
            'yolov8_engine_file_path',
            default_value='',
            description='The absolute path to the YOLOv8 engine plan.',
        ),
        DeclareLaunchArgument(
            'input_fps',
            default_value='30',
            description='FPS for input message to the drop node'
        ),
        DeclareLaunchArgument(
            'dropped_fps',
            default_value='28',
            description='FPS that are dropped by the drop node'),
        DeclareLaunchArgument(
            'yolov8_input_qos',
            default_value='SENSOR_DATA',
            description='QOS setting used for YOLOv8 input'),
        DeclareLaunchArgument(
            'confidence_threshold',
            default_value='0.25',
            description='Confidence threshold to filter candidate detections during NMS'
        ),
        DeclareLaunchArgument(
            'nms_threshold',
            default_value='0.45',
            description='NMS IOU threshold'
        ),
        DeclareLaunchArgument(
            'number_of_classes',
            default_value='1',
            description='Number of the classes detected by yolov8 model'
        ),
    ]

    return LaunchDescription(launch_args + [OpaqueFunction(function=launch_setup)])
