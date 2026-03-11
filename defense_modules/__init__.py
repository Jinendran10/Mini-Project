import logging as _logging
_pkg_logger = _logging.getLogger(__name__)

# NOTE: ALL try/except blocks catch (Exception, KeyboardInterrupt) — NOT just
# ImportError — because the transformers → torch.distributed → sympy import
# chain can raise KeyboardInterrupt in Jupyter kernels.  This ensures a single
# heavy-dependency failure never silently kills the entire package.

try:
    from .jie_detector import JIEDetector
except (Exception, KeyboardInterrupt) as _e:
    _pkg_logger.warning(f"JIEDetector unavailable: {type(_e).__name__}: {_e}")
    JIEDetector = None

try:
    from .rlod_detector import RLODDetector
except (Exception, KeyboardInterrupt) as _e:
    _pkg_logger.warning(f"RLODDetector unavailable: {type(_e).__name__}: {_e}")
    RLODDetector = None

try:
    from .jailbreak_patterns import JAILBREAK_PATTERNS, scan_regex, SEMANTIC_ANCHORS
except (Exception, KeyboardInterrupt) as _e:
    _pkg_logger.warning(f"jailbreak_patterns unavailable: {type(_e).__name__}: {_e}")
    JAILBREAK_PATTERNS = []
    scan_regex = None
    SEMANTIC_ANCHORS = []

try:
    from .semantic_detector import run_full_prescreening, detect_semantic_injection
except (Exception, KeyboardInterrupt) as _e:
    _pkg_logger.warning(f"semantic_detector unavailable: {type(_e).__name__}: {_e}")
    run_full_prescreening = None
    detect_semantic_injection = None

try:
    from .rlod_dataset import generate_full_dataset as generate_rlod_dataset
except (Exception, KeyboardInterrupt) as _e:
    _pkg_logger.warning(f"rlod_dataset unavailable: {type(_e).__name__}: {_e}")
    generate_rlod_dataset = None

try:
    from .rlod_analysis import analyze_dataset as RLODAnalyzer
except (Exception, KeyboardInterrupt) as _e:
    _pkg_logger.warning(f"RLODAnalyzer unavailable: {type(_e).__name__}: {_e}")
    RLODAnalyzer = None
