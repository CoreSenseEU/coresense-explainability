import json
import time
import requests

from rclpy.action import ActionClient
from rclpy.lifecycle import Node
from rclpy.lifecycle import State
from rclpy.lifecycle import TransitionCallbackReturn
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup

from rclpy.action import ActionServer, GoalResponse

from std_msgs.msg import String
from explainability_msgs.action import GenerateExplanation, GenerateComponentExplanation


class GenerateExplanationImpl(Node):
    """Implementation of explainer_selector."""

    def __init__(self) -> None:
        """Construct the node."""
        super().__init__('explainer_selectorer_selector')

        # Declare LLM parameters
        self.declare_parameter('llm_model', 'gpt-4.1-mini')
        self.declare_parameter('llm_host', 'https://api.openai.com')
        self.declare_parameter('api_key', '')

        # Attributes
        self.events_buffer = {}

        self.component_explainers_data = {
            "component_explainer_a": {
                "description": "Explains skills related to navigation and movement, "
                               "such as moving to locations and path planning.",
                "skills": ["move_to", "navigate", "avoid_obstacle"]
            },
            "component_explainer_b": {
                "description": "Explains skills related to object manipulation, "
                               "such as picking up, placing, and interacting with objects.",
                "skills": ["pick", "place", "manipulate"]
            },
            "component_explainer_c": {
                "description": "Explains skills related to high-level task planning, "
                               "such as task sequencing, prioritization, and goal setting.",
                "skills": ["plan_task", "set_goal"]
            },
        }

        # Subscribers
        self._events_subscriber = None

        # Get LLM configuration from ROS parameters
        self.llm_model = (self.get_parameter('llm_model').get_parameter_value().string_value
                          or 'gpt-4.1-mini')
        self.llm_host = (self.get_parameter('llm_host').get_parameter_value().string_value
                         or 'https://api.openai.com')

        self.api_key = (self.get_parameter('api_key').get_parameter_value().string_value or '')

        self.get_logger().info(f"Using LLM model: {self.llm_model}, host: {self.llm_host}")

        # Component Explainers
        self.component_explainers = None

        self.get_logger().info("Initialising...")

        self.get_logger().info('explainer_selector started, but not yet configured.')

    def on_request_goal(self, goal_handle):
        """Accept incoming goal if appropriate."""
        if self._state_machine.current_state[1] != "active":
            self.get_logger().error("Skill is not active yet, rejecting goal")
            return GoalResponse.REJECT

        # You can for example reject the goal if events is empty
        # if len(self.events_buffer) == 0:
        #     self.get_logger().error("No info available, rejecting goal")
        #     return GoalResponse.REJECT

        self.get_logger().info("Accepted a new goal")
        return GoalResponse.ACCEPT

    def on_request_exec(self, goal_handle):
        self.get_logger().info(f"Current state: {self._state_machine.current_state[1]}")
        """Process incoming goal."""
        self.get_logger().info(
            f"Generating explanation for question: {goal_handle.request.question}")

        # Get the relevant context
        relevant_events = self.get_relevant_events(goal_handle.request.question)

        # The flag auto_triggered denotes that there was not a user question,
        # but the explanation was triggered automatically by the system.
        if goal_handle.request.auto_triggered:
            self.get_logger().info("Explanation was auto-triggered by the system")

        # Select the component explainer to use
        component_explainer, context = self.select_explainer_and_create_context(
            goal_handle.request.question, relevant_events)

        # Invoke the selected component explainer
        list_of_explanations = self.invoke_explainer(component_explainer, context)

        # Here you could decide to invoke more than one component explainer
        # and aggregate the explanations later.

        # Each of the component explainers returns a list of Explanation messages, in case
        # they need to call other component explainers to create a chain of explanations.
        for explanation in list_of_explanations:
            self.get_logger().info(f"Explanation received: {explanation}")

        if len(list_of_explanations) == 0:
            self.get_logger().warn("No explanations received, returning default message")
            final_explanation = "I can't explain this right now, sorry."
        elif len(list_of_explanations) == 1:
            # If only one explanation, use it directly
            final_explanation = list_of_explanations[0]
        else:
            # Combine all explanations into a single string
            final_explanation = self.aggregate_explanations(list_of_explanations)

        self.get_logger().info(f"Final explanation: {final_explanation}")
        goal_handle.succeed()

        return GenerateExplanation.Result(explanation=final_explanation)

    #################################
    #
    # Explanation Coordination Logic
    #

    def get_relevant_events(self, question: str):
        """Fetch the relevant context."""
        # Implement here your strategy to fetch the relevant events,
        # using the question and the current time.
        # Here there is an example that gets the latest 3 events.

        current_time_msg = self.get_clock().now().to_msg()
        current_time = f"{current_time_msg.sec}.{current_time_msg.nanosec}"
        sorted_times = sorted(self.events_buffer.keys())
        relevant_times = [t for t in sorted_times if t <= current_time]
        relevant_times = relevant_times[-3:]  # Get the last 3 events
        relevant_events = {str(t): self.events_buffer[t] for t in relevant_times}
        return relevant_events

    def select_explainer_and_create_context(self, question: str, relevant_events: dict):
        """Select the component explainer to use."""
        # Implement here your strategy to select the component explainer to use,
        # based on the question and the relevant_events.

        # Here there is an example that checks for skill failures in the relevant_events,
        # and otherwise uses an LLM to select the component explainer.

        # The context information should also be created in this function
        # to be sent to the explainer.

        skill_failure = False
        print("relevant_events:", relevant_events)
        for timestamp in reversed(list(relevant_events.keys())):
            if "skill_failure" in relevant_events[timestamp]:
                if relevant_events[timestamp]["skill_failure"]:
                    skill_failure = True
                    failed_skill = relevant_events[timestamp].get("failed_skill", "")
                    timestamp_failure = timestamp
                    break
        if skill_failure:
            # One of the skills failed, should query the corresponding component explainer
            component_explainer = "component_explainer_a"  # Default
            for component in self.component_explainers_data:
                if failed_skill in self.component_explainers_data[component]["skills"]:
                    self.get_logger().info(
                        f"Skill failure detected in skill {failed_skill}, "
                        f"which is handled by {component} explainer")
                    component_explainer = component
                    break

            self.get_logger().info(
                f"Skill failure detected, selecting {component_explainer} component explainer")

            context = {
                "question": question,
                "timestamp": timestamp_failure,
            }
        else:
            # None of the skills failed
            component_explainer = self.select_explainer_via_LLM(question, relevant_events)
            self.get_logger().info(
                f"explain selected the {component_explainer} component explainer")

            if component_explainer in self.component_explainers:
                timestamp = list(relevant_events.keys())[-1] if len(
                    relevant_events) > 0 else ""
                context = {
                    "question": question,
                    "timestamp": timestamp,
                }

        return component_explainer, context

    def invoke_explainer(self, component_explainer: str, context: dict):
        self.component_explainer_responded = False

        result = self.send_goal_to_component_explainer(component_explainer, context)

        list_of_explanations = []
        for explanation in result.explanations:
            list_of_explanations.append(explanation.explanation)
        return list_of_explanations

    def select_explainer_via_LLM(self, question: str, context: dict):
        component_descriptions = [
            f"{component} - {self.component_explainers_data[component]['description']}"
            for component in self.component_explainers_data]

        component_classification_prompt = f"""
        You are a classification model in a robot explainability system.
        In this system, the robot performs simple tasks around the house for a user.
        The robot's behaviour is described by a list of skills.
        Your job is to select which component a question should be forwarded to.
        Some components are tailored to particular skills and others to high-level planning.
        You must answer in only one word, which is the name of the component.

        Here is the list of possible components and a description of each one:
        {component_descriptions}

        This is the context of the robot's recent activity:
        {json.dumps(context, indent=2)}

        These are the only components you can select.
        Do not select a component that does not appear in this list.
        Only answer with one word, the name of the component.
        """

        headers = {}
        if self.api_key:
            headers['Authorization'] = f"Bearer {self.api_key}"
        response = requests.post(
            f'{self.llm_host}/v1/chat/completions',
            json={
                'model': self.llm_model,
                'messages': [
                    {
                        'role': 'system',
                        'content': component_classification_prompt,
                    },
                    {
                        'role': 'user',
                        'content': question,
                    }],
                'temperature': 0.0,
                'stream': False},
            headers=headers)
        if response.status_code != requests.codes.ok:
            raise RuntimeError(
                f'Ollama server response [{response.status_code}]: {response.text}')
        response_json = response.json()['choices'][0]

        selected_component_explainer = str(response_json['message']['content']).strip()
        if selected_component_explainer in self.component_explainers:
            self.get_logger().info(
                f"LLM selected the {selected_component_explainer} component explainer")
            return selected_component_explainer
        else:
            # The LLM did not choose a valid intent, default to planner explainer
            default_component = "component_explainer_c"
            self.get_logger().warn(
                f"LLM selected {selected_component_explainer}, which is invalid. "
                f"Defaulting to {default_component}")
            return default_component

    def aggregate_explanations(self, explanations: list) -> str:
        """
        Summarizes the explanations into a single string.

        Uses an LLM prompt to summarize the explanations.
        """
        # Prepare the prompt for the LLM to summarize the explanations
        ans_key = "Summarized Explanation:"
        summarization_prompt_system = """
        You are a summarization model in a robot explainability system.
        Your goal is to clearly and concisely explain the robot’s behavior.
        Use a single sentence from the robot’s first-person perspective.

        Requirements:
        1. Use simple, user-friendly language in **first person**, focused on clarity.
        2. Do not suggest the user ask for more information.
        3. Avoid apologies; provide straightforward, factual explanations.
        4. Clearly state the specific causes behind the robot’s behavior.
        5. Don't speculate beyond the information provided in the explanations.
        """
        # Join the explanations into a single string
        raw_explanations = " This happened because ".join(explanations)

        summarization_prompt_user = f"""
        Explanations: {raw_explanations}
        """

        headers = {}
        if self.api_key:
            headers['Authorization'] = f"Bearer {self.api_key}"
        response = requests.post(
            f'{self.llm_host}/v1/chat/completions',
            json={
                'model': self.llm_model,
                'messages': [
                    {
                        'role': 'system',
                        'content': summarization_prompt_system,
                    },
                    {
                        'role': 'user',
                        'content': summarization_prompt_user,
                    }],
                'temperature': 0.0,
                'stream': False},
            headers=headers)
        if response.status_code != requests.codes.ok:
            raise RuntimeError(
                f'Ollama server response [{response.status_code}]: {response.text}')
        response = response.json()
        response = response['choices'][0]['message']['content']

        for line in response.split('\n'):
            if ans_key in line:
                return line[len(ans_key):].strip()
        return response

    def on_new_event(self, msg):
        """Implement the callback when the subscriber receives a new task info."""
        # Implement in this function your strategy to store the events.
        # Here there is an example by timestamps, but other apporaches like using an ID
        # or a hash can be used as well, were some classes are defined and used to store and
        # update the information.

        # New events can come from different sources, e.g., topics or services, but it is
        # recommended to merge all the information into a single data structure.

        self.get_logger().info(f"Received new context info{msg.data}")

        # Process the message
        try:
            data = json.loads(msg.data) if msg.data else {}
        except json.JSONDecodeError:
            self.get_logger().warn(f"Invalid json object received: \n{msg.data}")
            return

        current_time_msg = self.get_clock().now().to_msg()
        current_time = f"{current_time_msg.sec}.{current_time_msg.nanosec}"
        self.events_buffer[current_time] = data

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

    def send_goal_to_component_explainer(self, component_explainer: str, context: dict):
        goal = GenerateComponentExplanation.Goal()
        goal.json_data = json.dumps(context)

        client = self.component_explainers[component_explainer]

        self.get_logger().info(f'Sending goal to {component_explainer}')

        # Wait for the action server to be available
        while not client.wait_for_server(timeout_sec=1.0):
            self.get_logger().info(f'{component_explainer} not available, waiting...')

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
                result.error_msg = f"Failed to get result from {component_explainer}"

        return result

    #################################
    #
    # Lifecycle transitions callbacks
    #
    def on_configure(self, state: State) -> TransitionCallbackReturn:
        """Configure the node."""
        self.action_server = ActionServer(self,
                                          GenerateExplanation,
                                          "/generate_explanation",
                                          goal_callback=self.on_request_goal,
                                          execute_callback=self.on_request_exec)

        # Component Explainers
        self._component_explainer_a_client = ActionClient(
            self, GenerateComponentExplanation, '/component_explainer_a/explain')

        self._component_explainer_b_client = ActionClient(
            self, GenerateComponentExplanation, '/component_explainer_b/explain')

        self._component_explainer_c_client = ActionClient(
            self, GenerateComponentExplanation, '/component_explainer_c/explain')

        self.component_explainers = {
            "component_explainer_a": self._component_explainer_a_client,
            "component_explainer_b": self._component_explainer_b_client,
            "component_explainer_c": self._component_explainer_c_client,
        }

        self.get_logger().info("explainer_selector is configured, but not yet active")
        time.sleep(2)  # Give some time for everything to settle
        return TransitionCallbackReturn.SUCCESS

    def on_activate(self, state: State) -> TransitionCallbackReturn:
        """Activate the node."""
        # Subscribers
        # Add here subscribers to topics you want to listen that will be needed as context
        self._events_sub_cbGroup = MutuallyExclusiveCallbackGroup()
        self._events_subscriber = self.create_subscription(
            String,
            '/event',
            self.on_new_event,
            10, callback_group=self._events_sub_cbGroup)

        self.get_logger().info("explainer_selector is active and running...")
        return super().on_activate(state)

    def on_deactivate(self, state: State) -> TransitionCallbackReturn:
        """Stop the timer to stop calling the `run` function (main task of your application)."""
        self.get_logger().info("Stopping skill...")

        self.get_logger().info("explainer_selector is stopped (inactive)")
        return super().on_deactivate(state)

    def on_shutdown(self, state: State) -> TransitionCallbackReturn:
        """Shutdown the node, after a shutting-down transition is requested."""
        # Clean up any publishers/subscribers/timers here
        self.destroy_subscription(self._events_subscriber)

        self.get_logger().info('Shutting down explainer_selector skill.')

        self.action_server.destroy()

        self.get_logger().info("explainer_selector finalized.")
        return TransitionCallbackReturn.SUCCESS
