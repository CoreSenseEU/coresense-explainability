from launch import LaunchDescription
from launch.actions import EmitEvent, RegisterEventHandler, DeclareLaunchArgument
from launch.events import matches_action
from launch_ros.actions import LifecycleNode
from launch_ros.events.lifecycle import ChangeState
from launch_ros.event_handlers import OnStateTransition
from launch.substitutions import LaunchConfiguration
from lifecycle_msgs.msg import Transition


def generate_launch_description():
    pkg = 'explainer_selector'
    node = 'explainer_selector'
    ld = LaunchDescription()

    # Declare launch arguments for LLM configuration
    ld.add_action(DeclareLaunchArgument(
        'llm_model',
        default_value='gpt-4.1-mini',
        description='LLM model to use'
    ))

    ld.add_action(DeclareLaunchArgument(
        'llm_host',
        default_value='https://api.openai.com',
        description='LLM host URL'
    ))

    ld.add_action(DeclareLaunchArgument(
        'api_key',
        default_value='',
        description='API key for LLM service'
    ))

    # Add LLM parameters to the configuration
    llm_params = [
        {'llm_model': LaunchConfiguration('llm_model')},
        {'llm_host': LaunchConfiguration('llm_host')},
        {'api_key': LaunchConfiguration('api_key')}
    ]

    node = LifecycleNode(
        package=pkg,
        executable='start_explainer_selector',
        namespace='',
        name=node,
        parameters=llm_params,
        output='both', emulate_tty=True,
    )

    ld.add_action(node)

    # automatically perform the lifecycle transitions to configure and activate
    configure_event = EmitEvent(event=ChangeState(
        lifecycle_node_matcher=matches_action(node),
        transition_id=Transition.TRANSITION_CONFIGURE))

    ld.add_action(configure_event)

    activate_event = RegisterEventHandler(OnStateTransition(
        target_lifecycle_node=node, goal_state='inactive',
        entities=[EmitEvent(event=ChangeState(
            lifecycle_node_matcher=matches_action(node),
            transition_id=Transition.TRANSITION_ACTIVATE))],
        handle_once=True))

    ld.add_action(activate_event)

    return ld
