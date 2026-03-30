import paho.mqtt.client as mqtt
import cv2
import numpy as np
import threading
 
# Configuration
BROKER = os.getenv("BROKER")
PORT = int(os.getenv("PORT", 1883))
TOPIC_IMAGE = os.getenv("TOPIC_IMAGE")
TOPIC_COMMAND = os.getenv("TOPIC_COMMAND")

# Global flags
running = True
 
# Shared frame storage (thread-safe via lock)
latest_frame = None
frame_lock = threading.Lock()
 
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT Broker!")
        client.subscribe(TOPIC_IMAGE)
    else:
        print(f"Failed to connect, return code {rc}")
 
def on_message(client, userdata, msg):
    global latest_frame
    try:
        nparr = np.frombuffer(msg.payload, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
 
        if img is not None:
            # Store the frame — do NOT call cv2.imshow here (wrong thread!)
            with frame_lock:
                latest_frame = img
        else:
            print("Failed to decode image")
    except Exception as e:
        print(f"Error processing image: {e}")
 
def main():
    global running, latest_frame
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
 
    try:
        client.tls_set(ca_certs="certs/ca.crt")

        client.connect(BROKER, 8883, 60)
        client.loop_start()
 
        print("\n--- ESP32 Camera Controller ---")
        print("Controls:")
        print(" 's' : Take Single Picture")
        print(" 'b' : Begin Stream")
        print(" 'e' : End Stream")
        print(" 'q' : Quit")
        print("-------------------------------\n")
 
        cv2.namedWindow("ESP32-CAM Stream", cv2.WINDOW_AUTOSIZE)
 
        while running:
            # Display the latest frame if available (main thread only)
            with frame_lock:
                frame = latest_frame
 
            if frame is not None:
                cv2.imshow("ESP32-CAM Stream", frame)
 
            # Handle GUI events and keyboard input (main thread only)
            key = cv2.waitKey(30) & 0xFF
 
            if key == ord('q'):
                running = False
            elif key == ord('s'):
                print("Command: Capture")
                client.publish(TOPIC_COMMAND, "CAPTURE")
            elif key == ord('b'):
                print("Command: Start Stream")
                client.publish(TOPIC_COMMAND, "START-LIVE")
            elif key == ord('e'):
                print("Command: Stop Stream")
                client.publish(TOPIC_COMMAND, "STOP-LIVE")
 
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        client.loop_stop()
        client.disconnect()
        cv2.destroyAllWindows()
 
if __name__ == "__main__":
    main()
