import json
import traceback
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app.quiz.quiz_generate_router import QuizGeneratePayload, QuizChunkInput
from app.quiz.quiz_prompt_builder import prepare_all_model_inputs
from app.quiz.quiz_generator import _real_model_call

# The exact input you provided
payload_data = {
  "mcqs_per_chunk": 2,
  "chunks": [
    {
      "chunk_id": "0",
      "chunk_text": "Scale Invariant Feature Transform • It is a technique for detecting salient, stable feature • For every such point, it also provides a set of \"features\" that \"characterize/describe\" a small image region around the point. • These features are invariant to rotation and scale. o Estimation of affine transformation/homography o Estimation of fundamental matrix in stereo\n• Structure from motion, tracking, motion segmentation • All these applications need to\n• (1) detect salient, stable points in two or more images, and\n(2) determine correspondences between them. • To determine correspondences correctly, we need some features characterizing a salient point. • These features must not change with:\n• Object position/pose\n• Minor image artifacts/noise/blur • Individual pixel color values are not\nan adequate feature to determine\ncorrespondences (why?). • One could try matching patches around the salient feature points - but these patches will themselves change if there is change in object pose or illumination. • So these patches will lead to several false matches/correspondences. a Diane ee erg cg hee ts • SIFT provides features characterizing a salient point that remain invariant to changes in Steps of SIFT algorithm\n1. Determine approximate location and scale of\nsalient feature points (also called keypoints)\n2. Refine their location and scale\n3. Determine orientation(s) for each keypoint. 4. Determine descriptors for each keypoint.",
      "context_prev_sentence": None,
      "context_next_sentence": "Step 1: Approximate keypoint • Look for intensity changes using the difference of Gaussians at Convolution operator: refers to the application of a filter (in this case Gaussian filter to an image)",
      "bloom_level": "understand",
      "chunk_type": "definition",
      "concepts": [
        "scale invariant feature transform",
        "keypoint",
        "feature",
        "correspondence"
      ],
      "keywords": [
        "Scale Invariant Feature Transform",
        "keypoint",
        "feature",
        "correspondence",
        "DoG",
        "Gaussian filter"
      ]
    },
    {
      "chunk_id": "1",
      "chunk_text": "Step 1: Approximate keypoint • Look for intensity changes using the difference of Gaussians at Convolution operator: refers to the application of a filter (in this case Gaussian filter to an image)\nDifference of GaussiansD=o\"G\"\nScale refers to thσeof the Gaussian. This is an example of the DoG filter in gimp. In SIFT, however, the DoG is computed from Gaussians at nearby scales. Step 1: Approximatekeypoint location Octav . Within an octave, the adjacent scales differ by a constant factor k.",
      "context_prev_sentence": "Determine descriptors for each keypoint.",
      "context_next_sentence": "Such a sequence of",
      "bloom_level": "apply",
      "chunk_type": "process",
      "concepts": [
        "keypoint",
        "descriptor",
        "convolution operator",
        "gaussian filter"
      ],
      "keywords": [
        "keypoint",
        "descriptor",
        "Convolution operator",
        "Gaussian filter",
        "DoG",
        "octave"
      ]
    }
  ]
}

def run_debug():
    print("Preparing model inputs...")
    payload = QuizGeneratePayload(**payload_data)
    chunks_data = [chunk.model_dump() for chunk in payload.chunks]
    
    model_inputs = prepare_all_model_inputs(
        chunks=chunks_data,
        mcqs_per_chunk=payload.mcqs_per_chunk,
    )
    
    print(f"Generated {len(model_inputs)} prompt slots. Running inference...")
    
    debug_results = []
    
    for i, inp in enumerate(model_inputs):
        sys_prompt = inp["system_prompt"]
        usr_prompt = inp["user_prompt"]
        
        print(f"  -> Slot {i}...")
        try:
            raw_text = _real_model_call(sys_prompt, usr_prompt)
            
            # Try to parse it manually to see if it works
            parsed = None
            error_reason = None
            text = raw_text.strip()
            
            if text.startswith("```"):
                lines = text.splitlines()
                text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
                text = text.strip()
                
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError as e:
                import re
                match = re.search(r"\{.*\}", text, re.DOTALL)
                if match:
                    try:
                        parsed = json.loads(match.group(0))
                    except json.JSONDecodeError as e2:
                        error_reason = str(e2)
                else:
                    error_reason = str(e)
            
            debug_results.append({
                "slot_index": i,
                "chunk_id": inp.get("chunk_id"),
                "concept": inp.get("concept"),
                "raw_model_output": raw_text,
                "parsed_json": parsed,
                "parse_error": error_reason
            })
            
        except Exception as e:
            debug_results.append({
                "slot_index": i,
                "chunk_id": inp.get("chunk_id"),
                "concept": inp.get("concept"),
                "raw_model_output": None,
                "parsed_json": None,
                "parse_error": f"Exception during generation: {str(e)}\n{traceback.format_exc()}"
            })

    out_path = "failed_mcqs_debug.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(debug_results, f, indent=2, ensure_ascii=False)
        
    print(f"Done! Wrote results to {out_path}")

if __name__ == '__main__':
    run_debug()
