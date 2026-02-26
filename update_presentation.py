from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
import datetime

def add_progress_bar(shape, percentage):
    """Helper to show percentage"""
    return f"{percentage}%"

def update_presentation_comprehensive():
    """Update presentation with comprehensive current project progress"""
    
    # Load presentation
    prs = Presentation('phase2.pptx')
    
    # Current date
    current_date = datetime.datetime.now().strftime("%B %d, %Y")
    
    # Project metrics
    metrics = {
        'overall': '92%',
        'last_updated': current_date,
        'components': [
            {
                'name': 'JIE Detection System',
                'completion': 95,
                'status': '✅ Production Ready',
                'description': 'TracIn-based influence estimation with last-layer gradients',
                'pending': '⏳ Adaptive scheduling system'
            },
            {
                'name': 'RLOD Detection System',
                'completion': 95,
                'status': '✅ Complete & Integrated',
                'description': 'kNN + spectral analysis for representation-level outliers',
                'pending': '✅ None'
            },
            {
                'name': 'Robust Training System',
                'completion': 85,
                'status': '⚙️ Core Complete',
                'description': 'Soft weighting, mixed precision, defensive distillation',
                'pending': '⏳ Integration testing, Deployment validation'
            },
            {
                'name': 'Integration Layer',
                'completion': 90,
                'status': '✅ Complete',
                'description': 'API endpoints, Celery tasks, combined detection pipeline',
                'pending': '✅ None'
            },
            {
                'name': 'Frontend UI',
                'completion': 100,
                'status': '✅ Fully Functional',
                'description': '4 pages, 4 components, 7 detection API methods, responsive design',
                'pending': '✅ None'
            },
        ]
    }
    
    # Update slides
    for slide_idx, slide in enumerate(prs.slides, 1):
        slide_obj = prs.slides[slide_idx - 1]
        slide_text = ' '.join([shape.text for shape in slide_obj.shapes if shape.has_text_frame])
        
        # Update Project Status/Progress/Timeline slides
        if any(keyword in slide_text for keyword in ['Timeline', 'Progress', 'Status', 'Remaining', 'Next Steps']):
            print(f"Updating Slide {slide_idx}: Progress Information")
            
            # Find text shapes to update (exclude title)
            text_shapes = [s for s in slide_obj.shapes if s.has_text_frame and s != slide_obj.shapes[0]]
            
            if text_shapes:
                # Use first text shape for content
                main_shape = text_shapes[0]
                text_frame = main_shape.text_frame
                text_frame.clear()
                
                # Title paragraph
                p = text_frame.paragraphs[0]
                p.text = f"📊 PROJECT PROGRESS: {metrics['overall']} Complete"
                p.font.size = Pt(28)
                p.font.bold = True
                p.font.color.rgb = RGBColor(0, 120, 215)
                
                # Overall progress bar
                p = text_frame.add_paragraph()
                p.text = f"\nOverall Progress: {add_progress_bar(None, int(metrics['overall'].rstrip('%')))}"
                p.font.size = Pt(18)
                p.font.bold = True
                p.space_before = Pt(12)
                
                # Component breakdown
                p = text_frame.add_paragraph()
                p.text = "\nComponent Status Breakdown:"
                p.font.size = Pt(16)
                p.font.bold = True
                p.font.color.rgb = RGBColor(0, 100, 200)
                p.space_before = Pt(12)
                
                for comp in metrics['components']:
                    # Component name and status
                    p = text_frame.add_paragraph()
                    p.text = f"• {comp['name']}"
                    p.font.size = Pt(14)
                    p.font.bold = True
                    p.level = 0
                    p.space_before = Pt(8)
                    
                    # Progress bar
                    p = text_frame.add_paragraph()
                    p.text = f"  {add_progress_bar(None, comp['completion'])} | {comp['status']}"
                    p.font.size = Pt(13)
                    p.level = 1
                    p.space_before = Pt(2)
                    
                    # Pending work
                    p = text_frame.add_paragraph()
                    p.text = f"  Pending: {comp['pending']}"
                    p.font.size = Pt(11)
                    p.level = 2
                    p.font.italic = True
                
                # Last updated
                p = text_frame.add_paragraph()
                p.text = f"\n📅 Last Updated: {metrics['last_updated']}"
                p.font.size = Pt(12)
                p.font.italic = True
                p.space_before = Pt(14)
    
    # Also add a new summary slide at the end if there's space
    # Check if slide 20 exists and update it with summary
    if len(prs.slides) >= 20:
        slide_20 = prs.slides[19]  # 0-indexed
        slide_20_text = ' '.join([shape.text for shape in slide_20.shapes if shape.has_text_frame])
        
        if 'Summary' in slide_20_text or len(slide_20_text.split()) < 50:  # Short content slide
            print(f"Updating Slide 20: Summary")
            
            text_shapes = [s for s in slide_20.shapes if s.has_text_frame and s != slide_20.shapes[0]]
            if text_shapes:
                main_shape = text_shapes[0]
                text_frame = main_shape.text_frame
                text_frame.clear()
                
                # Summary title
                p = text_frame.paragraphs[0]
                p.text = "🎯 CURRENT PROGRESS SUMMARY"
                p.font.size = Pt(28)
                p.font.bold = True
                p.font.color.rgb = RGBColor(0, 120, 215)
                
                # Key metrics
                p = text_frame.add_paragraph()
                p.text = f"\n✅ Overall Completion: {metrics['overall']}"
                p.font.size = Pt(18)
                p.font.bold = True
                
                # Completed systems
                p = text_frame.add_paragraph()
                p.text = "\n🏆 Fully Operational Systems:"
                p.font.size = Pt(14)
                p.font.bold = True
                p.font.color.rgb = RGBColor(0, 150, 0)
                
                completed = [c for c in metrics['components'] if c['completion'] >= 95]
                for comp in completed:
                    p = text_frame.add_paragraph()
                    p.text = f"  ✓ {comp['name']}"
                    p.font.size = Pt(13)
                
                # In-progress systems
                p = text_frame.add_paragraph()
                p.text = "\n⚙️ In-Progress Systems:"
                p.font.size = Pt(14)
                p.font.bold = True
                p.font.color.rgb = RGBColor(255, 140, 0)
                
                in_progress = [c for c in metrics['components'] if c['completion'] < 95]
                for comp in in_progress:
                    p = text_frame.add_paragraph()
                    p.text = f"  ⚡ {comp['name']} ({comp['completion']}%)"
                    p.font.size = Pt(13)
                
                # Next steps
                p = text_frame.add_paragraph()
                p.text = "\n📋 Next Steps:"
                p.font.size = Pt(14)
                p.font.bold = True
                
                next_steps = [
                    'Implement adaptive scheduling for JIE system',
                    'Complete integration testing (JIE + RLOD + Training)',
                    'Production deployment validation'
                ]
                for step in next_steps:
                    p = text_frame.add_paragraph()
                    p.text = f"  → {step}"
                    p.font.size = Pt(12)
    
    # Save updated presentation
    prs.save('phase2.pptx')
    
    print("\n" + "="*60)
    print("✅ PRESENTATION UPDATED SUCCESSFULLY!")
    print("="*60)
    print(f"\n📊 Overall Project Status: {metrics['overall']}")
    print(f"📅 Last Updated: {metrics['last_updated']}")
    print("\n📈 Component Breakdown:")
    for comp in metrics['components']:
        print(f"\n  {comp['name']}")
        print(f"  Completion: {add_progress_bar(None, comp['completion'])}")
        print(f"  Status: {comp['status']}")
        print(f"  Pending: {comp['pending']}")
    print("\n" + "="*60)

if __name__ == '__main__':
    update_presentation_comprehensive()
