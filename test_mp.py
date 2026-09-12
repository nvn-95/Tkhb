import mediapipe as mp
print(f"MediaPipe version: {mp.__version__}")
try:
    with mp.solutions.holistic.Holistic() as holistic:
        print("Holistic initialized successfully!")
except Exception as e:
    print(f"Error: {e}")
