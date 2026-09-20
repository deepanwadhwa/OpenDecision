"""Run OpenDecision against a structured-state ViZDoom scenario."""

from __future__ import annotations

import argparse
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, replace
import math
from pathlib import Path
import sys
import tempfile
import time
from typing import Any, Mapping, Sequence


TICRATE = 35
CORRIDOR_CLOSE_COMBAT_DISTANCE = 300
CORRIDOR_ENGAGE_DISTANCE = 450

DEFEND_CENTER_ENEMIES = frozenset({"Demon", "MarineChainsawVzd"})
DEFEND_LINE_ENEMIES = frozenset({"Demon", "DoomImp"})
CORRIDOR_ENEMIES = frozenset({"ChaingunGuy", "ShotgunGuy", "Zombieman"})

SCENARIOS: dict[str, dict[str, Any]] = {
    "corridor": {
        "config": "deadly_corridor.cfg",
        "difficulty": 3,
        "enemy_names": CORRIDOR_ENEMIES,
        "goal_name": "GreenArmor",
        "instructions": "Choose the immediate action. In combat, face or shoot the nearby enemy and do not advance. Advance only when all enemies are farther than 450 map units.",
    },
    "center": {
        "config": "defend_the_center.cfg",
        "difficulty": 3,
        "enemy_names": DEFEND_CENTER_ENEMIES,
        "goal_name": None,
        "instructions": "Which single action best helps the player survive and eliminate enemies right now?",
    },
    "line": {
        "config": "defend_the_line.cfg",
        "difficulty": 3,
        "enemy_names": DEFEND_LINE_ENEMIES,
        "goal_name": None,
        "instructions": "Choose whether to attack the active enemy or wait.",
    },
}

MODE_ACTIONS: dict[str, dict[str, str]] = {
    "engage": {
        "attack": "Aim at the selected nearby enemy and fire.",
        "shoot_retreat": "Fire while backing away from the selected enemy.",
    },
    "approach": {
        "advance_fire": "Close on the selected enemy while aiming and firing.",
        "hold_fire": "Hold position while aiming and firing at the selected enemy.",
    },
    "evade": {
        "strafe_fire": "Fire while dodging sideways away from the nearest attacker.",
        "shoot_retreat": "Fire while backing away from the nearest attacker.",
    },
    "critical_evade": {
        "retreat_fire": "Retreat while firing to preserve critical health under immediate attack.",
        "strafe_fire": "Keep strafing sideways while firing under immediate attack.",
    },
    "advance": {
        "move_to_goal": "Aim toward the armor goal and move forward.",
        "wait": "Hold position only if the armor goal cannot be located.",
    },
}

DEFENSE_ACTIONS = {"attack": "Aim at the selected enemy and fire.", "wait": "Hold fire only when no enemy is a current threat."}

AIMING_ACTIONS = frozenset(
    {
        "turn_left", "turn_right", "aim_fire_left", "aim_fire_right", "attack", "hold_fire", "advance_fire", "move_to_goal",
    }
)

@dataclass(frozen=True)
class Enemy:
    """Structured geometry for an observable hostile actor."""

    id: int
    name: str
    angle: float
    distance: float


@dataclass(frozen=True)
class GameSnapshot:
    health: int
    ammo: int
    enemy_count: int
    nearest_enemy_angle: float | None
    nearest_enemy_distance: float | None
    taking_damage: bool
    kills: int = 0
    goal_angle: float | None = None
    goal_distance: float | None = None
    target_id: int | None = None
    target_name: str | None = None
    enemies: tuple[Enemy, ...] = ()

    def target(self, target_id: int) -> "GameSnapshot | None":
        """Return this live state aimed at a previously selected actor."""
        enemy = next((enemy for enemy in self.enemies if enemy.id == target_id), None)
        if enemy is None:
            return None
        return replace(
            self,
            nearest_enemy_angle=enemy.angle,
            nearest_enemy_distance=enemy.distance,
            target_id=enemy.id,
            target_name=enemy.name,
        )

    @property
    def nearest_direction(self) -> str:
        angle = self.nearest_enemy_angle
        if angle is None:
            return "none"
        if angle < -2.0:
            return "right"
        if angle > 2.0:
            return "left"
        return "ahead"

    @property
    def goal_direction(self) -> str:
        angle = self.goal_angle
        if angle is None:
            return "none"
        if angle < -18.0:
            return "right"
        if angle > 18.0:
            return "left"
        return "ahead"

    @property
    def tactical_priority(self) -> str:
        if self.taking_damage and self.health <= 40:
            return "critical evade; retreat while firing to preserve health"
        if self.taking_damage:
            return "evade; incoming damage overrides other priorities"
        if self.nearest_enemy_distance is None:
            return "advance to goal; no enemy remains"
        if self.nearest_enemy_distance <= CORRIDOR_CLOSE_COMBAT_DISTANCE:
            return "combat; neutralize the nearby enemy before advancing"
        if self.nearest_enemy_distance <= CORRIDOR_ENGAGE_DISTANCE:
            return "approach; close on the medium-range enemy while firing"
        return "advance to goal; enemies are currently distant"

    def decision_state(self) -> str:
        angle = (
            "none"
            if self.nearest_enemy_angle is None
            else f"{self.nearest_enemy_angle:+.1f} degrees"
        )
        distance = (
            "none"
            if self.nearest_enemy_distance is None
            else f"{self.nearest_enemy_distance:.0f} map units"
        )
        state = (
            f"Health: {self.health}/100. Ammo: {self.ammo}. "
            f"Enemies alive: {self.enemy_count}. Kills: {self.kills}. "
            f"Current target: {self.target_name or 'none'}. "
            f"Nearest enemy: {self.nearest_direction}, angle {angle}, "
            f"distance {distance}. Taking damage: "
            f"{'yes' if self.taking_damage else 'no'}. Tactical priority: {self.tactical_priority}."
        )
        if self.goal_distance is None:
            return state
        goal_angle = "none" if self.goal_angle is None else f"{self.goal_angle:+.1f} degrees"
        return f"{state} Goal armor: {self.goal_direction}, angle {goal_angle}, distance {self.goal_distance:.0f} map units."


def route_mode(snapshot: GameSnapshot) -> str:
    if snapshot.taking_damage and snapshot.health <= 40:
        return "critical_evade"
    if snapshot.taking_damage:
        return "evade"
    if snapshot.nearest_enemy_distance is not None and snapshot.nearest_enemy_distance <= CORRIDOR_ENGAGE_DISTANCE:
        return "engage" if snapshot.nearest_enemy_distance <= CORRIDOR_CLOSE_COMBAT_DISTANCE else "approach"
    return "advance"


def normalize_angle(angle: float) -> float:
    """Normalize an angle in degrees to [-180, 180)."""
    return (angle + 180.0) % 360.0 - 180.0


def extract_snapshot(
    game_variables: Sequence[float],
    objects: Sequence[Any],
    previous_health: int | None,
    enemy_names: frozenset[str] = DEFEND_CENTER_ENEMIES,
    goal_name: str | None = None,
) -> GameSnapshot:
    """Convert ViZDoom values and world objects into compact semantic state."""
    health, ammo, player_x, player_y, player_angle, *extra = game_variables
    kills = extra[0] if extra else 0
    enemy_objects = [obj for obj in objects if obj.name in enemy_names]
    enemies = tuple(
        sorted(
            (
                Enemy(
                    id=obj.id,
                    name=obj.name,
                    angle=normalize_angle(
                        math.degrees(
                            math.atan2(
                                obj.position_y - player_y,
                                obj.position_x - player_x,
                            )
                        )
                        - player_angle
                    ),
                    distance=math.hypot(
                        obj.position_x - player_x,
                        obj.position_y - player_y,
                    ),
                )
                for obj in enemy_objects
            ),
            key=lambda enemy: enemy.distance,
        )
    )

    nearest_angle: float | None = None
    nearest_distance: float | None = None
    if enemies:
        nearest_angle = enemies[0].angle
        nearest_distance = enemies[0].distance

    goal_angle: float | None = None
    goal_distance: float | None = None
    if goal_name is not None:
        goal = next((obj for obj in objects if obj.name == goal_name), None)
        if goal is not None:
            goal_dx = goal.position_x - player_x
            goal_dy = goal.position_y - player_y
            goal_distance = math.hypot(goal_dx, goal_dy)
            goal_angle = normalize_angle(math.degrees(math.atan2(goal_dy, goal_dx)) - player_angle)

    integer_health = max(0, round(health))
    return GameSnapshot(
        health=integer_health,
        ammo=max(0, round(ammo)),
        enemy_count=len(enemies),
        nearest_enemy_angle=nearest_angle,
        nearest_enemy_distance=nearest_distance,
        taking_damage=(
            previous_health is not None and integer_health < previous_health
        ),
        kills=max(0, round(kills)),
        goal_angle=goal_angle,
        goal_distance=goal_distance,
        target_id=enemies[0].id if enemies else None,
        target_name=enemies[0].name if enemies else None,
        enemies=enemies,
    )


def make_action_vector(
    action: str,
    snapshot: GameSnapshot,
    mode: str,
) -> list[float]:
    """Translate a semantic action into mouse-like turning and key presses."""
    turn_delta = 0.0
    target_angle = snapshot.goal_angle if mode == "advance" else snapshot.nearest_enemy_angle
    if action in {"attack", "hold_fire", "advance_fire", "move_to_goal"}:
        turn_delta = -max(min(target_angle or 0.0, 45.0), -45.0)
    elif action in {"turn_left", "aim_fire_left"}:
        turn_delta = -min(abs(target_angle or 0.0), 45.0)
    elif action in {"turn_right", "aim_fire_right"}:
        turn_delta = min(abs(target_angle or 0.0), 45.0)

    enemy_is_right = (snapshot.nearest_enemy_angle or 0.0) <= 0.0
    strafe_left = action in {"strafe_left", "shoot_strafe_left"}
    strafe_right = action in {"strafe_right", "shoot_strafe_right"}
    if action in {"shoot_strafe_away", "strafe_fire"}:
        strafe_left = enemy_is_right
        strafe_right = not enemy_is_right
    elif action == "shoot_strafe_toward":
        strafe_left = not enemy_is_right
        strafe_right = enemy_is_right

    return [
        turn_delta,
        float(
            action in {"shoot", "shoot_strafe_left", "shoot_strafe_right", "shoot_strafe_away", "shoot_strafe_toward", "shoot_move_forward", "shoot_retreat", "retreat_fire", "aim_fire_left", "aim_fire_right", "attack", "hold_fire", "advance_fire"}
        ),
        float(action in {"move_forward", "shoot_move_forward", "advance_fire", "move_to_goal"}),
        float(strafe_left),
        float(strafe_right),
        float(action in {"shoot_retreat", "retreat_fire"}),
    ]


def configure_game(
    vzd: Any,
    scenario_name: str = "corridor",
    *,
    doom_skill: int | None = None,
    seed: int = 0,
    execution_mode: str = "realtime",
    show_native_window: bool = False,
) -> Any:
    game = vzd.DoomGame()
    scenario = (
        Path(vzd.scenarios_path) / SCENARIOS[scenario_name]["config"]
    )
    if not game.load_config(str(scenario)):
        raise RuntimeError(f"Could not load ViZDoom scenario: {scenario}")

    # The installed ViZDoom package contains freedoom2.wad. An empty game path
    # makes the engine discover that bundled WAD without proprietary Doom data.
    game.set_doom_game_path("")
    game.set_doom_config_path(
        str(Path(tempfile.gettempdir()) / "opendecision-vizdoom.ini")
    )
    game.set_screen_resolution(vzd.ScreenResolution.RES_640X480)
    game.set_screen_format(vzd.ScreenFormat.RGB24)
    # Start observing and controlling immediately. A nonzero delay gives
    # skill-5 enemies free, uncontrollable tics at the start of an episode.
    game.set_episode_start_time(0)
    game.set_labels_buffer_enabled(True)
    game.set_objects_info_enabled(True)
    game.set_window_visible(show_native_window)
    game.set_mode(
        vzd.Mode.ASYNC_PLAYER
        if execution_mode == "realtime"
        else vzd.Mode.PLAYER
    )
    game.set_seed(seed)
    game.set_doom_skill(
        doom_skill or SCENARIOS[scenario_name]["difficulty"]
    )

    game.set_available_buttons(
        [
            vzd.Button.TURN_LEFT_RIGHT_DELTA,
            vzd.Button.ATTACK,
            vzd.Button.MOVE_FORWARD,
            vzd.Button.MOVE_LEFT,
            vzd.Button.MOVE_RIGHT,
            vzd.Button.MOVE_BACKWARD,
        ]
    )
    game.set_button_max_value(vzd.Button.TURN_LEFT_RIGHT_DELTA, 180)
    game.set_available_game_variables(
        [
            vzd.GameVariable.HEALTH,
            vzd.GameVariable.AMMO2,
            vzd.GameVariable.POSITION_X,
            vzd.GameVariable.POSITION_Y,
            vzd.GameVariable.ANGLE,
            vzd.GameVariable.KILLCOUNT,
        ]
    )
    game.init()
    return game


def render_overlay(
    frame: Any,
    snapshot: GameSnapshot,
    scenario_name: str,
    doom_skill: int,
    seed: int,
    execution_mode: str,
    choice_mode: str,
    mode: str,
    safety_reflex_active: bool,
    action: str,
    probabilities: Mapping[str, float],
    decision_latency_ms: float,
    decision_rate_hz: float,
    cv2: Any,
    np: Any,
) -> Any:
    """Attach a readable state/decision panel to a ViZDoom RGB frame."""
    frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
    height, width = frame_bgr.shape[:2]
    panel_width = 440
    canvas = np.zeros((height, width + panel_width, 3), dtype=np.uint8)
    canvas[:, :width] = frame_bgr
    canvas[:, width:] = (24, 24, 28)

    font = cv2.FONT_HERSHEY_SIMPLEX
    x = width + 18
    timing_label = (
        "REAL-TIME ASYNC GAMEPLAY | 35 FPS"
        if execution_mode == "realtime"
        else "SYNCHRONOUS PAUSED"
    )
    cv2.putText(
        canvas,
        "OpenDecision x ViZDoom",
        (x, 27),
        font,
        0.68,
        (80, 220, 255),
        2,
        cv2.LINE_AA,
    )
    cv2.putText(
        canvas,
        timing_label,
        (x, 48),
        font,
        0.36,
        (220, 220, 220),
        1,
        cv2.LINE_AA,
    )
    cv2.putText(
        canvas,
        "~400M MODEL | LOCAL | ZERO-SHOT",
        (x, 68),
        font,
        0.40,
        (220, 220, 220),
        1,
        cv2.LINE_AA,
    )
    cv2.putText(
        canvas,
        "NO GENERATIVE LLM",
        (x, 93),
        font,
        0.58,
        (110, 255, 130),
        2,
        cv2.LINE_AA,
    )
    cv2.putText(
        canvas,
        "STRUCTURED STATE - NO PIXELS",
        (x, 114),
        font,
        0.40,
        (80, 220, 255),
        1,
        cv2.LINE_AA,
    )

    angle = "-" if snapshot.nearest_enemy_angle is None else f"{snapshot.nearest_enemy_angle:+.1f} deg"
    distance = "-" if snapshot.nearest_enemy_distance is None else f"{snapshot.nearest_enemy_distance:.0f}"
    goal_angle = "-" if snapshot.goal_angle is None else f"{snapshot.goal_angle:+.1f} deg"
    goal_distance = "-" if snapshot.goal_distance is None else f"{snapshot.goal_distance:.0f}"
    state_lines = [
        f"health {snapshot.health:<4}  ammo {snapshot.ammo}",
        f"enemies {snapshot.enemy_count:<3}  kills {snapshot.kills}  target {snapshot.target_name or '-'}",
        f"enemy angle     {angle}  {snapshot.nearest_direction.upper()}",
        f"enemy distance  {distance}",
        f"goal angle      {goal_angle}  {snapshot.goal_direction.upper()}",
        f"goal distance   {goal_distance}",
        f"taking damage   {'YES' if snapshot.taking_damage else 'no'}",
    ]
    cv2.putText(canvas, "INPUT", (x, 136), font, 0.48, (80, 220, 255), 2)
    y = 154
    for line in state_lines:
        color = (
            (100, 180, 255)
            if line.endswith("YES")
            else (225, 225, 225)
        )
        cv2.putText(
            canvas,
            line,
            (x, y),
            font,
            0.48,
            color,
            1,
            cv2.LINE_AA,
        )
        y += 18

    chosen_probability = probabilities[action]
    cv2.putText(canvas, "DECISION", (x, 286), font, 0.48, (80, 220, 255), 2)
    cv2.putText(
        canvas,
        (
            f"POLICY MODE  {mode.upper()}"
            + (" | SAFETY REFLEX ACTIVE" if safety_reflex_active else "")
        ),
        (x, 306),
        font,
        0.42,
        (225, 225, 225),
        1,
        cv2.LINE_AA,
    )
    cv2.putText(
        canvas,
        f"{action.upper():<17} {chosen_probability:4.0%}",
        (x, 329),
        font,
        0.62,
        (110, 255, 130),
        2,
        cv2.LINE_AA,
    )
    cv2.putText(
        canvas,
        (
            f"{decision_latency_ms:,.0f} ms  |  {decision_rate_hz:.1f} decisions/s"
        ),
        (x, 349),
        font,
        0.41,
        (190, 190, 190),
        1,
        cv2.LINE_AA,
    )

    y = 371
    for name, probability in sorted(probabilities.items(), key=lambda item: item[1], reverse=True):
        color = (110, 255, 130) if name == action else (205, 205, 205)
        cv2.putText(
            canvas,
            f"{name:<17} {probability:5.1%}",
            (x, y),
            font,
            0.39,
            color,
            1,
            cv2.LINE_AA,
        )
        y += 15
    return canvas


@dataclass(frozen=True)
class Decision:
    snapshot: GameSnapshot
    mode: str
    action: str
    probabilities: Mapping[str, float]
    latency_ms: float


def choose_action(
    engine: Any,
    snapshot: GameSnapshot,
    scenario_name: str,
    choice_mode: str,
) -> Decision:
    """Run one OpenDecision request without touching the game object."""
    decision_state = snapshot.decision_state()
    started = time.perf_counter()
    choose = engine.choice_fast if choice_mode == "fast" else engine.choice
    if scenario_name == "corridor":
        mode = route_mode(snapshot)
        result = choose(state=decision_state, instructions=f"Which immediate action best executes the selected {mode} tactical mode?", criteria=MODE_ACTIONS[mode])
    else:
        mode = "defend"
        result = choose(state=decision_state.replace(f"Tactical priority: {snapshot.tactical_priority}.", "Tactical priority: defend the current target."), instructions=SCENARIOS[scenario_name]["instructions"], criteria=DEFENSE_ACTIONS)
    return Decision(
        snapshot=snapshot,
        mode=mode,
        action=result["choice"],
        probabilities=result["probabilities"],
        latency_ms=(time.perf_counter() - started) * 1000.0,
    )


def warm_choice_profile(engine: Any, choice_mode: str) -> None:
    """Warm the selected model path before real-time gameplay begins."""
    choose = engine.choice_fast if choice_mode == "fast" else engine.choice
    choose(
        state=(
            "Health: 100/100. Ammo: 52. Enemies alive: 1. "
            "Nearest enemy: ahead, angle +0.0 degrees, distance 150 map units."
        ),
        instructions="Which immediate action best executes engage tactical mode?",
        criteria=MODE_ACTIONS["engage"],
    )


def run_realtime(
    args: argparse.Namespace,
    game: Any,
    engine: Any,
    scenario: Mapping[str, Any],
    doom_skill: int,
    cv2: Any,
    np: Any,
) -> int:
    """Run a wall-clock control loop while ViZDoom advances at 35 tics/s."""
    writer = None
    pending: Future[Decision] | None = None
    last_overlay = None
    current_mode = "starting"
    current_action = "wait"
    current_probabilities: Mapping[str, float] = {"wait": 1.0}
    current_latency_ms = 0.0
    decisions_applied = 0
    decision_number = 0
    rendered_frames = 0
    previous_render_health: int | None = None
    previous_decision_health: int | None = None
    latest_snapshot: GameSnapshot | None = None
    clear_turn_after_advance = False
    action_after_turn: list[float] | None = None
    safety_reflex_active = False
    wait_for_turn_effect = False
    neutral_action = [0.0] * 6
    output = Path(args.record) if args.record else None
    gameplay_elapsed = 0.0

    game.new_episode()
    game.set_action(neutral_action)
    started = time.perf_counter()
    deadline = started + args.seconds

    try:
        with ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="opendecision",
        ) as executor:
            while time.perf_counter() < deadline:
                now = time.perf_counter()

                if game.is_episode_finished():
                    player_died = game.is_player_dead()
                    outcome = "PLAYER DIED" if player_died else "GOAL REACHED"
                    print(
                        "Player died; real-time corridor failed."
                        if player_died
                        else "Goal reached; real-time corridor complete.",
                        flush=True,
                    )
                    if last_overlay is not None:
                        outcome_overlay = last_overlay.copy()
                        cv2.putText(
                            outcome_overlay,
                            outcome,
                            (165, 250),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            1.25,
                            (80, 80, 255) if player_died else (110, 255, 130),
                            3,
                            cv2.LINE_AA,
                        )
                        minimum_total_frames = min(
                            10 * TICRATE,
                            round(args.seconds * TICRATE),
                        )
                        hold_frames = max(
                            2 * TICRATE,
                            minimum_total_frames - rendered_frames,
                        )
                        for _ in range(hold_frames):
                            if writer is not None:
                                writer.write(outcome_overlay)
                            rendered_frames += 1
                        last_overlay = outcome_overlay
                    break

                if pending is not None and pending.done():
                    decision = pending.result()
                    pending = None
                    current_mode = decision.mode
                    current_action = decision.action
                    current_probabilities = decision.probabilities
                    current_latency_ms = decision.latency_ms
                    safety_reflex_active = False
                    decisions_applied += 1
                    decision_number += 1
                    print(
                        f"[real-time decision {decision_number:03}] "
                        f"{decision.snapshot.decision_state()} -> "
                        f"{decision.mode}/{decision.action} "
                        f"({decision.latency_ms:,.0f} ms)",
                        flush=True,
                    )
                    actuation_snapshot = latest_snapshot or decision.snapshot
                    if decision.mode in {"engage", "approach", "evade", "defend"}:
                        live_target = (
                            actuation_snapshot.target(decision.snapshot.target_id)
                            if decision.snapshot.target_id is not None
                            else None
                        )
                        if live_target is None:
                            print(
                                "Discarded stale combat decision; target changed.",
                                flush=True,
                            )
                            continue
                        actuation_snapshot = live_target
                    action_vector = make_action_vector(
                        decision.action,
                        actuation_snapshot,
                        decision.mode,
                    )
                    game.set_action(action_vector)
                    if decision.action in AIMING_ACTIONS:
                        clear_turn_after_advance = True
                        action_after_turn = action_vector.copy()
                        action_after_turn[0] = 0.0
                        if decision.action in {"turn_left", "turn_right"}:
                            action_after_turn = neutral_action
                        # ViZDoom applies a delta turn on the following tic.
                        # Do not ask from the still-pre-turn observation.
                        wait_for_turn_effect = True

                # In ASYNC_PLAYER this waits for/catches up to the real-time
                # tic and publishes a fresh state. The game clock continues
                # independently while the inference worker is busy.
                game.advance_action(1)
                now = time.perf_counter()
                if clear_turn_after_advance:
                    game.set_action(action_after_turn or neutral_action)
                    clear_turn_after_advance = False
                    action_after_turn = None

                if game.is_episode_finished():
                    continue

                state = game.get_state()
                if state is None:
                    continue
                live_snapshot = extract_snapshot(
                    state.game_variables,
                    state.objects or (),
                    previous_render_health,
                    scenario["enemy_names"], scenario["goal_name"],
                )
                previous_render_health = live_snapshot.health
                latest_snapshot = live_snapshot

                if live_snapshot.taking_damage and pending is not None:
                    # This is a disclosed, one-tic safety reflex: act on a
                    # damage event while the semantic decision is still being
                    # scored. The model remains responsible for the next
                    # tactical action.
                    game.set_action(
                        make_action_vector(
                            "retreat_fire" if live_snapshot.health <= 40 else "shoot_strafe_away",
                            live_snapshot,
                            "evade",
                        )
                    )
                    safety_reflex_active = True

                if wait_for_turn_effect:
                    wait_for_turn_effect = False
                elif pending is None:
                    decision_snapshot = extract_snapshot(
                        state.game_variables,
                        state.objects or (),
                        previous_decision_health,
                        scenario["enemy_names"], scenario["goal_name"],
                    )
                    previous_decision_health = decision_snapshot.health
                    pending = executor.submit(
                        choose_action,
                        engine,
                        decision_snapshot,
                        args.scenario,
                        args.choice_mode,
                    )

                elapsed = max(time.perf_counter() - started, 1e-9)
                decision_rate_hz = decisions_applied / elapsed
                overlay = render_overlay(
                    state.screen_buffer,
                    live_snapshot,
                    args.scenario,
                    doom_skill,
                    args.seed,
                    "realtime",
                    args.choice_mode,
                    current_mode,
                    safety_reflex_active,
                    current_action,
                    current_probabilities,
                    current_latency_ms,
                    decision_rate_hz,
                    cv2,
                    np,
                )
                last_overlay = overlay

                if output is not None and writer is None:
                    output.parent.mkdir(parents=True, exist_ok=True)
                    writer = cv2.VideoWriter(
                        str(output),
                        cv2.VideoWriter_fourcc(*"mp4v"),
                        TICRATE,
                        (overlay.shape[1], overlay.shape[0]),
                    )
                    if not writer.isOpened():
                        raise RuntimeError(f"Could not open video output: {output}")
                if writer is not None:
                    writer.write(overlay)
                    rendered_frames += 1

                if not args.no_window:
                    cv2.imshow("OpenDecision playing Doom in real time", overlay)
                    key = cv2.waitKey(1) & 0xFF
                    if key in {ord("q"), 27}:
                        break
            gameplay_elapsed = time.perf_counter() - started
            game.set_action(neutral_action)
    finally:
        if writer is not None:
            writer.release()
        if not args.no_window:
            cv2.destroyAllWindows()

    print(
        f"Real-time decisions: {decisions_applied} in {gameplay_elapsed:.2f}s "
        f"({decisions_applied / max(gameplay_elapsed, 1e-9):.2f}/s)",
        flush=True,
    )
    if output is not None:
        print(f"Recorded demo to {output.resolve()}")
    return 0


def run(args: argparse.Namespace) -> int:
    try:
        import cv2
        import numpy as np
        import vizdoom as vzd
    except ImportError as exc:
        raise SystemExit(
            "Missing Doom demo dependencies. Run: "
            "uv pip install -r demos/doom/requirements.txt"
        ) from exc

    from opendecision.engine import OpenDecisionEngine

    scenario = SCENARIOS[args.scenario]
    doom_skill = args.doom_skill or scenario["difficulty"]
    game = configure_game(
        vzd,
        args.scenario,
        doom_skill=doom_skill,
        seed=args.seed,
        execution_mode=args.execution_mode,
    )
    writer = None
    target_frames = max(1, round(args.seconds * TICRATE))
    rendered_frames = 0
    decision_number = 0
    stop_requested = False
    last_overlay = None

    try:
        print("Loading OpenDecision (the first run may download the model)...")
        engine = OpenDecisionEngine(device=args.device)
        print("Warming selected choice profile before the episode starts...")
        warm_choice_profile(engine, args.choice_mode)
        if args.execution_mode == "realtime":
            return run_realtime(
                args,
                game,
                engine,
                scenario,
                doom_skill,
                cv2,
                np,
            )

        game.new_episode()
        synchronous_started = time.perf_counter()
        previous_health: int | None = None

        while rendered_frames < target_frames and not stop_requested:
            if game.is_episode_finished():
                if args.scenario == "corridor":
                    player_died = game.is_player_dead()
                    outcome = "PLAYER DIED" if player_died else "GOAL REACHED"
                    print(
                        "Player died; corridor failed."
                        if player_died
                        else "Goal reached; corridor complete.",
                        flush=True,
                    )
                    if last_overlay is not None:
                        outcome_overlay = last_overlay.copy()
                        cv2.putText(
                            outcome_overlay,
                            outcome,
                            (165, 250),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            1.25,
                            (80, 80, 255) if player_died else (110, 255, 130),
                            3,
                            cv2.LINE_AA,
                        )
                        minimum_total_frames = min(
                            10 * TICRATE,
                            target_frames,
                        )
                        hold_frames = min(
                            max(
                                2 * TICRATE,
                                minimum_total_frames - rendered_frames,
                            ),
                            target_frames - rendered_frames,
                        )
                        for _ in range(hold_frames):
                            if writer is not None:
                                writer.write(outcome_overlay)
                            rendered_frames += 1
                    break
                print("Episode ended; starting a fresh one.")
                game.new_episode()
                previous_health = None

            state = game.get_state()
            if state is None:
                continue
            snapshot = extract_snapshot(
                state.game_variables,
                state.objects or (),
                previous_health,
                scenario["enemy_names"], scenario["goal_name"],
            )
            decision = choose_action(
                engine,
                snapshot,
                args.scenario,
                args.choice_mode,
            )
            decision_state = snapshot.decision_state()
            mode = decision.mode
            action = decision.action
            probabilities = decision.probabilities
            decision_latency_ms = decision.latency_ms
            decision_number += 1
            print(
                f"[decision {decision_number:03}] "
                f"{decision_state} -> {mode}/{action} "
                f"({decision_latency_ms:,.0f} ms)",
                flush=True,
            )
            previous_health = snapshot.health
            game.set_action(make_action_vector(action, snapshot, mode))

            action_frames = min(
                1
                if action in AIMING_ACTIONS
                else args.action_tics,
                target_frames - rendered_frames,
            )
            for _ in range(action_frames):
                game.advance_action(1)
                if game.is_episode_finished():
                    break
                frame_state = game.get_state()
                if frame_state is None:
                    break
                overlay = render_overlay(
                    frame_state.screen_buffer,
                    snapshot,
                    args.scenario,
                    doom_skill,
                    args.seed,
                    "synchronous",
                    args.choice_mode,
                    mode,
                    False,
                    action,
                    probabilities,
                    decision_latency_ms,
                    decision_number
                    / max(time.perf_counter() - synchronous_started, 1e-9),
                    cv2,
                    np,
                )
                last_overlay = overlay

                if args.record and writer is None:
                    output = Path(args.record)
                    output.parent.mkdir(parents=True, exist_ok=True)
                    writer = cv2.VideoWriter(
                        str(output),
                        cv2.VideoWriter_fourcc(*"mp4v"),
                        TICRATE,
                        (overlay.shape[1], overlay.shape[0]),
                    )
                    if not writer.isOpened():
                        raise RuntimeError(
                            f"Could not open video output: {output}"
                        )
                if writer is not None:
                    writer.write(overlay)
                rendered_frames += 1

                if not args.no_window:
                    cv2.imshow("OpenDecision playing Doom", overlay)
                    key = cv2.waitKey(round(1000 / TICRATE)) & 0xFF
                    if key in {ord("q"), 27}:
                        stop_requested = True
                        break
    finally:
        if writer is not None:
            writer.release()
        game.close()
        if not args.no_window:
            cv2.destroyAllWindows()

    if args.record:
        print(f"Recorded demo to {Path(args.record).resolve()}")
    return 0


def parse_device(value: str) -> str | int:
    """Accept Transformers device names as well as numeric device indexes."""
    try:
        return int(value)
    except ValueError:
        return value


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--scenario",
        choices=SCENARIOS,
        default="corridor",
        help="ViZDoom task to run (default: corridor).",
    )
    parser.add_argument("--seconds", type=float, default=15.0, help="Game-time seconds to run (default: 15).")
    parser.add_argument("--action-tics", type=int, default=3, help="Game ticks per decision (default: 3).")
    parser.add_argument("--record", metavar="MP4", help="Write the annotated run to an MP4 file.")
    parser.add_argument("--no-window", action="store_true", help="Do not open the annotated display window.")
    parser.add_argument(
        "--doom-skill",
        type=int,
        choices=range(1, 6),
        default=None,
        help="Doom difficulty from 1 to 5 (scenario default: 3).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=0,
        help="Deterministic ViZDoom seed shown in the overlay (default: 0).",
    )
    parser.add_argument(
        "--execution-mode",
        choices=("realtime", "synchronous"),
        default="realtime",
        help=(
            "Run Doom continuously in wall-clock real time, or pause it during "
            "inference (default: realtime)."
        ),
    )
    parser.add_argument(
        "--choice-mode",
        choices=("fast", "balanced"),
        default="fast",
        help=(
            "Use one zero-shot profile for low latency, or OpenDecision's "
            "multi-profile arbitration (default: fast)."
        ),
    )
    parser.add_argument(
        "--device",
        default=None,
        type=parse_device,
        help="Transformers device override, for example cpu, mps, or 0.",
    )
    args = parser.parse_args(argv)
    if args.seconds <= 0:
        parser.error("--seconds must be positive")
    if args.action_tics <= 0:
        parser.error("--action-tics must be positive")
    return args


if __name__ == "__main__":
    sys.exit(run(parse_args()))
