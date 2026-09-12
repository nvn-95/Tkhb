import cv2
import mediapipe as mp
import os
import json
import sqlite3
import argparse
from glob import glob

# Initialize MediaPipe Holistic (combines pose, face, and hands)
mp_holistic = mp.solutions.holistic

def init_db(db_path="sign_language.db"):
    """Initialize the SQLite database for storing the frame sequences."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create a table for the videos/signs
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sign_name TEXT,
            video_path TEXT UNIQUE
        )
    ''')
    
    # Create a table for the frame landmarks
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS FrameLandmarks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id INTEGER,
            frame_index INTEGER,
            pose_landmarks TEXT,
            left_hand_landmarks TEXT,
            right_hand_landmarks TEXT,
            FOREIGN KEY(video_id) REFERENCES Videos(id)
        )
    ''')
    
    conn.commit()
    return conn

def extract_landmarks(results):
    """Extract standard JSON structures for landmarks from MediaPipe results."""
    def to_list(landmark_list):
        if not landmark_list:
            return None
        return [{"x": lm.x, "y": lm.y, "z": lm.z, "visibility": getattr(lm, 'visibility', 1.0)} for lm in landmark_list.landmark]
    
    return {
        "pose": to_list(results.pose_landmarks),
        "left_hand": to_list(results.left_hand_landmarks),
        "right_hand": to_list(results.right_hand_landmarks)
    }

def process_video(video_path, conn, holistic_model):
    """Process a single video, extract frames, detect landmarks, and save to DB."""
    # Derive the sign word from the video filename (e.g., "FOOD.mp4" -> "FOOD")
    sign_name = os.path.basename(video_path).split('.')[0].upper()
    print(f"Processing video for sign: {sign_name} ({video_path})")
    
    cursor = conn.cursor()
    
    # Insert or ignore video entry
    cursor.execute('INSERT OR IGNORE INTO Videos (sign_name, video_path) VALUES (?, ?)', (sign_name, video_path))
    cursor.execute('SELECT id FROM Videos WHERE video_path = ?', (video_path,))
    video_id = cursor.fetchone()[0]
    
    # Check if already processed (optional, but good for resuming if stopped halfway)
    cursor.execute('SELECT COUNT(*) FROM FrameLandmarks WHERE video_id = ?', (video_id,))
    if cursor.fetchone()[0] > 0:
        print(f"Skipping {sign_name}, already in database.")
        return
        
    cap = cv2.VideoCapture(video_path)
    frame_index = 0
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
            
        # Convert the BGR image to RGB before processing.
        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image.flags.writeable = False
        
        # Make detection using MediaPipe
        results = holistic_model.process(image)
        
        # Extract landmark data dictionary
        landmarks = extract_landmarks(results)
        
        # Convert dictionary data to JSON strings for database storage
        pose_json = json.dumps(landmarks["pose"]) if landmarks["pose"] else None
        lh_json = json.dumps(landmarks["left_hand"]) if landmarks["left_hand"] else None
        rh_json = json.dumps(landmarks["right_hand"]) if landmarks["right_hand"] else None
        
        cursor.execute('''
            INSERT INTO FrameLandmarks (video_id, frame_index, pose_landmarks, left_hand_landmarks, right_hand_landmarks)
            VALUES (?, ?, ?, ?, ?)
        ''', (video_id, frame_index, pose_json, lh_json, rh_json))
        
        frame_index += 1
        
    cap.release()
    conn.commit()
    print(f"Finished {sign_name}: processed {frame_index} frames.")

def main():
    parser = argparse.ArgumentParser(description="Extract hand/pose landmarks from videos and store in SQLite database.")
    # Default folder to expect the dataset. We'll wait until you create it.
    parser.add_argument("--dataset_folder", type=str, default="dataset_videos", help="Folder containing the Kaggle video files.")
    parser.add_argument("--db_path", type=str, default="sign_language.db", help="Path to output SQLite database.")
    args = parser.parse_args()

    # Ensure dataset folder exists (creates empty one if missing to guide the user)
    if not os.path.exists(args.dataset_folder):
        print(f"Dataset folder '{args.dataset_folder}' not found. Creating empty directory for later use.")
        os.makedirs(args.dataset_folder, exist_ok=True)
        print("📁 Please upload your Kaggle videos into the 'dataset_videos' directory and run this script again.")
        return

    # Look for common video formats
    video_files = glob(os.path.join(args.dataset_folder, "*.mp4")) + \
                  glob(os.path.join(args.dataset_folder, "*.avi")) + \
                  glob(os.path.join(args.dataset_folder, "*.mov"))
    
    if not video_files:
        print(f"No video files found in '{args.dataset_folder}'. 📁 Please put the dataset here.")
        return

    print(f"Found {len(video_files)} videos. Initializing database '{args.db_path}'...")
    conn = init_db(args.db_path)
    
    # Initialize MediaPipe Holistic model once and keep it open
    print("Loading MediaPipe Holistic AI model...")
    with mp_holistic.Holistic(
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5) as holistic:
        
        for video_path in video_files:
            try:
                process_video(video_path, conn, holistic)
            except Exception as e:
                print(f"Error processing video {video_path}: {e}")
                
    conn.close()
    print("✅ All videos successfully processed and saved to database.")

if __name__ == "__main__":
    main()
