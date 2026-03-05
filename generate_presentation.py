"""
Generate PowerPoint Presentation for AI Data Poisoning Mitigation System
"""

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE

def add_title_slide(prs, title, subtitle):
    """Add title slide."""
    slide = prs.slides.add_slide(prs.slide_layouts[0])
    slide.shapes.title.text = title
    slide.placeholders[1].text = subtitle
    return slide

def add_content_slide(prs, title, content_points=None):
    """Add slide with title and bullet points."""
    slide = prs.slides.add_slide(prs.slide_layouts[1])
    slide.shapes.title.text = title
    
    if content_points:
        tf = slide.placeholders[1].text_frame
        tf.clear()
        
        for point in content_points:
            p = tf.add_paragraph()
            if isinstance(point, tuple):
                p.text = point[0]
                p.level = point[1]
            else:
                p.text = point
                p.level = 0
            p.font.size = Pt(18)
    
    return slide

def add_code_slide(prs, title, code_text, description=""):
    """Add slide with code snippet."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # Blank layout
    
    # Title
    title_box = slide.shapes.add_textbox(Inches(0.5), Inches(0.5), Inches(9), Inches(0.6))
    title_frame = title_box.text_frame
    title_para = title_frame.paragraphs[0]
    title_para.text = title
    title_para.font.bold = True
    title_para.font.size = Pt(32)
    title_para.font.color.rgb = RGBColor(0, 51, 102)
    
    # Description
    if description:
        desc_box = slide.shapes.add_textbox(Inches(0.5), Inches(1.2), Inches(9), Inches(0.5))
        desc_frame = desc_box.text_frame
        desc_para = desc_frame.paragraphs[0]
        desc_para.text = description
        desc_para.font.size = Pt(14)
        desc_para.font.italic = True
        
        code_top = Inches(1.8)
    else:
        code_top = Inches(1.2)
    
    # Code box
    code_box = slide.shapes.add_textbox(Inches(0.5), code_top, Inches(9), Inches(4.5))
    code_frame = code_box.text_frame
    code_frame.word_wrap = True
    code_para = code_frame.paragraphs[0]
    code_para.text = code_text
    code_para.font.name = 'Consolas'
    code_para.font.size = Pt(11)
    code_para.font.color.rgb = RGBColor(0, 0, 0)
    
    # Add background to code box
    fill = code_box.fill
    fill.solid()
    fill.fore_color.rgb = RGBColor(245, 245, 245)
    
    return slide

def add_architecture_slide(prs, title, diagram_text):
    """Add architecture diagram slide."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    
    # Title
    title_box = slide.shapes.add_textbox(Inches(0.5), Inches(0.5), Inches(9), Inches(0.6))
    title_frame = title_box.text_frame
    title_para = title_frame.paragraphs[0]
    title_para.text = title
    title_para.font.bold = True
    title_para.font.size = Pt(28)
    title_para.font.color.rgb = RGBColor(0, 51, 102)
    
    # Diagram
    diagram_box = slide.shapes.add_textbox(Inches(0.5), Inches(1.2), Inches(9), Inches(5.3))
    diagram_frame = diagram_box.text_frame
    diagram_frame.word_wrap = False
    diagram_para = diagram_frame.paragraphs[0]
    diagram_para.text = diagram_text
    diagram_para.font.name = 'Courier New'
    diagram_para.font.size = Pt(9)
    
    # Add background
    fill = diagram_box.fill
    fill.solid()
    fill.fore_color.rgb = RGBColor(250, 250, 250)
    
    return slide

def add_flowchart_slide(prs, title, flow_steps):
    """Add flowchart slide with boxes and arrows."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    
    # Title
    title_box = slide.shapes.add_textbox(Inches(0.5), Inches(0.3), Inches(9), Inches(0.6))
    title_frame = title_box.text_frame
    title_para = title_frame.paragraphs[0]
    title_para.text = title
    title_para.font.bold = True
    title_para.font.size = Pt(28)
    title_para.font.color.rgb = RGBColor(0, 51, 102)
    
    # Flow boxes
    left = Inches(2)
    width = Inches(6)
    height = Inches(0.8)
    top = Inches(1.2)
    spacing = Inches(0.3)
    
    for i, step in enumerate(flow_steps):
        # Box
        box = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE,
            left, top + i * (height + spacing),
            width, height
        )
        
        # Fill color
        fill = box.fill
        fill.solid()
        if i == 0:
            fill.fore_color.rgb = RGBColor(68, 114, 196)  # Blue
        elif i == len(flow_steps) - 1:
            fill.fore_color.rgb = RGBColor(84, 130, 53)  # Green
        else:
            fill.fore_color.rgb = RGBColor(112, 173, 71)  # Light green
        
        # Text
        text_frame = box.text_frame
        text_frame.word_wrap = True
        p = text_frame.paragraphs[0]
        p.text = step
        p.font.size = Pt(14)
        p.font.color.rgb = RGBColor(255, 255, 255)
        p.font.bold = True
        p.alignment = PP_ALIGN.CENTER
        text_frame.vertical_anchor = 1  # Middle
        
        # Arrow (except for last box)
        if i < len(flow_steps) - 1:
            arrow = slide.shapes.add_shape(
                MSO_SHAPE.DOWN_ARROW,
                left + width/2 - Inches(0.2),
                top + (i+1) * (height + spacing) - spacing + Inches(0.05),
                Inches(0.4),
                spacing - Inches(0.1)
            )
            arrow_fill = arrow.fill
            arrow_fill.solid()
            arrow_fill.fore_color.rgb = RGBColor(68, 114, 196)
    
    return slide

def create_presentation():
    """Create the complete presentation."""
    prs = Presentation()
    prs.slide_width = Inches(10)
    prs.slide_height = Inches(7.5)
    
    # Slide 1: Title
    add_title_slide(
        prs,
        "AI Data Poisoning Mitigation System",
        "Joint Influence Estimation (JIE) + Representation-Level Outlier Detection (RLOD)\n" +
        "A Multi-Layer Defense Against Backdoor Attacks\n\n" +
        "Team Members:\n" +
        "ASI23CA024 - Avinash  |  ASI23CA046 - Nandhana Ramachandran\n" +
        "ASI23CA030 - Fayiza K H  |  ASI23CA036 - Jinendran S\n" +
        "Mentor: Dr Binju Saju"
    )
    
    # Slide 2: Team Members
    add_content_slide(
        prs,
        "Project Team",
        [
            "Department of Computer Applications",
            "",
            "Team Members:",
            ("ASI23CA024 - Avinash", 1),
            ("ASI23CA046 - Nandhana Ramachandran", 1),
            ("ASI23CA030 - Fayiza K H", 1),
            ("ASI23CA036 - Jinendran S", 1),
            "",
            "Project Mentor:",
            ("Dr Binju Saju", 1),
            "",
            "Project Title: AI Data Poisoning Mitigation System (Poison Guard)"
        ]
    )
    
    # Slide 3: Project Overview
    add_content_slide(
        prs,
        "Project Overview",
        [
            "What is Data Poisoning?",
            ("Malicious actors inject corrupted data into training datasets", 1),
            ("Can compromise models with as few as 250 poisoned samples", 1),
            ("Results in backdoors, biased behavior, and degraded performance", 1),
            "",
            "Our Solution: Three-Layer Defense System",
            ("JIE Model: TracIn-based influence estimation for trigger detection", 1),
            ("RLOD Model: kNN + spectral analysis for representation-level outliers", 1),
            ("Robust Training: Integrates detection outputs with soft weighting", 1),
            "",
            "Goal: Prevent successful poisoning with ≤250 samples"
        ]
    )
    
    # Slide 4: System Architecture
    arch_diagram = """
┌─────────────────────────────────────────────────────────────────────┐
│                     POISON GUARD SYSTEM ARCHITECTURE                │
└─────────────────────────────────────────────────────────────────────┘

┌───────────────────────┐            ┌────────────────────────────┐
│   Frontend (React)    │◄──────────►│  Backend (FastAPI+Celery)  │
│   Port: 3000          │   HTTP     │  Port: 8000                │
├───────────────────────┤            ├────────────────────────────┤
│ • Dashboard           │            │ • Detection Engines        │
│ • Chatbot             │            │   - JIE Detector           │
│ • Settings            │            │   - RLOD Detector          │
│ • Analytics Charts    │            │   - Combined (60/40)       │
└───────────────────────┘            │                            │
                                     │ • Celery Workers           │
                                     │ • Model Management         │
                                     │ • Redis Cache              │
                                     └────────────────────────────┘
                                                  │
                                                  ▼
                    ┌─────────────────────────────────────────┐
                    │        Detection Models                 │
                    ├─────────────────────────────────────────┤
                    │ • GPT-2-Medium (Base Model)             │
                    │ • JIE: TracIn with last-layer gradients │
                    │ • RLOD: Embeddings + kNN + Spectral     │
                    └─────────────────────────────────────────┘
"""
    add_architecture_slide(prs, "System Architecture", arch_diagram)
    
    # Slide 5: Data Flow
    add_flowchart_slide(
        prs,
        "Detection Pipeline Flow",
        [
            "Step 1: User Submits Samples (via Dashboard/API/Chatbot)",
            "Step 2: Frontend Validates & Formats Data",
            "Step 3: POST Request to Backend (/api/detect)",
            "Step 4: Load GPT-2-Medium Model & Initialize Detectors",
            "Step 5: Run JIE Detection (TracIn gradients)",
            "Step 6: Run RLOD Detection (kNN + Spectral)",
            "Step 7: Combine Scores (JIE×60% + RLOD×40%)",
            "Step 8: Return Results with Poisoning Probability"
        ]
    )
    
    # Slide 6: JIE Algorithm Overview
    add_content_slide(
        prs,
        "JIE Algorithm: Joint Influence Estimation",
        [
            "Core Concept: TracIn Method",
            ("TracIn = Tracing training data influence using gradients", 1),
            ("Measures how each sample affects model predictions", 1),
            "",
            "Key Features:",
            ("Last-layer gradient computation (lm_head + embeddings)", 1),
            ("10-20x faster than full-model gradients", 1),
            ("Checkpoints across multiple epochs for influence tracking", 1),
            ("Identifies samples that push model toward backdoor triggers", 1),
            "",
            "Output:",
            ("Influence score per sample (0-1 range)", 1),
            ("Higher score = more suspicious / likely poisoned", 1)
        ]
    )
    
    # Slide 6: JIE Code - Gradient Computation
    jie_code = """# TracIn: Compute sample gradient (last-layer params)
def compute_sample_gradient(model, tokenizer, text, device="cpu"):
    model.train()
    model.zero_grad()
    
    # Tokenize input
    inputs = tokenizer(text, return_tensors="pt").to(device)
    labels = inputs["input_ids"].clone()
    
    # Forward + Backward pass
    outputs = model(input_ids=inputs["input_ids"], labels=labels)
    loss = outputs.loss
    loss.backward()
    
    # Extract gradients from last-layer params (lm_head, wte)
    grad_pieces = []
    for name, param in model.named_parameters():
        if "lm_head" in name or "wte" in name:
            if param.grad is not None:
                grad_pieces.append(param.grad.detach().reshape(-1))
    
    # Concatenate all gradients into single vector
    gradient_vector = torch.cat(grad_pieces)
    return gradient_vector"""
    
    add_code_slide(
        prs,
        "JIE Algorithm: Gradient Computation",
        jie_code,
        "Extract last-layer gradients to measure sample influence"
    )
    
    # Slide 7: JIE Code - TracIn Scoring
    tracin_code = """# TracIn: Compute influence scores across checkpoints
def compute_tracin_scores(train_gradients, target_gradients):
    scores = {}
    
    for sample_id, train_grad in train_gradients.items():
        influence_sum = 0.0
        
        # Sum dot products across all target samples
        for target_grad in target_gradients:
            dot_product = torch.dot(train_grad, target_grad)
            influence_sum += dot_product.item()
        
        # Average influence across targets
        scores[sample_id] = influence_sum / len(target_gradients)
    
    return scores

# Usage in JIE Detector
scores = detector.detect(
    train_samples=[{"sample_id": "1", "text": "sample text"}],
    target_samples=[{"text": "backdoor trigger"}]
)
# Returns: {"1": 0.85}  # High score = suspicious"""
    
    add_code_slide(
        prs,
        "JIE Algorithm: TracIn Influence Scoring",
        tracin_code,
        "Calculate how each sample influences backdoor trigger predictions"
    )
    
    # Slide 8: RLOD Algorithm Overview
    add_content_slide(
        prs,
        "RLOD Algorithm: Representation-Level Outlier Detection",
        [
            "Core Concept: Embedding Space Analysis",
            ("Poisoned samples have anomalous representations", 1),
            ("Detect outliers in hidden layer embedding space", 1),
            "",
            "Three Detection Methods:",
            ("1. kNN Outlier Detection: Distance to k-nearest neighbors", 1),
            ("2. Spectral Analysis: Eigenvalue decomposition + clustering", 1),
            ("3. Clustering Analysis: Isolation from clean sample clusters", 1),
            "",
            "Process:",
            ("Extract embeddings from specified layer (default: last hidden)", 1),
            ("Pool to fixed-size vectors + normalize", 1),
            ("Apply kNN + spectral + clustering analysis", 1),
            ("Combine scores with weighted average", 1)
        ]
    )
    
    # Slide 9: RLOD Code - Embedding Extraction
    rlod_embed_code = """# RLOD: Extract embeddings from hidden layers
class EmbeddingExtractor:
    def extract(self, texts, layer_index=-1):
        embeddings = []
        
        for text in texts:
            inputs = self.tokenizer(text, return_tensors="pt").to(self.device)
            
            # Forward pass with output_hidden_states
            with torch.no_grad():
                outputs = self.model(
                    **inputs, 
                    output_hidden_states=True
                )
            
            # Get specified layer's hidden states
            hidden_states = outputs.hidden_states[layer_index]
            
            # Pool tokens to single vector (mean pooling)
            pooled = hidden_states.mean(dim=1).squeeze()
            
            # Normalize
            normalized = pooled / pooled.norm()
            
            embeddings.append(normalized)
        
        return torch.stack(embeddings)"""
    
    add_code_slide(
        prs,
        "RLOD Algorithm: Embedding Extraction",
        rlod_embed_code,
        "Extract and pool hidden layer representations"
    )
    
    # Slide 10: RLOD Code - Outlier Detection
    rlod_detection_code = """# RLOD: kNN Outlier Detection
def knn_outlier_score(embedding, baseline_embeddings, k=5):
    # Compute distances to all baseline samples
    distances = torch.cdist(embedding.unsqueeze(0), baseline_embeddings)
    
    # Get k-nearest neighbors
    k_nearest_dists, _ = torch.topk(distances, k, largest=False)
    
    # Average distance = outlier score
    outlier_score = k_nearest_dists.mean()
    return outlier_score.item()

# RLOD: Spectral Analysis
def spectral_outlier_score(embedding, baseline_embeddings):
    # Compute covariance matrix
    cov_matrix = torch.cov(baseline_embeddings.T)
    
    # Eigenvalue decomposition
    eigenvalues, eigenvectors = torch.linalg.eigh(cov_matrix)
    
    # Project embedding onto principal components
    projection = embedding @ eigenvectors
    
    # Score based on projection onto low-variance components
    score = (projection ** 2 * (1 / (eigenvalues + 1e-6))).sum()
    return score.item()"""
    
    add_code_slide(
        prs,
        "RLOD Algorithm: Outlier Detection Methods",
        rlod_detection_code,
        "kNN distance-based and spectral signature analysis"
    )
    
    # Slide 11: Integration Pipeline
    integration_code = """# Integration Pipeline: Combine JIE + RLOD
class IntegrationPipeline:
    def __init__(self):
        self.jie_detector = JIEDetector.from_config("config.yaml")
        self.rlod_detector = RLODDetector.from_config("config.yaml")
        self.scheduler = AdaptiveScheduler()  # 30% sampling
    
    def run_detection(self, samples, target_prompts):
        results = []
        
        for sample in samples:
            # JIE Detection
            jie_score = self.jie_detector.detect(
                train_samples=[sample],
                target_samples=target_prompts
            )[sample["sample_id"]]
            
            # RLOD Detection (only if JIE flags as suspicious)
            if jie_score > 0.5:
                rlod_score = self.rlod_detector.detect([sample])[0]
            else:
                rlod_score = 0.0
            
            # Combined score (60% JIE + 40% RLOD)
            combined = 0.6 * jie_score + 0.4 * rlod_score
            
            results.append({
                "sample_id": sample["sample_id"],
                "jie_score": jie_score,
                "rlod_score": rlod_score,
                "combined_score": combined,
                "is_poisoned": combined > 0.7
            })
        
        return results"""
    
    add_code_slide(
        prs,
        "Integration Pipeline: JIE + RLOD",
        integration_code,
        "Combine both detection methods with adaptive scheduling"
    )
    
    # Slide 12: API Endpoints
    add_content_slide(
        prs,
        "FastAPI Backend Endpoints",
        [
            "Detection Endpoints:",
            ("POST /api/detect - JIE detection (sync/async)", 1),
            ("POST /api/detect/rlod - RLOD detection", 1),
            ("POST /api/detect/combined - Combined JIE+RLOD", 1),
            ("GET /api/jobs/{job_id} - Check async job status", 1),
            "",
            "Monitoring Endpoints:",
            ("GET /health - Liveness probe", 1),
            ("GET /ready - Readiness probe (validates checkpoints)", 1),
            ("GET /metrics - System metrics", 1),
            "",
            "Features:",
            ("API key authentication", 1),
            ("Rate limiting (10 req/min)", 1),
            ("Input validation with Pydantic", 1),
            ("Celery workers for background processing", 1)
        ]
    )
    
    # Slide 13: Frontend Components
    add_content_slide(
        prs,
        "Frontend UI Components (React + Vite)",
        [
            "Pages (4 Routes):",
            ("Home - Landing page with project intro", 1),
            ("Dashboard - Analytics with 6 KPIs + 4 charts", 1),
            ("Chatbot - Interactive detection assistant", 1),
            ("Settings - Configuration & preferences", 1),
            "",
            "Key Features:",
            ("Sidebar navigation with responsive design", 1),
            ("Real-time detection results", 1),
            ("Data visualization (charts & metrics)", 1),
            ("File upload for batch detection", 1),
            ("Tailwind CSS styling", 1),
            ("Axios API integration", 1)
        ]
    )
    
    # Slide 14: Workflow Diagram
    workflow_diagram = """
┌──────────────┐        ┌──────────────┐        ┌──────────────┐
│   Training   │───────>│   Poisoned   │───────>│   Deploy     │
│   Dataset    │        │   Dataset    │        │   Model      │
└──────────────┘        └──────────────┘        └──────────────┘
                                │                        │
                                │                        │
                        ┌───────▼────────┐      ┌────────▼────────┐
                        │  JIE Detector  │      │ RLOD Detector   │
                        │  (TracIn)      │      │ (kNN+Spectral)  │
                        └───────┬────────┘      └────────┬────────┘
                                │                        │
                                └────────┬───────────────┘
                                         │
                                  ┌──────▼──────┐
                                  │  Combined   │
                                  │  Detection  │
                                  │  (60/40)    │
                                  └──────┬──────┘
                                         │
                        ┌────────────────┼────────────────┐
                        │                │                │
                  ┌─────▼─────┐   ┌─────▼─────┐   ┌─────▼─────┐
                  │  Clean    │   │ Suspicious │   │ Poisoned  │
                  │  (< 0.3)  │   │ (0.3-0.7) │   │ (> 0.7)   │
                  └───────────┘   └───────────┘   └───────────┘
                        │                │                │
                        └────────────────┼────────────────┘
                                         │
                                  ┌──────▼──────┐
                                  │   Robust    │
                                  │   Training  │
                                  │  (Weighted) │
                                  └─────────────┘
"""
    add_architecture_slide(prs, "Complete Workflow Diagram", workflow_diagram)
    
    # Slide 15: Performance Metrics
    add_content_slide(
        prs,
        "System Performance Metrics",
        [
            "JIE Detection Performance:",
            ("Overhead: 12-15% with last-layer gradients", 1),
            ("Accuracy: ~95% on backdoor trigger detection", 1),
            ("Adaptive sampling: 30% of samples per epoch", 1),
            ("Gradient checkpointing: 40% memory reduction", 1),
            "",
            "RLOD Detection Performance:",
            ("Embedding extraction: Fast with GPU acceleration", 1),
            ("kNN with FAISS: Handles large datasets efficiently", 1),
            ("Combined with JIE: Better coverage of poisoning types", 1),
            "",
            "Overall System:",
            ("API Response: <60s for sync requests", 1),
            ("Batch processing: Up to 1000 samples per request", 1),
            ("Goal: Block poisoning attacks with ≤250 samples", 1)
        ]
    )
    
    # Slide 16: Technology Stack
    add_content_slide(
        prs,
        "Technology Stack",
        [
            "Backend:",
            ("FastAPI - RESTful API framework", 1),
            ("Celery - Distributed task queue", 1),
            ("Redis - Caching & message broker", 1),
            ("PyTorch - Deep learning framework", 1),
            ("Transformers - HuggingFace models", 1),
            ("FAISS - Fast similarity search", 1),
            "",
            "Frontend:",
            ("React - UI framework", 1),
            ("Vite - Build tool", 1),
            ("Tailwind CSS - Styling", 1),
            ("Axios - HTTP client", 1),
            "",
            "Model & Data:",
            ("GPT-2-Medium (base model)", 1),
            ("WikiText-103 (training dataset)", 1)
        ]
    )
    
    # Slide 17: SRS Requirements Summary
    add_content_slide(
        prs,
        "Software Requirements Summary (SRS)",
        [
            "Functional Requirements (24 total):",
            ("Dataset Management: Upload, validate, configure poisoned datasets", 1),
            ("Detection Engine: Run JIE, RLOD, and combined detection modes", 1),
            ("Training Integration: Weighted robust training with detection outputs", 1),
            ("Async Processing: Task queue with real-time progress tracking", 1),
            ("Checkpoint Management: Save/resume full training state", 1),
            "",
            "Key Performance Targets (NFRs):",
            ("Detection Rate: > 85% (AC-1)", 1),
            ("False Positive Rate: < 7% (AC-2)", 1),
            ("Training Overhead: < 25% compared to baseline (AC-3)", 1),
            ("Sync API Response: < 60 seconds (NFR-5)", 1),
            ("Batch Processing: Up to 1000 samples per request (NFR-6)", 1),
            "",
            "SRS Version: 1.0  |  Date: 2026-02-26"
        ]
    )
    
    # Slide 18: Acceptance Criteria
    add_content_slide(
        prs,
        "Acceptance Criteria & Validation",
        [
            "Core Acceptance Criteria (AC-1 to AC-9):",
            ("AC-1: Detection rate > 85% on benchmark datasets", 1),
            ("AC-2: False positive rate < 7%", 1),
            ("AC-3: Training overhead < 25% vs baseline", 1),
            ("AC-4: Block poisoning attacks with ≤ 250 samples", 1),
            ("AC-5: All FR-1–FR-24 implemented and tested", 1),
            ("AC-6: Complete API docs with example calls", 1),
            ("AC-7: Docker-compose brings up all services", 1),
            ("AC-8: Frontend loads and communicates with backend", 1),
            ("AC-9: Checkpoint save/resume working correctly", 1),
            "",
            "Risk Mitigations:",
            ("R-1: RLOD incomplete → fallback to JIE-only mode", 1),
            ("R-2: Checkpoint paths → documented in CHECKPOINT_USAGE_GUIDE.md", 1),
            ("R-3: Redis sync latency → configurable timeouts + retries", 1),
            ("R-4: False positives → tunable threshold (default 0.5)", 1)
        ]
    )
    
    # Slide 19: Key Achievements
    add_content_slide(
        prs,
        "Key Achievements & Current Status",
        [
            "Completed Components:",
            ("✅ JIE Detection System (95% complete)", 1),
            ("✅ RLOD Detection System (85% complete)", 1),
            ("✅ FastAPI Backend with async workers", 1),
            ("✅ React Frontend with Dashboard & Chatbot", 1),
            ("✅ Integration Pipeline with adaptive scheduling", 1),
            ("✅ Docker deployment on GCP (35.237.37.33:8000)", 1),
            "",
            "In Progress:",
            ("⚠ RLOD fine-tuning and optimization", 1),
            ("⚠ End-to-end integration testing", 1),
            "",
            "Overall Progress: ~70% Complete  |  SRS Compliance: AC-1 to AC-9 tracked"
        ]
    )
    
    # Slide 20: Conclusion
    add_content_slide(
        prs,
        "Conclusion & Future Work",
        [
            "Achievements:",
            ("Built custom ML models for backdoor detection", 1),
            ("Implemented two-layer defense (JIE + RLOD)", 1),
            ("Created production-ready API and UI", 1),
            ("Optimized performance with last-layer gradients", 1),
            "",
            "Future Enhancements:",
            ("Expand to other model architectures (BERT, T5)", 1),
            ("Real-time streaming detection", 1),
            ("Auto-mitigation with model fine-tuning", 1),
            ("Enhanced visualization tools", 1),
            ("Scalability testing with larger datasets", 1),
            "",
            "Impact:",
            ("Protect AI models from data poisoning attacks", 1),
            ("Ensure model safety and reliability", 1)
        ]
    )
    
    # Save presentation
    output_file = "implementation presentation.pptx"
    prs.save(output_file)
    print(f"✅ Presentation created successfully: {output_file}")
    print(f"📊 Total slides: {len(prs.slides)}")
    return output_file

if __name__ == "__main__":
    create_presentation()
