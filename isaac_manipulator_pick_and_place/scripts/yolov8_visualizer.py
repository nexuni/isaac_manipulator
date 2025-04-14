#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from vision_msgs.msg import Detection2DArray
from cv_bridge import CvBridge
import cv2
import time

from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSHistoryPolicy, qos_profile_sensor_data

class YoloBBoxVisualizer(Node):
    def __init__(self):
        super().__init__('yolo_bbox_visualizer')

        # Declare parameters
        self.declare_parameter('input_image_qos', "SENSOR_DATA")
        self.declare_parameter('input_bbox_qos', "SENSOR_DATA")
        self.declare_parameter('output_qos', "DEFAULT")

        # Extract the parameters
        self.input_image_qos_string = self.get_parameter('input_image_qos').get_parameter_value().string_value
        self.input_bbox_qos_string = self.get_parameter('input_bbox_qos').get_parameter_value().string_value
        self.output_qos_string = self.get_parameter('output_qos').get_parameter_value().string_value

        self.bridge = CvBridge()

        self.qos_dict = {
            "SENSOR_DATA": qos_profile_sensor_data,
            "DEFAULT": QoSProfile(
                reliability=QoSReliabilityPolicy.RELIABLE, 
                history=QoSHistoryPolicy.KEEP_LAST,
                depth=10
            )
        }
        if self.input_image_qos_string not in self.qos_dict:
            self.input_image_qos_string = "SENSOR_DATA"
        if self.input_bbox_qos_string not in self.qos_dict:
            self.input_bbox_qos_string = "SENSOR_DATA"
        if self.output_qos_string not in self.qos_dict:
            self.output_qos_string = "DEFAULT"

        self.image_sub = self.create_subscription(
            Image,
            '/camera/image_raw',
            self.image_callback,
            self.qos_dict[self.input_image_qos_string])

        self.detections_sub = self.create_subscription(
            Detection2DArray,
            '/yolo_detections',
            self.detections_callback,
            self.qos_dict[self.input_bbox_qos_string])

        self.image_pub = self.create_publisher(
            Image,
            '/yolov8/image_with_boxes',
            self.qos_dict[self.output_qos_string])

        self.latest_image = None

    def image_callback(self, msg):
        self.get_logger().info("receive_img")
        self.latest_image = msg

    def detections_callback(self, msg):
        self.get_logger().info("receive_detections")
        if self.latest_image is None:

            self.get_logger().info("No!!")
            return

        # Convert ROS image to OpenCV
        cv_image = self.bridge.imgmsg_to_cv2(self.latest_image, desired_encoding='bgr8')

        for idx, detection in enumerate(msg.detections):
            box = detection.bbox
            center_x = int(box.center.position.x)
            center_y = int(box.center.position.y)
            width = int(box.size_x)
            height = int(box.size_y)

            top_left = (center_x - width // 2, center_y - height // 2)
            bottom_right = (center_x + width // 2, center_y + height // 2)

            cv2.rectangle(cv_image, top_left, bottom_right, (0, 255, 0), 2)

            if detection.results:
                # label = detection.results[0].hypothesis.class_id
                label = str(idx)
                cv2.putText(cv_image, label, (top_left[0], top_left[1] - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2, cv2.LINE_AA)

        # Publish the image with bounding boxes
        img_msg = self.bridge.cv2_to_imgmsg(cv_image, encoding='bgr8')
        self.image_pub.publish(img_msg)

def main(args=None):
    rclpy.init(args=args)
    node = YoloBBoxVisualizer()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
