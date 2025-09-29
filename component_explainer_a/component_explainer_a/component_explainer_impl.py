import random
import json

from rclpy.action import ActionServer, GoalResponse, ActionClient
from rclpy.lifecycle import Node
from rclpy.lifecycle import State
from rclpy.lifecycle import TransitionCallbackReturn

from explainability_msgs.action import GenerateComponentExplanation
from explainability_msgs.msg import Explanation


class explainerImpl(Node):
    """Implementation of component_explainer_a."""

    def __init__(self) -> None:
        """Construct the node."""
        super().__init__('explainer_component_explainer_a')

        self.get_logger().info("Initialising...")

        self.explainer_server = None  # action server to start/stop this explainer

        self.get_logger().info('explainer component_explainer_a started, but not yet configured.')

    def on_request_goal(self, goal_handle):
        """Accept incoming goal if appropriate."""
        if self._state_machine.current_state[1] != "active":
            self.get_logger().error("explainer is not active, rejecting goal")
            return GoalResponse.REJECT

        self.get_logger().info("Accepted a new goal")
        return GoalResponse.ACCEPT

    def on_request_exec(self, goal_handle):
        """Process incoming goal."""
        context = json.loads(goal_handle.request.json_data)

        # Get here your attributes from the input context, if needed for the explanation generation
        question = context.get("question", "")
        timestamp = context.get("timestamp", "")
        self.get_logger().info(f"Request for explanation with question: {question} at {timestamp}")

        feedback_msg = GenerateComponentExplanation.Feedback()
        feedback_msg.status = "explainer started"

        goal_handle.publish_feedback(feedback_msg)

        # Implement here the actual explanation generation logic
        if random.randint(0, 1) < 0.5:
            explanation = "I failed because I was tired."
            generated_explanation = Explanation(
                component_name="component_explainer_a",
                explanation=explanation)
            explanations = [generated_explanation]
            self.get_logger().info(f"Generated explanation: {generated_explanation.explanation}")
        else:
            # Here we call another component explainer to create a chain of explanations
            explanation = "I failed because I could not execute skill B."
            generated_explanation = Explanation(
                component_name="component_explainer_a",
                explanation=explanation)
            explanations = [generated_explanation]
            self.get_logger().info(f"Generated explanation: {generated_explanation.explanation}")

            self.component_explainer_responded = False
            sub_explanations = self.send_goal_to_component_explainer(context).explanations
            explanations.extend(sub_explanations)

        feedback_msg.status = "explainer completed"
        goal_handle.publish_feedback(feedback_msg)

        self.get_logger().info("Explanation generation completed.")
        self.get_logger().info(f"Explanations: {[exp.explanation for exp in explanations]}")

        goal_handle.succeed()
        return GenerateComponentExplanation.Result(explanations=explanations)

    def component_explainer_response_callback(self, future):
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().info('Goal rejected by component explain')
            return

        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(self.component_get_result_callback)

    def component_get_result_callback(self, future):
        # result = future.result().result
        self.component_explainer_responded = True

    def send_goal_to_component_explainer(self, context: dict):
        goal = GenerateComponentExplanation.Goal()
        goal.json_data = json.dumps(context)

        client = self._component_explainer_b_client

        self.get_logger().info('Sending goal to component_explainer_b')

        # Wait for the action server to be available
        while not client.wait_for_server(timeout_sec=1.0):
            self.get_logger().info('Component explainer not available, waiting...')

        # Send the goal to the action server
        future = client.send_goal_async(goal)
        future.add_done_callback(self.component_explainer_response_callback)

        # Wait for the result
        while not self.component_explainer_responded:
            result_future = future.result()
            if result_future:
                result = result_future.get_result().result
            else:
                result = GenerateComponentExplanation.Result()
                result.error_msg = "Failed to get result from component_explainer_b"

        return result

    #################################
    #
    # Lifecycle transitions callbacks
    #
    def on_configure(self, state: State) -> TransitionCallbackReturn:
        """
        Configure the skill.

        You usually want to do the following in this state:
        - Read ROS parameters (if any)
        - Create ROS action clients and servers
        - Create ROS publishers and subscribers
        - Start publishing diagnostic information

        While the explainer is configured, but not activated, it should not
        perform any actions that are not required for configuration, such as
        effectively processing data or calling external services.
        For instance, incoming goals on an action server should be rejected.

        :return: The state machine either invokes a transition to the
            "inactive" state or stays in "unconfigured" depending on the
            return value.
            TransitionCallbackReturn.SUCCESS transitions to "inactive".
            TransitionCallbackReturn.FAILURE transitions to "unconfigured".
            TransitionCallbackReturn.ERROR or any uncaught exceptions to
            "errorprocessing"
        """
        self.explainer_server = ActionServer(
            self, GenerateComponentExplanation, "/component_explainer_a/explain",
            goal_callback=self.on_request_goal,
            execute_callback=self.on_request_exec)

        self._component_explainer_b_client = ActionClient(
            self, GenerateComponentExplanation, '/component_explainer_b/explain')

        self.get_logger().info("explainer component_explainer_a is configured, but not yet active")
        return TransitionCallbackReturn.SUCCESS

    def on_activate(self, state: State) -> TransitionCallbackReturn:
        """
        Activate the skill.

        You usually want to do the following in this state:
        - Create and start any timers performing periodic routines
        - Start processing data, and accepting action goals, if any

        """
        self.get_logger().info("component_explainer_a is active and running")
        return super().on_activate(state)

    def on_deactivate(self, state: State) -> TransitionCallbackReturn:
        """Stop the timer to stop calling the `run` function."""
        self.get_logger().info("Stopping explainer...")

        self.get_logger().info("component_explainer_a is stopped (inactive)")
        return super().on_deactivate(state)

    def on_shutdown(self, state: State) -> TransitionCallbackReturn:
        """
        Shutdown the node, after a shutting-down transition is requested.

        :return: The state machine either invokes a transition to the
            "finalized" state or stays in the current state depending on the
            return value.
            TransitionCallbackReturn.SUCCESS transitions to "finalized".
            TransitionCallbackReturn.FAILURE remains in current state.
            TransitionCallbackReturn.ERROR or any uncaught exceptions to
            "errorprocessing"
        """
        self.get_logger().info('Shutting down component_explainer_a.')

        self.get_logger().info("component_explainer_a finalized.")
        return TransitionCallbackReturn.SUCCESS

    #################################
