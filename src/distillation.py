import torch.nn.functional as F

def distillation_loss(student_logits, teacher_logits, T=2.0):
    teacher_probs = F.softmax(teacher_logits / T, dim=-1)
    student_log_probs = F.log_softmax(student_logits / T, dim=-1)

    return F.kl_div(
        student_log_probs,
        teacher_probs,
        reduction="batchmean"
    ) * (T * T)
