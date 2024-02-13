import sys
import os
import cv2
import numpy as np

ROOT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(ROOT_PATH)
from src.ppng.decoder.decoder import Decoder

class TestDecode:
    TEST_DIR = os.path.join(ROOT_PATH, 'tests/image/mandrill/')

    def _assert_equal_image(self, file_name: str) -> None:
        decoder = Decoder()
        file_name = self.TEST_DIR + file_name
        expected = cv2.imread(file_name, cv2.IMREAD_UNCHANGED)
        try:
            with open(file_name, 'rb') as f:
                dec_data = decoder.decode_png(f)
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

                assert expected.dtype == actual.dtype
                assert expected.shape == actual.shape
                assert np.array_equal(expected, actual)
        except FileNotFoundError:
            raise FileNotFoundError(f'File not found: {os.path.abspath(file_name)}')

    # def test_type0_1bit(self):
    #     self._assert_equal_image('type0-1bit.png')

    # def test_type0_2bit(self):
    #     self._assert_equal_image('type0-2bit.png')

    # def test_type0_4bit(self):
    #     self._assert_equal_image('type0-4bit.png')

    def test_type0_8bit(self):
        self._assert_equal_image('type0-8bit.png')

    def test_type0_16bit(self):
        self._assert_equal_image('type0-16bit.png')

    def test_type2_8bit(self):
        self._assert_equal_image('type2-8bit.png')

    def test_type2_16bit(self):
        self._assert_equal_image('type2-16bit.png')

    def test_type3_8bit(self):
        self._assert_equal_image('type3-8bit.png')

    def test_type4_8bit(self):
        self._assert_equal_image('type4-8bit.png')

    def test_type4_16bit(self):
        self._assert_equal_image('type4-16bit.png')

    def test_type6_8bit(self):
        self._assert_equal_image('type6-8bit.png')

    def test_type6_16bit(self):
        self._assert_equal_image('type6-16bit.png')
