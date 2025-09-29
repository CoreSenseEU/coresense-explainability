import random
import json

from rclpy.action import ActionServer, GoalResponse
from rclpy.lifecycle import Node
from rclpy.lifecycle import State
from rclpy.lifecycle import TransitionCallbackReturn

from explainability_msgs.action import GenerateComponentExplanation
from explainability_msgs.msg import Explanation


class explainerImpl(Node):
    """Implementation of component_explainer_c."""

    def __init__(self) -> None:
        """Construct the node."""
        super().__init__('explainer_component_explainer_c')

        self.get_logger().info("Initialising...")

        self.explainer_server = None  # action server to start/stop this explainer

        self.get_logger().info('explainer component_explainer_c started, but not yet configured.')

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
            explanation = "I failed because the plan I generated had a wrong sequence of skills."
        else:
            explanation = "I failed because there was an unforeseen situation during execution."

        generated_explanation = Explanation(
            component_name="component_explainer_c",
            explanation=explanation)

        self.get_logger().info(f"Generated explanation: {generated_explanation.explanation}")

        explanations = [generated_explanation]

        feedback_msg.status = "explainer completed"
        goal_handle.publish_feedback(feedback_msg)

        goal_handle.succeed()
        return GenerateComponentExplanation.Result(explanations=explanations)

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
        # create the control server for ourselves
        self.explainer_server = ActionServer(
            self, GenerateComponentExplanation, "/component_explainer_c/explain",
            goal_callback=self.on_request_goal,
            execute_callback=self.on_request_exec)

        self.get_logger().info("explainer component_explainer_c is configured, but not yet active")
        return TransitionCallbackReturn.SUCCESS

    def on_activate(self, state: State) -> TransitionCallbackReturn:
        """
        Activate the skill.

        You usually want to do the following in this state:
        - Create and start any timers performing periodic routines
        - Start processing data, and accepting action goals, if any

        """
        self.get_logger().info("component_explainer_c is active and running")
        return super().on_activate(state)

    def on_deactivate(self, state: State) -> TransitionCallbackReturn:
        """Stop the timer to stop calling the `run` function."""
        self.get_logger().info("Stopping explainer...")

        self.get_logger().info("component_explainer_c is stopped (inactive)")
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
        self.get_logger().info('Shutting down component_explainer_c.')

        self.get_logger().info("component_explainer_c finalized.")
        return TransitionCallbackReturn.SUCCESS

    #################################
