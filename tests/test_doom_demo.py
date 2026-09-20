from types import SimpleNamespace

import pytest

from demos.doom.doom_demo import CORRIDOR_ENEMIES, Enemy, GameSnapshot, extract_snapshot, make_action_vector, normalize_angle, parse_device, route_mode


def _actor(name, x, y, actor_id=0):
    return SimpleNamespace(id=actor_id, name=name, position_x=x, position_y=y)


def test_extract_snapshot_finds_nearest_enemy_relative_to_player():
    snapshot = extract_snapshot([80, 12, 10, 20, 90], [_actor("DoomPlayer", 10, 20, 1), _actor("Demon", 110, 20, 2), _actor("MarineChainsawVzd", 10, 70, 3)], previous_health=95)
    assert snapshot.health == 80
    assert snapshot.ammo == 12
    assert snapshot.enemy_count == 2
    assert snapshot.nearest_enemy_distance == pytest.approx(50)
    assert snapshot.nearest_enemy_angle == pytest.approx(0)
    assert snapshot.taking_damage is True


@pytest.mark.parametrize(("angle", "expected"), [(181, -179), (-181, 179), (360, 0), (540, -180)])
def test_normalize_angle(angle, expected):
    assert normalize_angle(angle) == expected


def test_corridor_snapshot_includes_goal_and_kills():
    snapshot = extract_snapshot([84, 48, 100, 0, 0, 2], [_actor("DoomPlayer", 100, 0, 1), _actor("ShotgunGuy", 200, 100, 2), _actor("GreenArmor", 500, 0, 3)], previous_health=100, enemy_names=CORRIDOR_ENEMIES, goal_name="GreenArmor")
    assert snapshot.kills == 2
    assert snapshot.goal_distance == pytest.approx(400)
    assert snapshot.goal_angle == pytest.approx(0)
    assert snapshot.target_name == "ShotgunGuy"


def test_snapshot_can_retarget_a_live_actor_by_stable_id():
    snapshot = GameSnapshot(80, 20, 2, -10, 100, False, target_id=1, target_name="Zombieman", enemies=(Enemy(1, "Zombieman", -10, 100), Enemy(2, "ShotgunGuy", 25, 160)))
    assert snapshot.target(2).target_name == "ShotgunGuy"


def test_tactical_attack_uses_geometry_actuator_to_aim_and_fire():
    snapshot = GameSnapshot(100, 26, 2, 21.8, 172, False)
    assert make_action_vector("attack", snapshot, "engage") == [-21.8, 1.0, 0.0, 0.0, 0.0, 0.0]


@pytest.mark.parametrize(("snapshot", "expected"), [(GameSnapshot(52, 50, 4, 0, 274, True), "evade"), (GameSnapshot(40, 50, 4, 0, 274, True), "critical_evade"), (GameSnapshot(76, 50, 4, -14, 245, False), "engage"), (GameSnapshot(76, 50, 4, -8, 414, False), "approach"), (GameSnapshot(76, 50, 4, -8, 500, False), "advance")])
def test_router_enforces_game_constraints(snapshot, expected):
    assert route_mode(snapshot) == expected


@pytest.mark.parametrize(("value", "expected"), [("-1", -1), ("0", 0), ("cpu", "cpu"), ("mps", "mps")])
def test_parse_device(value, expected):
    assert parse_device(value) == expected
