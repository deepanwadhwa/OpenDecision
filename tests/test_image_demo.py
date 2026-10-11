from demos.images.run import alarm_decision, condition_decision, evaluate_answers


def answers(presence=.9, winner='bear', probability=.9):
    other = 'cat' if winner == 'bear' else 'bear'
    return {'animal_present': {'type': 'noul', 'noul': presence},
            'animal_type': {'type': 'choice', 'choice': winner,
                            'probabilities': {winner: probability, other: 1-probability}}}


def test_alarm_requires_both_predicates():
    assert alarm_decision(answers())['action'] == 'sound_alarm'
    assert alarm_decision(answers(presence=.1))['action'] == 'no_alarm'
    assert alarm_decision(answers(winner='cat'))['action'] == 'no_alarm'


def test_uncertain_or_missing_choice_does_not_sound_alarm():
    result = alarm_decision(answers(probability=.55))
    assert result['action'] == 'no_alarm'
    assert result['trace']['status'] == 'unknown'
    assert alarm_decision({})['trace']['status'] == 'unknown'


def test_alarm_trace_keeps_both_inputs_and_threshold_policy():
    result = alarm_decision(answers(), noul_threshold=.95)
    assert result['action'] == 'no_alarm'
    assert result['policy']['noul_threshold'] == .95
    assert [child['fact'] for child in result['trace']['children']] == ['animal_present', 'animal_is_bear']


def test_ambiguous_visual_expectations_remain_unscored():
    checks = evaluate_answers({'q': {'type': 'noul', 'noul': .9}},
                             {'q': {'expected': None, 'note': 'Ambiguous'}}, .5)
    assert checks['q']['observed'] is True
    assert checks['q']['passed'] is None


def test_collection_requires_bin_and_overflow():
    def decide(presence, condition, probability):
        return condition_decision(
            {'bin_present': {'noul': presence},
             'bin_condition': {'choice': condition, 'probabilities': {condition: probability}}},
            presence_question='bin_present', choice_question='bin_condition',
            target_choice='overflowing', action='request_collection',
            otherwise='no_collection_request',
        )
    assert decide(.9, 'overflowing', .9)['action'] == 'request_collection'
    assert decide(.1, 'overflowing', .9)['action'] == 'no_collection_request'
    assert decide(.9, 'contained', .9)['action'] == 'no_collection_request'
    assert decide(.9, 'overflowing', .55)['trace']['status'] == 'unknown'


def test_missing_fence_answer_does_not_create_repair_task():
    result = condition_decision(
        {}, presence_question='fence_present', choice_question='fence_condition',
        target_choice='damaged', action='create_repair_task', otherwise='no_repair_task',
    )
    assert result['action'] == 'no_repair_task'
    assert result['trace']['status'] == 'unknown'
