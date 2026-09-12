import cv2
import mediapipe as mp
import os
import json
from glob import glob

mp_holistic = mp.solutions.holistic

def extract_mid_frame_pose(video_path):
    cap = cv2.VideoCapture(video_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    mid_frame_idx = total_frames // 2
    
    cap.set(cv2.CAP_PROP_POS_FRAMES, mid_frame_idx)
    ret, frame = cap.read()
    cap.release()
    if not ret: return None
        
    image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    with mp_holistic.Holistic(static_image_mode=True) as holistic:
        results = holistic.process(image)
        if not results.pose_landmarks: return None
            
        def to_canvas(lm):
            # FLIP x since avatar left is image right
            x = round((1.0 - lm.x) * 400)
            y = round(lm.y * 420)
            return [x, y]

        pose = {
            "le": to_canvas(results.pose_landmarks.landmark[13]),
            "lw": to_canvas(results.pose_landmarks.landmark[15]),
            "re": to_canvas(results.pose_landmarks.landmark[14]),
            "rw": to_canvas(results.pose_landmarks.landmark[16]),
            "lh": "open",
            "rh": "open"
        }
        
        # Simple hand logic: if fingers are closer to palm, use fist
        if results.left_hand_landmarks:
            pose["lh"] = "relaxed"
        if results.right_hand_landmarks: 
            pose["rh"] = "relaxed"
            
        return pose

def main():
    folders = [f for f in os.listdir('.') if os.path.exists(f) and os.path.isdir(f) and f[0].isdigit()]
    new_poses = {}
    for folder in folders:
        sign_name = folder.split('. ', 1)[-1].upper() if '. ' in folder else folder.upper()
        video_files = glob(os.path.join(folder, "*.MOV")) + glob(os.path.join(folder, "*.mp4"))
        if not video_files: continue
        pose = extract_mid_frame_pose(video_files[0])
        if pose:
            new_poses[sign_name] = pose
            
    print("\n    // --- CUSTOM POSES FROM VIDEOS ---")
    for name, p in new_poses.items():
        print(f"    {name}: {{ le:[{p['le'][0]},{p['le'][1]}], lw:[{p['lw'][0]},{p['lw'][1]}], re:[{p['re'][0]},{p['re'][1]}], rw:[{p['rw'][0]},{p['rw'][1]}], lh:'{p['lh']}', rh:'{p['rh']}' }},")

if __name__ == "__main__":
    main()
