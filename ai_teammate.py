"""Adaptive, non-playing AI suggestions for the Panda Camp experiment.

The teammate observes performance and camp conditions. It never clicks, selects,
or completes a task for the player.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import math
import statistics
import pygame


@dataclass
class AttemptState:
    started_ms: int = 0
    last_action_ms: int | None = None
    phase: str = ""
    assisted: bool = False
    suggestion_text: str = ""
    completed: bool = False


class AITeammate:
    """Tracks training latency and reveals guidance only after a first Storm try."""

    SLOW_MULTIPLIER = 1.45
    MIN_TRIGGER_MS = {
        "medical": 2800,
        "power": 3400,
        "kitchen": 2600,
    }
    CONDITION_GRACE_MS = 900
    LOW_MORALE = 40.0

    def __init__(self) -> None:
        self.enabled = False
        self.baselines: dict[str, list[int]] = defaultdict(list)
        self.attempts: dict[str, AttemptState] = {
            "medical": AttemptState(),
            "power": AttemptState(),
            "kitchen": AttemptState(),
        }
        self.completed_storm_attempts: dict[str, int] = defaultdict(int)
        self.active_minigame: str | None = None

    def toggle(self, state) -> bool:
        """Secretly enable/disable the experimental condition."""
        self.enabled = not self.enabled
        state.log_event("AI", f"Experimental condition {'enabled' if self.enabled else 'disabled'}")
        # Do not reveal the condition at activation time.
        return self.enabled

    def begin_attempt(self, name: str, phase: str) -> None:
        if name not in self.attempts:
            return
        self.active_minigame = name
        self.attempts[name] = AttemptState(
            started_ms=pygame.time.get_ticks(),
            phase=phase,
        )

    def record_action(self, name: str, phase: str) -> None:
        """Record response/inter-click latency without changing gameplay."""
        if not self.enabled or name not in self.attempts:
            return
        attempt = self.attempts[name]
        if attempt.started_ms <= 0:
            return

        now = pygame.time.get_ticks()
        anchor = attempt.last_action_ms if attempt.last_action_ms is not None else attempt.started_ms
        latency = max(1, now - anchor)
        attempt.last_action_ms = now

        if phase == "TRAINING":
            self.baselines[name].append(latency)

    def end_attempt(self, name: str) -> None:
        attempt = self.attempts.get(name)
        if attempt is not None and not attempt.completed:
            attempt.completed = True
            if self.enabled and attempt.phase == "STORM":
                self.completed_storm_attempts[name] += 1
        if self.active_minigame == name:
            self.active_minigame = None

    def baseline_ms(self, name: str) -> int | None:
        values = self.baselines.get(name, [])
        if not values:
            return None
        return int(statistics.median(values))

    def _trigger_threshold(self, name: str) -> int:
        baseline = self.baseline_ms(name)
        if baseline is None:
            return self.MIN_TRIGGER_MS[name]
        return max(self.MIN_TRIGGER_MS[name], int(baseline * self.SLOW_MULTIPLIER))

    def _critical_reason(self, name: str, state) -> str | None:
        """Return why camp conditions justify help for this active task."""
        if state.joy <= self.LOW_MORALE:
            return f"morale is critically low at {state.joy:.1f}%"

        if name == "medical":
            if state.patients >= 3:
                return f"the Safety panel is red with {state.patients} patients"
            if state.med_crates <= 2:
                return f"medical supplies are low ({state.med_crates} crates)"
        elif name == "power" and state.power_issues >= 3:
            return f"the Power panel is red with {state.power_issues} outages"
        elif name == "kitchen":
            if state.food_crates <= 2:
                return f"the Food panel is red with {state.food_crates} crates"
            if state.money < 10:
                return f"the budget is low at ${state.money}"
        return None

    def _activate(self, name: str, state, reason: str, pause_ms: int) -> None:
        messages = {
            "medical": (
                f"AI SUGGESTION: You already tried Surgery once. Because {reason}, "
                "the target will glow bright green whenever the moving line is in the right zone. "
                "You still press SPACE yourself."
            ),
            "power": (
                f"AI SUGGESTION: You already tried Power Repair once. Because {reason}, "
                "one valid matching pair will be outlined and connected in bright yellow. "
                "You still click both nodes yourself."
            ),
            "kitchen": (
                f"AI SUGGESTION: You already tried Kitchen Prep once. Because {reason}, "
                "high-value foods and useful close clusters will glow gold so you can prioritize them. "
                "You still collect the foods yourself."
            ),
        }
        attempt = self.attempts[name]
        attempt.assisted = True
        attempt.suggestion_text = messages[name]
        state.instruction_text = messages[name]
        state.log_event(
            "AI_INTERVENTION",
            f"Suggestion activated for {name}; reason={reason}; "
            f"baseline={self.baseline_ms(name)}ms; pause={pause_ms}ms; "
            f"prior_storm_attempts={self.completed_storm_attempts[name]}",
        )

    def update(self, state) -> None:
        """Activate help in Storm after one fully unassisted attempt."""
        if not self.enabled or state.phase != "STORM":
            return

        mapping = {
            "MED_MINIGAME": "medical",
            "POWER_MINIGAME": "power",
            "MONEY_MINIGAME": "kitchen",
        }
        name = mapping.get(state.sub_phase)
        if name is None:
            return

        attempt = self.attempts[name]
        if attempt.started_ms <= 0 or attempt.assisted:
            return

        # The first Storm attempt for each minigame must remain completely unassisted.
        if self.completed_storm_attempts[name] < 1:
            return

        now = pygame.time.get_ticks()
        anchor = attempt.last_action_ms if attempt.last_action_ms is not None else attempt.started_ms
        pause_ms = now - anchor

        critical_reason = self._critical_reason(name, state)
        if critical_reason and now - attempt.started_ms >= self.CONDITION_GRACE_MS:
            self._activate(name, state, critical_reason, pause_ms)
            return

        if pause_ms >= self._trigger_threshold(name):
            baseline = self.baseline_ms(name)
            reason = (
                f"your response pause ({pause_ms / 1000:.1f}s) is slower than your "
                f"training pattern ({baseline / 1000:.1f}s)"
                if baseline is not None
                else f"you have paused for {pause_ms / 1000:.1f}s"
            )
            self._activate(name, state, reason, pause_ms)

    def is_assisting(self, name: str) -> bool:
        return self.enabled and self.attempts.get(name, AttemptState()).assisted

    def draw_medical_suggestion(self, screen, state) -> None:
        if not self.is_assisting("medical") or state.phase != "STORM":
            return
        target_center = state.mg_target_pos + state.mg_target_width / 2
        slider_center = state.mg_slider_pos + 4
        distance = abs(slider_center - target_center)
        in_zone = distance <= max(10, state.mg_target_width / 2 + 3)
        if in_zone:
            glow = pygame.Surface((state.mg_target_width + 28, 68), pygame.SRCALPHA)
            pygame.draw.rect(glow, (50, 255, 90, 125), glow.get_rect(), border_radius=10)
            screen.blit(glow, (state.mg_target_pos - 14, 266))
            pygame.draw.rect(
                screen,
                (70, 255, 110),
                pygame.Rect(state.mg_target_pos, 280, state.mg_target_width, 40),
                width=5,
                border_radius=4,
            )

    def suggested_power_pair(self, state):
        if not self.is_assisting("power") or state.phase != "STORM":
            return None
        by_color = defaultdict(list)
        for idx, circle in enumerate(state.pg_circles):
            if circle.get("active"):
                by_color[circle["color"]].append(idx)
        pairs = [indices[:2] for indices in by_color.values() if len(indices) >= 2]
        if not pairs:
            return None

        def pair_distance(pair):
            return math.dist(
                state.pg_circles[pair[0]]["pos"],
                state.pg_circles[pair[1]]["pos"],
            )

        return min(pairs, key=pair_distance)

    def draw_power_suggestion(self, screen, state, radius: int) -> None:
        pair = self.suggested_power_pair(state)
        if pair is None:
            return
        p1 = state.pg_circles[pair[0]]["pos"]
        p2 = state.pg_circles[pair[1]]["pos"]
        pygame.draw.line(screen, (255, 245, 70), p1, p2, width=6)
        for point in (p1, p2):
            pygame.draw.circle(screen, (255, 245, 70), point, radius + 10, width=6)

    def kitchen_priority_ids(self, ingredients) -> set[int]:
        if not self.is_assisting("kitchen"):
            return set()

        selected = {id(item) for item in ingredients if item.get("value", 0) >= 8}
        # Highlight medium/high-value members of close clusters. Avoid highlighting
        # every low-value item merely because two objects happen to be nearby.
        for i, first in enumerate(ingredients):
            for second in ingredients[i + 1:]:
                if math.dist(first["rect"].center, second["rect"].center) <= 145:
                    if first.get("value", 0) >= 6:
                        selected.add(id(first))
                    if second.get("value", 0) >= 6:
                        selected.add(id(second))
        return selected

    def training_summary(self) -> str:
        parts = []
        for name in ("medical", "power", "kitchen"):
            values = self.baselines.get(name, [])
            baseline = self.baseline_ms(name)
            parts.append(
                f"{name}={baseline if baseline is not None else 'n/a'}ms "
                f"({len(values)} actions)"
            )
        return "; ".join(parts)