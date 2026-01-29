from weight_store import update_weight, get_weight

update_weight("sample_1", jie=0.2, rlod=0.1)
update_weight("sample_2", jie=0.9, rlod=0.8)

print("sample_1 weight:", get_weight("sample_1"))
print("sample_2 weight:", get_weight("sample_2"))
print("unknown sample weight:", get_weight("sample_3"))