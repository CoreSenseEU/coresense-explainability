Coresense Explainability Framework
====================

This repository contains the implementation of the CORESENSE explainability framework, which includes component explainers and an explainer selector. The framework is designed to provide explanations for the behavior of robotic systems.

This repository includes templates that serve as code skeletons for developing custom explainers and an explainer selector.

The main elements of the framework are:
- Component Explainers: These are responsible for generating explanations tailored to specific modules of the robotic system. Each component explainer can be tailored to the specific needs of the module it is related to. Three example component explainers are provided, with very simple logic to illustrate how to create custom component explainers. In one of them (component explainer a), the component explainer can call another component explainer to create a chain of explanations. The other two component explainers (b and c) are simpler and do not call other explainers.
- Explainer Selector: This module selects the most appropriate component explainer based on the context and the question posed. It ensures that the explanations provided are relevant and informative. Again, an example explainer selector is provided, with simple logic to illustrate how to create a custom explainer selector.

Getting Started
----------------
To test the current implementation, you can first build the workspace and then launch the explainer selector along with the component explainers using the provided launch file. Remember to set your API key for the LLM service as a launch argument, or point to your local ollama server.

```bash
colcon build
source install/setup.bash
ros2 launch explainer_selector explainers.launch.py
ros2 launch explainer_selector explainer_selector.launch.py api_key:='your_key_here'

ros2 action send_goal /generate_explanation explainability_msgs/action/GenerateExplanation "question: 'Why did you do it?'
auto_triggered: false" 

ros2 topic pub -1 /event std_msgs/msg/String "data: '{\"skill_failure\":true, \"failed_skill\":\"pick\"}'" 

ros2 action send_goal /generate_explanation explainability_msgs/action/GenerateExplanation "question: 'Why did you do it?'
auto_triggered: false"
```

## Acknowledgement

<img src="https://github.com/user-attachments/assets/b11da974-9201-4f79-902e-c9c20e8aa7a4" alt="Funded by the European Union" width="240"/>

This work has received funding from the European Union's Horizon Europe research and innovation programme under grant agreement No 101070254 ([CORESENSE](https://coresense.eu)). Views and opinions expressed are however those of the author(s) only and do not necessarily reflect those of the European Union or the European Commission. Neither the European Union nor the granting authority can be held responsible for them.
