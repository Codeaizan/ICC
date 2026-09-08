# Automated ASPECTS Scoring for Ischemic Stroke

## What Our Project Does (In Simple Terms)
When a patient suffers a stroke, doctors need to quickly figure out how much of the brain is damaged to decide if they can safely perform surgery to remove the blood clot. They use a standard 10-point scoring system called **ASPECTS** based on CT brain scans. A score of 10 means a healthy brain, and every damaged region subtracts 1 point. 

Doing this manually is incredibly hard because early stroke damage is very subtle and barely visible to the human eye. 

**Our project automates this scoring process.** We built a software pipeline that takes raw 3D CT scans of the brain, automatically maps the 10 specific ASPECTS regions, analyzes them for stroke damage, and provides a final clinical score through an interactive, offline 3D web viewer.

---

## The Two Phases of Our Solution

### Phase 1: Before the ML Model (Rule-Based Approach)
Initially, we built a **rule-based algorithm**. 
- It aligned the patient's brain to a standard "atlas" (a map of the brain) to find the 10 specific ASPECTS regions.
- It then looked at the brightness (Hounsfield Units) of the pixels in those regions and compared the left side of the brain to the right side.
- If one side was significantly darker than the other (a sign of dead tissue), it flagged the region as damaged and subtracted a point.

**The limitation:** While this heuristic approach was fast and caught obvious damage, it struggled with extremely subtle lesions or unusual brain shapes, missing some critical damage.

### Phase 2: Fusing the ML Model (The Hybrid Approach)
To fix this, we trained a deep learning AI model (**3D U-Net**) on a dataset of stroke CT scans. 
- The AI learned to look at the overall texture and structure of the brain to detect subtle stroke lesions that simple pixel-brightness rules missed.
- **The Fusion (Hybrid Scoring):** We didn't replace the rule-based system; we *fused* them together. Now, the system first runs the rule-based check. Then, it layers the AI's probability maps on top. If the AI is highly confident there is a lesion in a region that the rule-based system missed, we flag it as an **`ml_assisted`** detection and subtract the point.

**The result:** By combining the rigid anatomical rules of the atlas with the pattern-recognition power of deep learning, we achieved a more accurate, hybrid scoring system that captures subtle strokes earlier.

---

## How to Run the Project for the Judges

If the judges ask to see the project running, follow these exact steps to launch the pipeline and the clinical viewer.

### 1. Open the Terminal and Activate the Environment
Open PowerShell in the `D:\Addy project` folder and run:
```powershell
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force
.\.venv\Scripts\activate
```

### 2. Show the Command Line Pipeline (Optional)
If they want to see the terminal tool running a single case through the hybrid pipeline:
```powershell
aspects-score data/processed/aisd/0538941_ct.nii.gz --atlas-dir data/atlas/downloaded/ASPECTS-281 --ml-prob outputs/local_ml_predictions/0538941/ml_prob.nii.gz --output outputs/demo_case
```

### 3. Launch the Clinical Viewer (The Main Demo)
To show the beautiful UI with all the 50 test cases pre-processed through our hybrid ML pipeline, run:
```powershell
aspects-viewer --output outputs/hybrid_test --port 8000
```
*(Leave this terminal window open while demonstrating!)*

### 4. Demonstrate the UI
1. Open your web browser and go to **http://localhost:8000**
2. Click on a case on the left (e.g., **`0538941`** or **`0538799`**).
3. **What to point out to the judges:**
   - **The 3D Viewer:** Show how you can scroll through the brain slices.
   - **The Colored Overlays:** Point out the highlighted ASPECTS regions on the scan.
   - **The Hybrid Evidence Tags:** Look at the grid on the right. Point out regions labeled as **`ml_assisted`**. Explain: *"This region was caught by our deep learning model, proving that the AI is finding subtle stroke damage that our basic algorithms missed."*
