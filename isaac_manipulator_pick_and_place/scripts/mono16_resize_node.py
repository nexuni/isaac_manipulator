#!/usr/bin/env python3

import rclpy
from rclpy.node import Node

from sensor_msgs.msg import Image
import cv2
from cv_bridge import CvBridge, CvBridgeError
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSHistoryPolicy, qos_profile_sensor_data


class DepthImageResizer(Node):
    def __init__(self):
        super().__init__('depth_image_resizer')
        # Declare parameters
        self.declare_parameter('input_width', 1280)
        self.declare_parameter('input_height', 720)
        self.declare_parameter('input_qos', "SENSOR_DATA")
        self.declare_parameter('output_width', 640)
        self.declare_parameter('output_height', 360)
        self.declare_parameter('outpu_qos', "DEFAULT")


        # Extract the parameters
        self.input_width = self.get_parameter('input_width').get_parameter_value().integer_value
        self.input_height = self.get_parameter('input_height').get_parameter_value().integer_value
        self.input_qos_string = self.get_parameter('input_qos').get_parameter_value().string_value
        self.output_width = self.get_parameter('output_width').get_parameter_value().integer_value
        self.output_height = self.get_parameter('output_height').get_parameter_value().integer_value
        self.output_qos_string = self.get_parameter('outpu_qos').get_parameter_value().string_value

        # Define input and output topics
        self.input_topic = 'image_raw'
        self.output_topic = 'image_raw_output'

        self.qos_dict = {
            "SENSOR_DATA": qos_profile_sensor_data,
            "DEFAULT": QoSProfile(
                reliability=QoSReliabilityPolicy.RELIABLE, 
                history=QoSHistoryPolicy.KEEP_LAST,
                depth=10
            )
        }
        if self.input_qos_string not in self.qos_dict:
            self.input_qos_string = "SENSOR_DATA"
        if self.output_qos_string not in self.qos_dict:
            self.output_qos_string = "DEFAULT"

        # Image encoding
        self.encoding = '16UC1'

        # Initialize CvBridge
        self.bridge = CvBridge()

        # Create a subscriber to the input topic
        self.subscription = self.create_subscription(
            Image,
            self.input_topic,
            self.listener_callback,
            self.qos_dict[self.input_qos_string]
        )
        self.subscription  # prevent unused variable warning

        # Create a publisher for the output topic
        self.publisher = self.create_publisher(
            Image,
            self.output_topic,
            self.qos_dict[self.output_qos_string]
        )

        self.get_logger().info('DepthImageResizer node has been started.')

    def listener_callback(self, msg):
        try:
            # Convert ROS Image message to OpenCV image (numpy array)
            cv_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding=self.encoding)

            # Verify input image size
            height, width = cv_image.shape
            if width != self.input_width or height != self.input_height:
                self.get_logger().warn(
                    f"Received image with resolution {width}x{height}, expected {self.input_width}x{self.input_height}."
                )

            # Resize the image to desired resolution
            resized_image = cv2.resize(
                cv_image,
                (self.output_width, self.output_height),
                interpolation=cv2.INTER_NEAREST  # Use nearest to preserve depth accuracy
            )

            # Convert resized OpenCV image back to ROS Image message
            output_msg = self.bridge.cv2_to_imgmsg(resized_image, encoding=self.encoding)
            output_msg.header = msg.header  # Preserve the original timestamp and frame ID

            # Publish the resized image
            self.publisher.publish(output_msg)

            self.get_logger().debug(
                f"Published resized image with resolution {self.output_width}x{self.output_height}."
            )

        except CvBridgeError as e:
            self.get_logger().error(f"CvBridge Error: {e}")
        except Exception as e:
            self.get_logger().error(f"Unexpected error: {e}")


def main(args=None):
    rclpy.init(args=args)
    node = DepthImageResizer()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('DepthImageResizer node has been stopped.')
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()