#!/usr/bin/env python3
import rclpy
from rclpy.node import Node

from isaac_manipulator_interfaces.srv import ClearObjects
from isaac_manipulator_interfaces.action import GetObjects, PickAndPlace

from rclpy.action import ActionClient
from rclpy.callback_groups import ReentrantCallbackGroup

import time

class PickAndPlaceController(Node):
    def __init__(self):
        super().__init__('pick_and_place_controller')

        # Declare parameters
        self.declare_parameter('target_class_id', -1)

        # Extract the parameters
        self.target_class_id = self.get_parameter('target_class_id').get_parameter_value().integer_value

        if self.target_class_id == -1:
            self.get_logger().error(f'target_class_id is not provided')
            raise Exception("")

        self.callback_group = ReentrantCallbackGroup()

        # 1. Service Client
        self.clear_objects_client = self.create_client(
            ClearObjects,
            '/clear_objects',
            callback_group=self.callback_group
        )

        # 2. Action Clients
        self.get_objects_client = ActionClient(
            self,
            GetObjects,
            '/get_objects',
            callback_group=self.callback_group
        )

        self.pick_and_place_client = ActionClient(
            self,
            PickAndPlace,
            '/pick_and_place',
            callback_group=self.callback_group
        )

        # Wait for all services and actions
        self.get_logger().info('Waiting for services/actions...')
        self.clear_objects_client.wait_for_service()
        self.get_objects_client.wait_for_server()
        self.pick_and_place_client.wait_for_server()
        self.get_logger().info('All service/action ready.')

        self.run_loop()

    def call_clear_objects(self):
        request = ClearObjects.Request()
        future = self.clear_objects_client.call_async(request)
        rclpy.spin_until_future_complete(self, future)
        if future.result() is not None:
            self.get_logger().info('Cleared all objects.')
        else:
            self.get_logger().error('Failed to call /clear_objects')

    def call_get_objects(self):
        goal_msg = GetObjects.Goal()
        future = self.get_objects_client.send_goal_async(goal_msg)
        rclpy.spin_until_future_complete(self, future)
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().warn('GetObjects goal rejected')
            return []

        result_future = goal_handle.get_result_async()
        rclpy.spin_until_future_complete(self, result_future)
        result = result_future.result().result

        obj_lists = result.objects
        grasp_object_id = 10000

        for obj in obj_lists:
            idx = int(obj.object_id)
            class_id = obj.detection_2d.results[0].hypothesis.class_id
            bbox = obj.detection_2d.bbox
            self.get_logger().info(f"Object {idx} is Class {class_id}, bbox @ ({bbox.center.position.x}, {bbox.center.position.y}) wirh size({bbox.size_x}, {bbox.size_y})")
            if str(class_id) == str(self.target_class_id):
                if idx < grasp_object_id:
                    grasp_object_id = idx

        if grasp_object_id == 10000:
            return None

        return grasp_object_id

    def call_pick_and_place(self, object_id: int):
        goal_msg = PickAndPlace.Goal()
        goal_msg.object_id = object_id
        future = self.pick_and_place_client.send_goal_async(goal_msg)
        rclpy.spin_until_future_complete(self, future)
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().warn(f'PickAndPlace goal for {object_id} rejected')
            return

        result_future = goal_handle.get_result_async()
        rclpy.spin_until_future_complete(self, result_future)
        result = result_future.result().result
        self.get_logger().info(f'Pick and place for {object_id} completed with success: {result.success}')

    def run_loop(self):
        while rclpy.ok():
            self.call_clear_objects()
            time.sleep(0.5)

            object_id = self.call_get_objects()

            if object_id is None:
                self.get_logger().info('No objects found, retrying in 3 seconds...')
                time.sleep(3.0)
                continue

            time.sleep(0.5)
            self.get_logger().warn(f'Start to PickAndPlace Object-{object_id}...')
            self.call_pick_and_place(object_id)

            pause_secs = 5
            for i in range(pause_secs):
                time.sleep(2.0)
                self.get_logger().info(f'Pause for {i+1}/{pause_secs}')

def main(args=None):
    rclpy.init(args=args)
    node = PickAndPlaceController()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()