import sys
import os
import cv2
import numpy as np

ROOT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(ROOT_PATH)
from src.pngd.decoder import decode_png, is_logging

TEST_DIR = os.path.join(ROOT_PATH, 'tests/image/mandrill')

def assert_equal_type(expected: np.ndarray, actual: np.ndarray) -> None:
    if expected.dtype != actual.dtype:
        raise AssertionError(f'Type (expected: {expected.dtype}, actual: {actual.dtype})')

def assert_equal_shape(expected: np.ndarray, actual: np.ndarray) -> None:
    if expected.shape != actual.shape:
        raise AssertionError(f'Shape (expected: {expected.shape}, actual: {actual.shape})')

def assert_equal_data(expected: np.ndarray, actual: np.ndarray) -> None:
    if not np.array_equal(expected, actual):
        raise AssertionError(f'Data')

def assert_equal_image(path: str) -> None:
    expected = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    try:
        with open(path, 'rb') as f:
            dec_data = decode_png(f)
            if dec_data.ndim == 3:
                # if the shape of dec_data is (height, width, channel)
                if dec_data.shape[2] == 3:
                    actual = cv2.cvtColor(dec_data, cv2.COLOR_RGB2BGR)
                elif dec_data.shape[2] == 4:
                    actual = cv2.cvtColor(dec_data, cv2.COLOR_RGBA2BGRA)
                else:
                    assert False
            else:
                # if dec_data is mono-color and shape is just (height, width)
                actual = dec_data
            assert_equal_type(expected, actual)
            assert_equal_shape(expected, actual)
            assert_equal_data(expected, actual)
    except FileNotFoundError:
        raise FileNotFoundError(f'File not found: {os.path.abspath(path)}')
    except AssertionError as ae:
        raise AssertionError(f'{os.path.abspath(path)} {ae}')
    except Exception as e:
        raise e

def test_decode():
    is_logging(False)
    try:
        # assert_image(TEST_DIR + '/type0-1bit.png')
        # assert_image(TEST_DIR + '/type0-2bit.png')
        # assert_image(TEST_DIR + '/type0-4bit.png')
        assert_equal_image(TEST_DIR + '/type0-8bit.png')
        assert_equal_image(TEST_DIR + '/type0-16bit.png')
        assert_equal_image(TEST_DIR + '/type2-8bit.png')
        assert_equal_image(TEST_DIR + '/type2-16bit.png')
        assert_equal_image(TEST_DIR + '/type4-8bit.png')
        assert_equal_image(TEST_DIR + '/type4-16bit.png')
        assert_equal_image(TEST_DIR + '/type6-8bit.png')
        assert_equal_image(TEST_DIR + '/type6-16bit.png')
    except AssertionError as ae:
        print(f'Failed: {ae}')
    except Exception as e:
        print(e)

if __name__ == '__main__':
    test_decode()