from .weighting import mitigation_weight

weight_table = {}
dirty_flags = set()

def update_weight(sample_id, jie, rlod):
    weight_table[sample_id] = mitigation_weight(jie, rlod)
    dirty_flags.add(sample_id)

def commit_weights():
    dirty_flags.clear()

def get_weight(sample_id):
    return weight_table.get(sample_id, 1.0)
