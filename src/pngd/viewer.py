import numpy as np
import cv2

def show_image(color_data: np.ndarray, file_name: str) -> None:
    # cv2 allows only BGR format
    color_data_BGR = cv2.cvtColor(color_data, cv2.COLOR_RGB2BGR)

    cv2.imshow(file_name, color_data_BGR)
    while True:
        # Wait for 100ms
        key = cv2.waitKey(100)

        # Quit if 'q' or ESC is pressed
        if key == ord('q') or key == 27:
            cv2.destroyAllWindows()
            break
        # Quit if the window is closed
        if cv2.getWindowProperty(file_name, cv2.WND_PROP_VISIBLE) < 1:
            break

    cv2.destroyAllWindows()
