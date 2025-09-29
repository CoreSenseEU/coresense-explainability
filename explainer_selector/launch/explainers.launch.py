import os
from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource


def generate_launch_description():

    ld = LaunchDescription()

    for dep in [
                "component_explainer_a",
                "component_explainer_b",
                "component_explainer_c"
                ]:
        ld.add_action(IncludeLaunchDescription(
          PythonLaunchDescriptionSource([os.path.join(
            get_package_share_directory(dep), 'launch'), f'/{dep}.launch.py'])
        ))

    return ld
