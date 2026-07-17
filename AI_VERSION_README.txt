PANDA CAMP — AI EXPERIMENT VERSION

Run:
    python panda_camp.py

Group assignment:
- Control group: run the game and do not press the activation shortcut.
- AI group: after the game opens, press Ctrl+Shift+A once.

Behavior:
- The AI module records response and inter-click latency during TRAINING.
- It provides no suggestions during TUTORIAL or TRAINING.
- During STORM only, an unusually long pause can activate one suggestion.
- Surgery: the target glows bright green when the moving line is close.
- Power Repair: one valid same-color pair receives yellow rings and a connecting line.
- Kitchen Prep: high-value ingredients and close ingredient clusters become gold.
- The player must still perform every click or keypress.

Research notes:
- AI activation and intervention events are written to the activity CSV.
- Baselines use the participant's median latency, which is more robust than a mean.
- Current trigger: maximum of a per-game minimum delay and 1.6x baseline.
- Current intervention cooldown: 15 seconds.
- These constants can be changed near the top of ai_teammate.py.

Environment:
    pip install pygame pillow
